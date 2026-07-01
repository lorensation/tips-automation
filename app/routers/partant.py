from datetime import datetime
from pathlib import Path

from fastapi import APIRouter, Depends, File, Form, UploadFile
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload
from starlette.requests import Request

from app.config import get_settings
from app.database import get_db
from app.dependencies import require_admin
from app.enums import JourneyStatus
from app.models.journey import Journey
from app.models.participant import Participant
from app.models.race import Race
from app.models.user import User
from app.services.audit import record_event
from app.services.pdf_parser import parse_participants_pdf
from app.services.validation_engine import validate_partant

router = APIRouter(prefix="/journeys/{journey_id}", tags=["partant"])
templates = Jinja2Templates(directory="app/templates")


@router.post("/pdf")
async def upload_pdf(
    journey_id: str,
    pdf: UploadFile = File(...),
    db: Session = Depends(get_db),
    user: User = Depends(require_admin),
) -> RedirectResponse:
    settings = get_settings()
    if not pdf.filename.lower().endswith(".pdf"):
        return RedirectResponse(f"/journeys/{journey_id}?error=pdf_type", status_code=303)
    content = await pdf.read()
    if len(content) > settings.max_pdf_bytes:
        return RedirectResponse(f"/journeys/{journey_id}?error=pdf_size", status_code=303)
    journey = _load_journey(db, journey_id)
    upload_dir = settings.upload_dir / journey_id
    upload_dir.mkdir(parents=True, exist_ok=True)
    pdf_path = upload_dir / pdf.filename
    pdf_path.write_bytes(content)
    parsed = parse_participants_pdf(pdf_path)

    journey.races.clear()
    db.flush()
    for parsed_race in parsed.races:
        race = Race(
            journey=journey,
            race_number=parsed_race.race_number,
            name=parsed_race.name,
            distance_meters=parsed_race.distance_meters,
            surface=parsed_race.surface,
        )
        for parsed_participant in parsed_race.participants:
            race.participants.append(
                Participant(
                    number=parsed_participant.number,
                    horse_name=parsed_participant.horse_name,
                    raw_name=parsed_participant.raw_name,
                    jockey=parsed_participant.jockey,
                    trainer=parsed_participant.trainer,
                    stall=parsed_participant.stall,
                )
            )
        journey.races.append(race)
    journey.pdf_original_filename = pdf.filename
    journey.pdf_storage_path = str(pdf_path)
    journey.status = JourneyStatus.PARTANT_EXTRACTED
    record_event(db, "pdf_uploaded", journey.id, user.id, {"filename": pdf.filename, "races": len(parsed.races)})
    db.commit()
    return RedirectResponse(f"/journeys/{journey_id}/partant", status_code=303)


@router.get("/partant", response_class=HTMLResponse)
def review_partant(request: Request, journey_id: str, db: Session = Depends(get_db), user: User = Depends(require_admin)) -> HTMLResponse:
    journey = _load_journey(db, journey_id)
    result = validate_partant(journey)
    return templates.TemplateResponse("partant/review.html", {"request": request, "journey": journey, "errors": result.errors, "user": user})


@router.post("/partant")
def save_partant(
    journey_id: str,
    race_ids: list[str] = Form(default=[]),
    participant_ids: list[str] = Form(default=[]),
    participant_numbers: list[int] = Form(default=[]),
    horse_names: list[str] = Form(default=[]),
    db: Session = Depends(get_db),
    user: User = Depends(require_admin),
) -> RedirectResponse:
    journey = _load_journey(db, journey_id)
    participant_map = {participant.id: participant for race in journey.races for participant in race.participants}
    for participant_id, number, horse_name in zip(participant_ids, participant_numbers, horse_names, strict=False):
        participant = participant_map.get(participant_id)
        if participant:
            participant.number = number
            participant.horse_name = horse_name.strip()
    record_event(db, "partant_saved", journey.id, user.id)
    db.commit()
    return RedirectResponse(f"/journeys/{journey_id}/partant", status_code=303)


@router.post("/partant/confirm")
def confirm_partant(journey_id: str, db: Session = Depends(get_db), user: User = Depends(require_admin)) -> RedirectResponse:
    journey = _load_journey(db, journey_id)
    result = validate_partant(journey)
    if result.ok:
        journey.partant_confirmed_at = datetime.utcnow()
        journey.status = JourneyStatus.PARTANT_CONFIRMED
        record_event(db, "partant_confirmed", journey.id, user.id)
        db.commit()
    return RedirectResponse(f"/journeys/{journey_id}/partant", status_code=303)


def _load_journey(db: Session, journey_id: str) -> Journey:
    journey = db.scalar(
        select(Journey)
        .where(Journey.id == journey_id)
        .options(selectinload(Journey.races).selectinload(Race.participants))
    )
    if journey is None:
        raise ValueError("Journey not found")
    return journey
