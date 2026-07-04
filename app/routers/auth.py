import logging

from fastapi import APIRouter, Depends, Form
from fastapi.responses import HTMLResponse, RedirectResponse
from sqlalchemy import select
from sqlalchemy.orm import Session
from starlette.requests import Request

from app.auth import SESSION_USER_ID, verify_password
from app.config import get_settings
from app.database import get_db
from app.models.user import User
from app.security import login_rate_limiter, verify_csrf
from app.templating import templates

logger = logging.getLogger(__name__)

router = APIRouter(dependencies=[Depends(verify_csrf)])


def _client_key(request: Request) -> str:
    return request.client.host if request.client else "unknown"


@router.get("/", include_in_schema=False)
def root() -> RedirectResponse:
    return RedirectResponse("/journeys", status_code=303)


@router.get("/login", response_class=HTMLResponse)
def login_form(request: Request) -> HTMLResponse:
    return templates.TemplateResponse("login.html", {"request": request, "error": None})


@router.post("/login")
def login(request: Request, email: str = Form(...), password: str = Form(...), db: Session = Depends(get_db)):
    settings = get_settings()
    login_rate_limiter.max_attempts = settings.login_max_attempts
    login_rate_limiter.window_seconds = settings.login_window_seconds
    key = _client_key(request)
    if login_rate_limiter.is_blocked(key):
        logger.warning("Login blocked by rate limit for %s", key)
        return templates.TemplateResponse(
            "login.html",
            {"request": request, "error": "Demasiados intentos fallidos. Espera unos minutos y vuelve a intentarlo."},
            status_code=429,
        )
    user = db.scalar(select(User).where(User.email == email, User.is_active.is_(True)))
    if user is None or not verify_password(password, user.password_hash):
        login_rate_limiter.register_failure(key)
        logger.info("Failed login attempt for %s from %s", email, key)
        return templates.TemplateResponse("login.html", {"request": request, "error": "Credenciales incorrectas."}, status_code=400)
    login_rate_limiter.reset(key)
    request.session[SESSION_USER_ID] = user.id
    logger.info("User %s logged in", user.email)
    return RedirectResponse("/journeys", status_code=303)


@router.post("/logout")
def logout(request: Request) -> RedirectResponse:
    request.session.clear()
    return RedirectResponse("/login", status_code=303)
