import logging
from pathlib import Path

from fastapi import APIRouter, Depends
from fastapi.responses import HTMLResponse, RedirectResponse
from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload
from starlette.requests import Request

from app.config import get_settings
from app.database import get_db
from app.dependencies import require_admin
from app.enums import JourneyStatus, OutputStatus
from app.models.generated_output import GeneratedOutput
from app.models.journey import Journey
from app.models.user import User
from app.security import verify_csrf
from app.services.drive_uploader import upload_file_to_drive
from app.services.email_sender import send_outputs_email
from app.services.output_guard import can_run_final_action
from app.templating import templates
from app.utils import utcnow

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/journeys/{journey_id}", tags=["integrations"], dependencies=[Depends(verify_csrf)])


@router.post("/drive/upload")
def upload_drive(journey_id: str, db: Session = Depends(get_db), user: User = Depends(require_admin)) -> RedirectResponse:
    settings = get_settings()
    journey = _load_journey(db, journey_id)
    if not can_run_final_action(journey).ok:
        return RedirectResponse(f"/journeys/{journey_id}/outputs", status_code=303)
    try:
        for output in journey.outputs:
            result = upload_file_to_drive(Path(output.local_path), settings, f"{journey.date}_{journey.venue}")
            output.drive_file_id = result.file_id
            output.drive_url = result.url
            output.status = OutputStatus.UPLOADED
            output.uploaded_at = utcnow()
    except Exception:
        logger.exception("Drive upload failed for journey %s", journey_id)
        for output in journey.outputs:
            output.status = OutputStatus.FAILED
        db.commit()
        return RedirectResponse(f"/journeys/{journey_id}/outputs?error=drive", status_code=303)
    journey.drive_uploaded_at = utcnow()
    journey.status = JourneyStatus.DRIVE_UPLOADED
    db.commit()
    return RedirectResponse(f"/journeys/{journey_id}/outputs", status_code=303)


@router.get("/email", response_class=HTMLResponse)
def email_preview(request: Request, journey_id: str, db: Session = Depends(get_db), user: User = Depends(require_admin)) -> HTMLResponse:
    journey = _load_journey(db, journey_id)
    settings = get_settings()
    return templates.TemplateResponse("outputs/email.html", {"request": request, "journey": journey, "settings": settings, "user": user, "blockers": can_run_final_action(journey).errors})


@router.post("/email/send")
def email_send(journey_id: str, db: Session = Depends(get_db), user: User = Depends(require_admin)) -> RedirectResponse:
    settings = get_settings()
    journey = _load_journey(db, journey_id)
    if not can_run_final_action(journey).ok:
        return RedirectResponse(f"/journeys/{journey_id}/email", status_code=303)
    paths = [Path(output.local_path) for output in journey.outputs if output.local_path]
    subject = f"Tips y pronósticos - {journey.venue} {journey.date}"
    drive_links = "\n".join(output.drive_url or "" for output in journey.outputs if output.drive_url)
    body = f"Buenos días,\n\nAdjunto los Tips y el cuadro de pronósticos de la jornada.\n\n{drive_links}\n\nUn saludo."
    try:
        send_outputs_email(settings, subject, body, paths)
    except Exception:
        logger.exception("Email send failed for journey %s", journey_id)
        for output in journey.outputs:
            output.status = OutputStatus.FAILED
        db.commit()
        return RedirectResponse(f"/journeys/{journey_id}/email?error=smtp", status_code=303)
    now = utcnow()
    for output in journey.outputs:
        output.status = OutputStatus.SENT
        output.sent_at = now
    journey.email_sent_at = now
    journey.status = JourneyStatus.EMAIL_SENT
    db.commit()
    return RedirectResponse(f"/journeys/{journey_id}/outputs", status_code=303)


def _load_journey(db: Session, journey_id: str) -> Journey:
    journey = db.scalar(select(Journey).where(Journey.id == journey_id).options(selectinload(Journey.outputs)))
    if journey is None:
        raise ValueError("Journey not found")
    return journey
