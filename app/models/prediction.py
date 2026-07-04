import uuid
from datetime import datetime

from sqlalchemy import DateTime, Float, ForeignKey, Integer, JSON, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base
from app.enums import PredictionStatus
from app.utils import utcnow


class Prediction(Base):
    __tablename__ = "predictions"
    __table_args__ = (UniqueConstraint("journey_id", "specialist_id", name="uq_prediction_journey_specialist"),)

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    journey_id: Mapped[str] = mapped_column(String(36), ForeignKey("journeys.id"), nullable=False)
    specialist_id: Mapped[str] = mapped_column(String(36), ForeignKey("specialists.id"), nullable=False)
    raw_text: Mapped[str] = mapped_column(Text, default="", nullable=False)
    normalized_json: Mapped[dict | None] = mapped_column(JSON)
    status: Mapped[PredictionStatus] = mapped_column(String(40), default=PredictionStatus.MISSING, nullable=False)
    requires_human_review: Mapped[bool] = mapped_column(default=False, nullable=False)
    validation_errors: Mapped[list | None] = mapped_column(JSON)
    llm_provider: Mapped[str | None] = mapped_column(String(80))
    llm_model: Mapped[str | None] = mapped_column(String(120))
    llm_confidence: Mapped[float | None] = mapped_column(Float)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, onupdate=utcnow, nullable=False)

    journey = relationship("Journey", back_populates="predictions")
    specialist = relationship("Specialist")
    picks = relationship("PredictionPick", back_populates="prediction", cascade="all, delete-orphan", order_by="PredictionPick.race_number")


class PredictionPick(Base):
    __tablename__ = "prediction_picks"
    __table_args__ = (UniqueConstraint("prediction_id", "race_id", name="uq_pick_prediction_race"),)

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    prediction_id: Mapped[str] = mapped_column(String(36), ForeignKey("predictions.id"), nullable=False)
    race_id: Mapped[str] = mapped_column(String(36), ForeignKey("races.id"), nullable=False)
    race_number: Mapped[int] = mapped_column(Integer, nullable=False)
    pick_1: Mapped[int] = mapped_column(Integer, nullable=False)
    pick_2: Mapped[int] = mapped_column(Integer, nullable=False)
    pick_3: Mapped[int] = mapped_column(Integer, nullable=False)
    confidence: Mapped[float | None] = mapped_column(Float)
    notes: Mapped[str | None] = mapped_column(Text)

    prediction = relationship("Prediction", back_populates="picks")
    race = relationship("Race")
