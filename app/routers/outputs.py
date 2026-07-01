import asyncio
import hashlib
from datetime import datetime
from pathlib import Path

from fastapi import APIRouter, Depends
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy import func, select
from sqlalchemy.orm import Session, selectinload
from starlette.requests import Request

from app.config import get_settings
from app.database import get_db
from app.dependencies import require_admin
from app.enums import JourneyStatus, OutputStatus, OutputType
from app.models.generated_output import GeneratedOutput
from app.models.journey import Journey
from app.models.prediction import Prediction
from app.models.race import Race
from app.models.user import User
from app.services.board_renderer import export_board_png_pdf, write_board_html
from app.services.output_guard import generation_blockers
from app.services.tips_excel_generator import generate_tips_excel

router = APIRouter(prefix="/journeys/{journey_id}/outputs", tags=["outputs"])
templates = Jinja2Templates(directory="app/templates")


@router.get("", response_class=HTMLResponse)
def outputs_index(request: Request, journey_id: str, db: Session = Depends(get_db), user: User = Depends(require_admin)) -> HTMLResponse:
    journey = _load_journey(db, journey_id)
    return templates.TemplateResponse("outputs/index.html", {"request": request, "journey": journey, "blockers": generation_blockers(journey), "user": user})


@router.post("/generate")
async def generate_outputs(journey_id: str, db: Session = Depends(get_db), user: User = Depends(require_admin)) -> RedirectResponse:
    settings = get_settings()
    journey = _load_journey(db, journey_id)
    if generation_blockers(journey):
        return RedirectResponse(f"/journeys/{journey_id}/outputs", status_code=303)
    version = (db.scalar(select(func.max(GeneratedOutput.version)).where(GeneratedOutput.journey_id == journey_id)) or 0) + 1
    output_dir = settings.generated_dir / f"{journey.date}_{journey.venue}_v{version}"
    output_dir.mkdir(parents=True, exist_ok=True)

    excel_path = output_dir / f"tips_{journey.venue}_{journey.date}_v{version}.xlsx"
    html_path = output_dir / f"pronosticos_{journey.venue}_{journey.date}_v{version}.html"
    png_path = output_dir / f"pronosticos_{journey.venue}_{journey.date}_v{version}.png"
    pdf_path = output_dir / f"pronosticos_{journey.venue}_{journey.date}_v{version}.pdf"

    generate_tips_excel(journey, excel_path, settings.templates_excel_dir / "Tips_base.xlsx")
    write_board_html(journey, settings, html_path)
    try:
        await export_board_png_pdf(html_path, png_path, pdf_path)
    except Exception:
        png_path.write_text("Playwright export failed. HTML preview is available.", encoding="utf-8")
        pdf_path.write_text("Playwright export failed. HTML preview is available.", encoding="utf-8")

    _add_output(db, journey, OutputType.TIPS_EXCEL, version, excel_path)
    _add_output(db, journey, OutputType.PRONOSTICOS_PNG, version, png_path)
    _add_output(db, journey, OutputType.PRONOSTICOS_PDF, version, pdf_path)
    journey.status = JourneyStatus.OUTPUTS_GENERATED
    db.commit()
    return RedirectResponse(f"/journeys/{journey_id}/outputs", status_code=303)


@router.post("/review")
def review_outputs(journey_id: str, db: Session = Depends(get_db), user: User = Depends(require_admin)) -> RedirectResponse:
    journey = _load_journey(db, journey_id)
    now = datetime.utcnow()
    for output in journey.outputs:
        output.status = OutputStatus.REVIEWED
        output.reviewed_at = now
    journey.reviewed_outputs_at = now
    journey.status = JourneyStatus.OUTPUTS_REVIEWED
    db.commit()
    return RedirectResponse(f"/journeys/{journey_id}/outputs", status_code=303)


def _load_journey(db: Session, journey_id: str) -> Journey:
    journey = db.scalar(
        select(Journey)
        .where(Journey.id == journey_id)
        .options(
            selectinload(Journey.races).selectinload(Race.participants),
            selectinload(Journey.predictions).selectinload(Prediction.picks),
            selectinload(Journey.predictions).selectinload(Prediction.specialist),
            selectinload(Journey.outputs),
        )
    )
    if journey is None:
        raise ValueError("Journey not found")
    return journey


def _add_output(db: Session, journey: Journey, output_type: OutputType, version: int, path: Path) -> None:
    checksum = hashlib.sha256(path.read_bytes()).hexdigest() if path.exists() else None
    db.add(GeneratedOutput(journey=journey, type=output_type, version=version, status=OutputStatus.GENERATED, local_path=str(path), checksum=checksum))
