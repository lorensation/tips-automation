from datetime import date

from fastapi import APIRouter, Depends, Form
from fastapi.responses import HTMLResponse, RedirectResponse
from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload
from starlette.requests import Request

from app.database import get_db
from app.dependencies import current_user, require_admin
from app.enums import JourneyStatus, VENUE_THEMES
from app.models.journey import Journey
from app.models.user import User
from app.security import verify_csrf
from app.templating import templates

router = APIRouter(prefix="/journeys", tags=["journeys"], dependencies=[Depends(verify_csrf)])


@router.get("", response_class=HTMLResponse)
def list_journeys(request: Request, db: Session = Depends(get_db), user: User = Depends(current_user)) -> HTMLResponse:
    journeys = db.scalars(select(Journey).order_by(Journey.date.desc(), Journey.created_at.desc())).all()
    return templates.TemplateResponse("journeys/list.html", {"request": request, "journeys": journeys, "user": user})


@router.get("/new", response_class=HTMLResponse)
def new_journey(request: Request, user: User = Depends(require_admin)) -> HTMLResponse:
    return templates.TemplateResponse("journeys/new.html", {"request": request, "venues": VENUE_THEMES, "user": user})


@router.post("")
def create_journey(
    journey_date: date = Form(...),
    venue: str = Form(...),
    db: Session = Depends(get_db),
    user: User = Depends(require_admin),
) -> RedirectResponse:
    theme = VENUE_THEMES.get(venue, "blue")
    journey = Journey(
        date=journey_date,
        venue=venue,
        theme=theme,
        season_year=journey_date.year,
        status=JourneyStatus.DRAFT,
        created_by_user_id=user.id,
    )
    db.add(journey)
    db.commit()
    return RedirectResponse(f"/journeys/{journey.id}", status_code=303)


@router.get("/{journey_id}", response_class=HTMLResponse)
def journey_detail(request: Request, journey_id: str, db: Session = Depends(get_db), user: User = Depends(current_user)) -> HTMLResponse:
    journey = db.scalar(
        select(Journey)
        .where(Journey.id == journey_id)
        .options(
            selectinload(Journey.races),
            selectinload(Journey.predictions),
            selectinload(Journey.outputs),
        )
    )
    if journey is None:
        return templates.TemplateResponse("404.html", {"request": request}, status_code=404)
    error_messages = {
        "pdf_type": "El archivo subido no parece un PDF válido.",
        "pdf_size": "El PDF supera el tamaño máximo permitido.",
        "partant_parse_empty": "No se encontraron carreras en el PDF. Revisa que sea el PDF de participantes definitivos.",
        "partant_parse_invalid": "El parser encontró carreras o participantes duplicados/inválidos. Revisa el log y vuelve a subir el PDF.",
    }
    error_code = request.query_params.get("error")
    return templates.TemplateResponse(
        "journeys/detail.html",
        {
            "request": request,
            "journey": journey,
            "user": user,
            "error_message": error_messages.get(error_code),
        },
    )
