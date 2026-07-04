import logging

from fastapi import APIRouter, Depends, Form
from fastapi.responses import HTMLResponse, RedirectResponse
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
from app.security import verify_csrf
from app.services.audit import record_event
from app.services.bulk_segmenter import segment_bulk_text
from app.services.llm.factory import build_llm_provider
from app.services.prediction_normalizer import normalize_prediction
from app.services.validation_engine import validate_picks, validate_prediction
from app.templating import templates

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/journeys/{journey_id}/predictions", tags=["predictions"], dependencies=[Depends(verify_csrf)])


@router.get("", response_class=HTMLResponse)
def predictions_index(request: Request, journey_id: str, db: Session = Depends(get_db), user: User = Depends(current_user)) -> HTMLResponse:
    journey = _load_journey(db, journey_id)
    specialists = db.scalars(select(Specialist).where(Specialist.is_active.is_(True)).order_by(Specialist.display_order)).all()
    predictions = {prediction.specialist_id: prediction for prediction in journey.predictions}
    return templates.TemplateResponse("predictions/index.html", {"request": request, "journey": journey, "specialists": specialists, "predictions": predictions, "user": user})


@router.get("/bulk", response_class=HTMLResponse)
def bulk_form(request: Request, journey_id: str, db: Session = Depends(get_db), user: User = Depends(current_user)) -> HTMLResponse:
    journey = _load_journey(db, journey_id)
    return templates.TemplateResponse("predictions/bulk.html", {"request": request, "journey": journey, "user": user})


@router.post("/bulk/preview", response_class=HTMLResponse)
def bulk_preview(
    request: Request,
    journey_id: str,
    raw_text: str = Form(...),
    db: Session = Depends(get_db),
    user: User = Depends(current_user),
) -> HTMLResponse:
    settings = get_settings()
    journey = _load_journey(db, journey_id)
    specialists = db.scalars(
        select(Specialist).where(Specialist.is_active.is_(True)).order_by(Specialist.display_order)
    ).all()
    specialists_by_name = {specialist.name: specialist for specialist in specialists}
    segmentation = segment_bulk_text(raw_text)
    valid_numbers = {
        race.race_number: [participant.number for participant in race.participants if participant.is_active]
        for race in journey.races
    }
    total_races = len(journey.races)

    provider = None
    provider_error: str | None = None
    try:
        provider = build_llm_provider(settings)
    except Exception as exc:
        provider_error = f"Proveedor LLM no disponible ({type(exc).__name__}); se usará solo el parser determinista."
        logger.warning("LLM provider unavailable for bulk preview: %s", exc)

    entries = []
    for block in segmentation.blocks:
        specialist = specialists_by_name.get(block.specialist_name)
        if specialist is None:
            continue
        picks: dict[int, tuple[int, int, int]] = {}
        general_errors: list[str] = []
        requires_review = False
        llm_provider = llm_model = None
        confidence = None
        if block.raw_block:
            try:
                if provider is None:
                    raise RuntimeError(provider_error or "LLM provider unavailable")
                normalized = normalize_prediction(provider, specialist.name, block.raw_block, total_races, valid_numbers)
                picks = {
                    race.race_number: (race.pick_1, race.pick_2, race.pick_3) for race in normalized.races
                }
                requires_review = normalized.requires_human_review or (normalized.global_confidence or 0) < 0.8
                llm_provider = provider.provider_name
                llm_model = provider.model_name
                confidence = normalized.global_confidence
            except Exception as exc:
                logger.warning("Bulk normalization failed for %s", specialist.name, exc_info=True)
                requires_review = True
                general_errors.append(
                    f"No se pudo normalizar el bloque automáticamente ({type(exc).__name__}). Introduce los picks a mano."
                )
        else:
            general_errors.append("El bloque de este especialista está vacío.")
            requires_review = True
        result = validate_picks(journey, specialist.name, picks)
        errors_by_race: dict[int, list[str]] = {}
        for error in result.errors:
            if error.race_number:
                errors_by_race.setdefault(error.race_number, []).append(error.message)
            else:
                general_errors.append(error.message)
        entries.append(
            {
                "specialist": specialist,
                "raw_block": block.raw_block,
                "picks": picks,
                "errors_by_race": errors_by_race,
                "general_errors": general_errors,
                "error_count": len(result.errors) + len(general_errors),
                "requires_review": requires_review,
                "ok": result.ok and not general_errors,
                "llm_provider": llm_provider,
                "llm_model": llm_model,
                "confidence": confidence,
            }
        )

    return templates.TemplateResponse(
        "predictions/bulk_preview.html",
        {
            "request": request,
            "journey": journey,
            "entries": entries,
            "missing_specialists": segmentation.missing_specialists,
            "duplicated_specialists": segmentation.duplicated_specialists,
            "unassigned_preamble": segmentation.unassigned_preamble,
            "provider_error": provider_error,
            "bulk_raw_text": raw_text,
            "user": user,
        },
    )


@router.post("/bulk/confirm")
async def bulk_confirm(
    request: Request,
    journey_id: str,
    db: Session = Depends(get_db),
    user: User = Depends(current_user),
) -> RedirectResponse:
    journey = _load_journey(db, journey_id)
    form = await request.form()
    bulk_raw_text = str(form.get("bulk_raw_text", ""))
    specialists = db.scalars(
        select(Specialist).where(Specialist.is_active.is_(True)).order_by(Specialist.display_order)
    ).all()
    races_by_number = {race.race_number: race for race in journey.races}
    saved_names: list[str] = []

    for specialist in specialists:
        if form.get(f"include_{specialist.id}") != "1":
            continue
        prediction = _get_or_create_prediction(db, journey_id, specialist.id)
        prediction.raw_text = str(form.get(f"raw_block_{specialist.id}", "")) or bulk_raw_text
        prediction.llm_provider = str(form.get(f"llm_provider_{specialist.id}", "")) or None
        prediction.llm_model = str(form.get(f"llm_model_{specialist.id}", "")) or None
        confidence_raw = str(form.get(f"llm_confidence_{specialist.id}", ""))
        prediction.llm_confidence = float(confidence_raw) if _is_float(confidence_raw) else None
        was_review = form.get(f"requires_review_{specialist.id}") == "1"
        prediction.picks.clear()
        db.flush()
        for race_number, race in races_by_number.items():
            values = []
            for slot in (1, 2, 3):
                raw_value = str(form.get(f"pick_{specialist.id}_{race_number}_{slot}", "")).strip()
                values.append(int(raw_value) if raw_value.lstrip("-").isdigit() else None)
            if any(value is None for value in values):
                continue
            prediction.picks.append(
                PredictionPick(
                    race_id=race.id,
                    race_number=race_number,
                    pick_1=values[0],
                    pick_2=values[1],
                    pick_3=values[2],
                    confidence=1.0,
                )
            )
        result = validate_prediction(journey, prediction)
        prediction.validation_errors = [error.model_dump() for error in result.errors]
        if result.ok:
            prediction.status = PredictionStatus.VALID
            prediction.requires_human_review = False
        else:
            prediction.status = PredictionStatus.REQUIRES_REVIEW if was_review else PredictionStatus.VALIDATION_FAILED
            prediction.requires_human_review = was_review
        saved_names.append(specialist.name)

    if saved_names:
        record_event(
            db,
            "bulk_predictions_saved",
            journey.id,
            user.id,
            {"specialists": saved_names, "raw_text": bulk_raw_text},
        )
        if journey.status == JourneyStatus.PARTANT_CONFIRMED:
            journey.status = JourneyStatus.PREDICTIONS_IN_PROGRESS
        _promote_journey_if_predictions_valid(journey)
        logger.info("Bulk predictions saved for journey %s: %s", journey_id, ", ".join(saved_names))
    db.commit()
    return RedirectResponse(f"/journeys/{journey_id}/predictions", status_code=303)


def _is_float(value: str) -> bool:
    try:
        float(value)
        return True
    except ValueError:
        return False


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
        logger.exception("Prediction normalization failed for journey %s specialist %s", journey_id, specialist_id)
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
