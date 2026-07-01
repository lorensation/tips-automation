import uuid
from sqlalchemy import Boolean, ForeignKey, Integer, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class Participant(Base):
    __tablename__ = "participants"
    __table_args__ = (UniqueConstraint("race_id", "number", name="uq_participant_race_number"),)

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    race_id: Mapped[str] = mapped_column(String(36), ForeignKey("races.id"), nullable=False)
    number: Mapped[int] = mapped_column(Integer, nullable=False)
    horse_name: Mapped[str] = mapped_column(String(255), nullable=False)
    raw_name: Mapped[str | None] = mapped_column(String(255))
    jockey: Mapped[str | None] = mapped_column(String(255))
    trainer: Mapped[str | None] = mapped_column(String(255))
    stall: Mapped[int | None] = mapped_column(Integer)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    race = relationship("Race", back_populates="participants")
