"""initial schema

Revision ID: 0001_initial
Revises:
Create Date: 2026-06-30
"""

from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa

revision: str = "0001_initial"
down_revision: str | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "users",
        sa.Column("id", sa.String(length=36), primary_key=True),
        sa.Column("email", sa.String(length=255), nullable=False),
        sa.Column("password_hash", sa.String(length=255), nullable=False),
        sa.Column("role", sa.String(length=32), nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_users_email", "users", ["email"], unique=True)
    op.create_table(
        "specialists",
        sa.Column("id", sa.String(length=36), primary_key=True),
        sa.Column("name", sa.String(length=255), nullable=False, unique=True),
        sa.Column("display_order", sa.Integer(), nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False),
    )
    op.create_table(
        "journeys",
        sa.Column("id", sa.String(length=36), primary_key=True),
        sa.Column("date", sa.Date(), nullable=False),
        sa.Column("venue", sa.String(length=80), nullable=False),
        sa.Column("theme", sa.String(length=40), nullable=False),
        sa.Column("season_year", sa.Integer(), nullable=False),
        sa.Column("status", sa.String(length=40), nullable=False),
        sa.Column("pdf_original_filename", sa.String(length=255)),
        sa.Column("pdf_storage_path", sa.String(length=512)),
        sa.Column("partant_confirmed_at", sa.DateTime(timezone=True)),
        sa.Column("reviewed_outputs_at", sa.DateTime(timezone=True)),
        sa.Column("drive_uploaded_at", sa.DateTime(timezone=True)),
        sa.Column("email_sent_at", sa.DateTime(timezone=True)),
        sa.Column("created_by_user_id", sa.String(length=36), sa.ForeignKey("users.id")),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_journeys_date", "journeys", ["date"])
    op.create_table(
        "races",
        sa.Column("id", sa.String(length=36), primary_key=True),
        sa.Column("journey_id", sa.String(length=36), sa.ForeignKey("journeys.id"), nullable=False),
        sa.Column("race_number", sa.Integer(), nullable=False),
        sa.Column("name", sa.String(length=255)),
        sa.Column("scheduled_time", sa.Time()),
        sa.Column("distance_meters", sa.Integer()),
        sa.Column("surface", sa.String(length=80)),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint("journey_id", "race_number", name="uq_race_journey_number"),
    )
    op.create_table(
        "participants",
        sa.Column("id", sa.String(length=36), primary_key=True),
        sa.Column("race_id", sa.String(length=36), sa.ForeignKey("races.id"), nullable=False),
        sa.Column("number", sa.Integer(), nullable=False),
        sa.Column("horse_name", sa.String(length=255), nullable=False),
        sa.Column("raw_name", sa.String(length=255)),
        sa.Column("jockey", sa.String(length=255)),
        sa.Column("trainer", sa.String(length=255)),
        sa.Column("stall", sa.Integer()),
        sa.Column("is_active", sa.Boolean(), nullable=False),
        sa.UniqueConstraint("race_id", "number", name="uq_participant_race_number"),
    )
    op.create_table(
        "predictions",
        sa.Column("id", sa.String(length=36), primary_key=True),
        sa.Column("journey_id", sa.String(length=36), sa.ForeignKey("journeys.id"), nullable=False),
        sa.Column("specialist_id", sa.String(length=36), sa.ForeignKey("specialists.id"), nullable=False),
        sa.Column("raw_text", sa.Text(), nullable=False),
        sa.Column("normalized_json", sa.JSON()),
        sa.Column("status", sa.String(length=40), nullable=False),
        sa.Column("requires_human_review", sa.Boolean(), nullable=False),
        sa.Column("validation_errors", sa.JSON()),
        sa.Column("llm_provider", sa.String(length=80)),
        sa.Column("llm_model", sa.String(length=120)),
        sa.Column("llm_confidence", sa.Float()),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint("journey_id", "specialist_id", name="uq_prediction_journey_specialist"),
    )
    op.create_table(
        "prediction_picks",
        sa.Column("id", sa.String(length=36), primary_key=True),
        sa.Column("prediction_id", sa.String(length=36), sa.ForeignKey("predictions.id"), nullable=False),
        sa.Column("race_id", sa.String(length=36), sa.ForeignKey("races.id"), nullable=False),
        sa.Column("race_number", sa.Integer(), nullable=False),
        sa.Column("pick_1", sa.Integer(), nullable=False),
        sa.Column("pick_2", sa.Integer(), nullable=False),
        sa.Column("pick_3", sa.Integer(), nullable=False),
        sa.Column("confidence", sa.Float()),
        sa.Column("notes", sa.Text()),
        sa.UniqueConstraint("prediction_id", "race_id", name="uq_pick_prediction_race"),
    )
    op.create_table(
        "generated_outputs",
        sa.Column("id", sa.String(length=36), primary_key=True),
        sa.Column("journey_id", sa.String(length=36), sa.ForeignKey("journeys.id"), nullable=False),
        sa.Column("type", sa.String(length=60), nullable=False),
        sa.Column("version", sa.Integer(), nullable=False),
        sa.Column("status", sa.String(length=40), nullable=False),
        sa.Column("local_path", sa.String(length=512)),
        sa.Column("drive_file_id", sa.String(length=255)),
        sa.Column("drive_url", sa.String(length=512)),
        sa.Column("checksum", sa.String(length=128)),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("reviewed_at", sa.DateTime(timezone=True)),
        sa.Column("uploaded_at", sa.DateTime(timezone=True)),
        sa.Column("sent_at", sa.DateTime(timezone=True)),
        sa.UniqueConstraint("journey_id", "type", "version", name="uq_output_journey_type_version"),
    )
    op.create_table(
        "audit_events",
        sa.Column("id", sa.String(length=36), primary_key=True),
        sa.Column("journey_id", sa.String(length=36), sa.ForeignKey("journeys.id")),
        sa.Column("user_id", sa.String(length=36), sa.ForeignKey("users.id")),
        sa.Column("event_type", sa.String(length=120), nullable=False),
        sa.Column("payload", sa.JSON()),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )


def downgrade() -> None:
    op.drop_table("audit_events")
    op.drop_table("generated_outputs")
    op.drop_table("prediction_picks")
    op.drop_table("predictions")
    op.drop_table("participants")
    op.drop_table("races")
    op.drop_index("ix_journeys_date", table_name="journeys")
    op.drop_table("journeys")
    op.drop_table("specialists")
    op.drop_index("ix_users_email", table_name="users")
    op.drop_table("users")
