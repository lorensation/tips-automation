from pathlib import Path

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from starlette.middleware.sessions import SessionMiddleware

from app.config import get_settings
from app.database import Base, SessionLocal, engine
from app.enums import SPECIALIST_NAMES, UserRole
from app.auth import hash_password
from app.models import Specialist, User  # noqa: F401
from app.routers import auth, integrations, journeys, outputs, partant, predictions


def create_app() -> FastAPI:
    settings = get_settings()
    app = FastAPI(title="Hipódromo Tips Agent")
    app.add_middleware(
        SessionMiddleware,
        secret_key=settings.app_secret_key,
        https_only=settings.is_production,
        same_site="lax",
    )
    Path("app/static").mkdir(parents=True, exist_ok=True)
    app.mount("/static", StaticFiles(directory="app/static"), name="static")

    app.include_router(auth.router)
    app.include_router(journeys.router)
    app.include_router(partant.router)
    app.include_router(predictions.router)
    app.include_router(outputs.router)
    app.include_router(integrations.router)

    @app.on_event("startup")
    def startup() -> None:
        settings.upload_dir.mkdir(exist_ok=True)
        settings.generated_dir.mkdir(exist_ok=True)
        Base.metadata.create_all(bind=engine)
        _seed_reference_data()

    @app.get("/healthz")
    def healthz() -> dict[str, str]:
        return {"status": "ok"}

    return app


def _seed_reference_data() -> None:
    settings = get_settings()
    with SessionLocal() as db:
        for index, name in enumerate(SPECIALIST_NAMES, start=1):
            if not db.query(Specialist).filter(Specialist.name == name).first():
                db.add(Specialist(name=name, display_order=index))
        if settings.admin_email and not db.query(User).filter(User.email == settings.admin_email).first():
            password_hash = settings.admin_password_hash
            if not password_hash and settings.app_env == "local":
                password_hash = hash_password("admin")
            if password_hash:
                db.add(User(email=settings.admin_email, password_hash=password_hash, role=UserRole.ADMIN))
        db.commit()


app = create_app()
