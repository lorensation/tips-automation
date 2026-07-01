from passlib.context import CryptContext
from passlib.exc import UnknownHashError
from sqlalchemy import select
from sqlalchemy.orm import Session
from starlette.requests import Request

from app.models.user import User

pwd_context = CryptContext(schemes=["pbkdf2_sha256"], deprecated="auto")
SESSION_USER_ID = "user_id"


def hash_password(password: str) -> str:
    return pwd_context.hash(password)


def is_supported_password_hash(value: str | None) -> bool:
    if not value:
        return False
    return pwd_context.identify(value) is not None


def verify_password(password: str, password_hash: str) -> bool:
    if not password_hash:
        return False
    try:
        return pwd_context.verify(password, password_hash)
    except (UnknownHashError, ValueError, TypeError):
        return False


def get_user_from_session(request: Request, db: Session) -> User | None:
    user_id = request.session.get(SESSION_USER_ID)
    if not user_id:
        return None
    return db.scalar(select(User).where(User.id == user_id, User.is_active.is_(True)))
