import uuid
from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Integer, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base
from app.enums import OutputStatus, OutputType
from app.utils import utcnow


class GeneratedOutput(Base):
    __tablename__ = "generated_outputs"
    __table_args__ = (UniqueConstraint("journey_id", "type", "version", name="uq_output_journey_type_version"),)

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    journey_id: Mapped[str] = mapped_column(String(36), ForeignKey("journeys.id"), nullable=False)
    type: Mapped[OutputType] = mapped_column(String(60), nullable=False)
    version: Mapped[int] = mapped_column(Integer, nullable=False)
    status: Mapped[OutputStatus] = mapped_column(String(40), default=OutputStatus.GENERATED, nullable=False)
    local_path: Mapped[str | None] = mapped_column(String(512))
    drive_file_id: Mapped[str | None] = mapped_column(String(255))
    drive_url: Mapped[str | None] = mapped_column(String(512))
    checksum: Mapped[str | None] = mapped_column(String(128))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, nullable=False)
    reviewed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    uploaded_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    sent_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    journey = relationship("Journey", back_populates="outputs")
