from fastapi import APIRouter, Depends, Form
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload
from starlette.requests import Request

from app.config import get_settings
from app.database import get_db
from app.dependencies import current_user
from app.enums import JourneyStatus, PredictionStatus
from app.models.journey import Journey
from app.models.prediction import Prediction, PredictionPick
from app.models.race import Race
from app.models.specialist import Specialist
from app.models.user import User
from app.services.llm.factory import build_llm_provider
from app.services.prediction_normalizer import normalize_prediction
from app.services.validation_engine import validate_prediction

router = APIRouter(prefix="/journeys/{journey_id}/predictions", tags=["predictions"])
templates = Jinja2Templates(directory="app/templates")


@router.get("", response_class=HTMLResponse)
def predictions_index(request: Request, journey_id: str, db: Session = Depends(get_db), user: User = Depends(current_user)) -> HTMLResponse:
    journey = _load_journey(db, journey_id)
    specialists = db.scalars(select(Specialist).where(Specialist.is_active.is_(True)).order_by(Specialist.display_order)).all()
    predictions = {prediction.specialist_id: prediction for prediction in journey.predictions}
    return templates.TemplateResponse("predictions/index.html", {"request": request, "journey": journey, "specialists": specialists, "predictions": predictions, "user": user})


@router.get("/{specialist_id}", response_class=HTMLResponse)
def prediction_form(request: Request, journey_id: str, specialist_id: str, db: Session = Depends(get_db), user: User = Depends(current_user)) -> HTMLResponse:
    journey = _load_journey(db, journey_id)
    specialist = db.get(Specialist, specialist_id)
    prediction = _get_prediction(db, journey_id, specialist_id)
    pick_map = {pick.race_number: pick for pick in prediction.picks} if prediction else {}
    return templates.TemplateResponse("predictions/form.html", {"request": request, "journey": journey, "specialist": specialist, "prediction": prediction, "pick_map": pick_map, "user": user})


@router.post("/{specialist_id}/normalize")
def normalize(
    journey_id: str,
    specialist_id: str,
    raw_text: str = Form(...),
    db: Session = Depends(get_db),
    user: User = Depends(current_user),
) -> RedirectResponse:
    settings = get_settings()
    journey = _load_journey(db, journey_id)
    specialist = db.get(Specialist, specialist_id)
    prediction = _get_or_create_prediction(db, journey_id, specialist_id)
    prediction.raw_text = raw_text
    try:
        provider = build_llm_provider(settings)
        valid_numbers = {race.race_number: [participant.number for participant in race.participants] for race in journey.races}
        normalized = normalize_prediction(provider, specialist.name, raw_text, len(journey.races), valid_numbers)
    except Exception as exc:
        prediction.requires_human_review = True
        prediction.status = PredictionStatus.REQUIRES_REVIEW
        prediction.validation_errors = [
            {
                "scope": "llm",
                "message": f"No se pudo normalizar con el proveedor LLM configurado: {type(exc).__name__}. Revisa LLM_PROVIDER, LLM_MODEL, LLM_BASE_URL y LLM_API_KEY.",
                "race_number": None,
                "specialist": specialist.name if specialist else None,
                "field": None,
            }
        ]
        db.commit()
        return RedirectResponse(f"/journeys/{journey_id}/predictions/{specialist_id}", status_code=303)
    prediction.normalized_json = normalized.model_dump()
    prediction.requires_human_review = normalized.requires_human_review or (normalized.global_confidence or 0) < 0.8
    prediction.llm_provider = provider.provider_name
    prediction.llm_model = provider.model_name
    prediction.llm_confidence = normalized.global_confidence
    prediction.picks.clear()
    db.flush()
    races_by_number = {race.race_number: race for race in journey.races}
    for race_pick in normalized.races:
        race = races_by_number.get(race_pick.race_number)
        if race:
            prediction.picks.append(
                PredictionPick(
                    race_id=race.id,
                    race_number=race_pick.race_number,
                    pick_1=race_pick.pick_1,
                    pick_2=race_pick.pick_2,
                    pick_3=race_pick.pick_3,
                    confidence=race_pick.confidence,
                    notes=race_pick.notes,
                )
            )
    result = validate_prediction(journey, prediction)
    prediction.validation_errors = [error.model_dump() for error in result.errors]
    prediction.status = PredictionStatus.REQUIRES_REVIEW if prediction.requires_human_review else (PredictionStatus.VALID if result.ok else PredictionStatus.VALIDATION_FAILED)
    if journey.status == JourneyStatus.PARTANT_CONFIRMED:
        journey.status = JourneyStatus.PREDICTIONS_IN_PROGRESS
    _promote_journey_if_predictions_valid(journey)
    db.commit()
    return RedirectResponse(f"/journeys/{journey_id}/predictions/{specialist_id}", status_code=303)


@router.post("/{specialist_id}/manual")
def save_manual(
    journey_id: str,
    specialist_id: str,
    race_ids: list[str] = Form(default=[]),
    race_numbers: list[int] = Form(default=[]),
    pick_1: list[int] = Form(default=[]),
    pick_2: list[int] = Form(default=[]),
    pick_3: list[int] = Form(default=[]),
    db: Session = Depends(get_db),
    user: User = Depends(current_user),
) -> RedirectResponse:
    journey = _load_journey(db, journey_id)
    prediction = _get_or_create_prediction(db, journey_id, specialist_id)
    prediction.picks.clear()
    db.flush()
    for race_id, race_number, first, second, third in zip(race_ids, race_numbers, pick_1, pick_2, pick_3, strict=False):
        prediction.picks.append(PredictionPick(race_id=race_id, race_number=race_number, pick_1=first, pick_2=second, pick_3=third, confidence=1.0))
    prediction.requires_human_review = False
    result = validate_prediction(journey, prediction)
    prediction.validation_errors = [error.model_dump() for error in result.errors]
    prediction.status = PredictionStatus.VALID if result.ok else PredictionStatus.VALIDATION_FAILED
    _promote_journey_if_predictions_valid(journey)
    db.commit()
    return RedirectResponse(f"/journeys/{journey_id}/predictions/{specialist_id}", status_code=303)


def _load_journey(db: Session, journey_id: str) -> Journey:
    journey = db.scalar(
        select(Journey)
        .where(Journey.id == journey_id)
        .options(
            selectinload(Journey.races).selectinload(Race.participants),
            selectinload(Journey.predictions).selectinload(Prediction.picks),
            selectinload(Journey.predictions).selectinload(Prediction.specialist),
        )
    )
    if journey is None:
        raise ValueError("Journey not found")
    return journey


def _get_prediction(db: Session, journey_id: str, specialist_id: str) -> Prediction | None:
    return db.scalar(select(Prediction).where(Prediction.journey_id == journey_id, Prediction.specialist_id == specialist_id).options(selectinload(Prediction.picks)))


def _get_or_create_prediction(db: Session, journey_id: str, specialist_id: str) -> Prediction:
    prediction = _get_prediction(db, journey_id, specialist_id)
    if prediction:
        return prediction
    prediction = Prediction(journey_id=journey_id, specialist_id=specialist_id, status=PredictionStatus.RAW_SAVED)
    db.add(prediction)
    db.flush()
    return prediction


def _promote_journey_if_predictions_valid(journey: Journey) -> None:
    if len(journey.predictions) == 8 and all(prediction.status == PredictionStatus.VALID for prediction in journey.predictions):
        journey.status = JourneyStatus.PREDICTIONS_VALID
