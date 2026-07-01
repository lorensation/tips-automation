from sqlalchemy.orm import Session

from app.models.audit_event import AuditEvent


def record_event(db: Session, event_type: str, journey_id: str | None = None, user_id: str | None = None, payload: dict | None = None) -> None:
    db.add(AuditEvent(event_type=event_type, journey_id=journey_id, user_id=user_id, payload=payload or {}))
