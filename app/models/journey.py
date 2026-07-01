import uuid
from datetime import date, datetime

from sqlalchemy import Date, DateTime, ForeignKey, Integer, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base
from app.enums import JourneyStatus


class Journey(Base):
    __tablename__ = "journeys"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    date: Mapped[date] = mapped_column(Date, nullable=False, index=True)
    venue: Mapped[str] = mapped_column(String(80), nullable=False)
    theme: Mapped[str] = mapped_column(String(40), nullable=False)
    season_year: Mapped[int] = mapped_column(Integer, nullable=False)
    status: Mapped[JourneyStatus] = mapped_column(String(40), default=JourneyStatus.DRAFT, nullable=False)
    pdf_original_filename: Mapped[str | None] = mapped_column(String(255))
    pdf_storage_path: Mapped[str | None] = mapped_column(String(512))
    partant_confirmed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    reviewed_outputs_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    drive_uploaded_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    email_sent_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    created_by_user_id: Mapped[str | None] = mapped_column(String(36), ForeignKey("users.id"))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    races = relationship("Race", back_populates="journey", cascade="all, delete-orphan", order_by="Race.race_number")
    predictions = relationship("Prediction", back_populates="journey", cascade="all, delete-orphan")
    outputs = relationship("GeneratedOutput", back_populates="journey", cascade="all, delete-orphan")
