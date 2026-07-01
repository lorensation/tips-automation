import uuid
from datetime import datetime, time

from sqlalchemy import DateTime, ForeignKey, Integer, String, Time, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class Race(Base):
    __tablename__ = "races"
    __table_args__ = (UniqueConstraint("journey_id", "race_number", name="uq_race_journey_number"),)

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    journey_id: Mapped[str] = mapped_column(String(36), ForeignKey("journeys.id"), nullable=False)
    race_number: Mapped[int] = mapped_column(Integer, nullable=False)
    name: Mapped[str | None] = mapped_column(String(255))
    scheduled_time: Mapped[time | None] = mapped_column(Time)
    distance_meters: Mapped[int | None] = mapped_column(Integer)
    surface: Mapped[str | None] = mapped_column(String(80))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow, nullable=False)

    journey = relationship("Journey", back_populates="races")
    participants = relationship("Participant", back_populates="race", cascade="all, delete-orphan", order_by="Participant.number")
