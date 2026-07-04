import hmac
import logging
import re
import secrets
import time
from pathlib import Path

from fastapi import HTTPException, status
from starlette.requests import Request

logger = logging.getLogger(__name__)

CSRF_SESSION_KEY = "csrf_token"
CSRF_FORM_FIELD = "csrf_token"

_UNSAFE_FILENAME_CHARS = re.compile(r"[^A-Za-z0-9 ._-]")


def get_csrf_token(request: Request) -> str:
    token = request.session.get(CSRF_SESSION_KEY)
    if not token:
        token = secrets.token_urlsafe(32)
        request.session[CSRF_SESSION_KEY] = token
    return token


async def verify_csrf(request: Request) -> None:
    if request.method not in {"POST", "PUT", "PATCH", "DELETE"}:
        return
    form = await request.form()
    submitted = str(form.get(CSRF_FORM_FIELD, ""))
    expected = request.session.get(CSRF_SESSION_KEY, "")
    if not expected or not hmac.compare_digest(submitted, expected):
        logger.warning("CSRF verification failed for %s %s", request.method, request.url.path)
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="CSRF token inválido")


def sanitize_filename(name: str | None, fallback: str = "archivo.pdf") -> str:
    if not name:
        return fallback
    cleaned = _UNSAFE_FILENAME_CHARS.sub("_", Path(name).name).strip(" .")
    if not cleaned or set(cleaned) <= {"_"}:
        return fallback
    return cleaned[:120]


class LoginRateLimiter:
    """In-memory sliding-window limiter; enough for a single uvicorn process."""

    def __init__(self, max_attempts: int = 5, window_seconds: int = 300) -> None:
        self.max_attempts = max_attempts
        self.window_seconds = window_seconds
        self._failures: dict[str, list[float]] = {}

    def _prune(self, key: str) -> list[float]:
        cutoff = time.monotonic() - self.window_seconds
        attempts = [moment for moment in self._failures.get(key, []) if moment > cutoff]
        if attempts:
            self._failures[key] = attempts
        else:
            self._failures.pop(key, None)
        return attempts

    def is_blocked(self, key: str) -> bool:
        return len(self._prune(key)) >= self.max_attempts

    def register_failure(self, key: str) -> None:
        self._prune(key)
        self._failures.setdefault(key, []).append(time.monotonic())

    def reset(self, key: str) -> None:
        self._failures.pop(key, None)


login_rate_limiter = LoginRateLimiter()
