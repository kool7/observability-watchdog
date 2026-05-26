"""init_tables

Revision ID: 0001
Revises:
Create Date: 2026-05-26

"""

from typing import Sequence, Union

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

revision: str = "0001"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "log_entries",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("service_name", sa.String(100), nullable=False),
        sa.Column("level", sa.String(20), nullable=False),
        sa.Column("message", sa.Text(), nullable=False),
        sa.Column("timestamp", sa.DateTime(timezone=True), nullable=False),
        sa.Column("metadata", postgresql.JSON(astext_type=sa.Text()), nullable=True),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_log_entries_service_name", "log_entries", ["service_name"])
    op.create_index("ix_log_entries_level", "log_entries", ["level"])
    op.create_index("ix_log_entries_timestamp", "log_entries", ["timestamp"])

    op.create_table(
        "anomalies",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("service_name", sa.String(100), nullable=False),
        sa.Column("detected_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("window_start", sa.DateTime(timezone=True), nullable=False),
        sa.Column("window_end", sa.DateTime(timezone=True), nullable=False),
        sa.Column("error_count", sa.Integer(), nullable=False),
        sa.Column("z_score", sa.Float(), nullable=False),
        sa.Column("threshold_breached", sa.Float(), nullable=False),
        sa.Column("ai_narrative", sa.Text(), nullable=True),
        sa.Column("severity", sa.String(20), nullable=False),
        sa.Column(
            "webhook_fired", sa.Boolean(), nullable=False, server_default="false"
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_anomalies_service_name", "anomalies", ["service_name"])
    op.create_index("ix_anomalies_detected_at", "anomalies", ["detected_at"])

    op.create_table(
        "webhook_events",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("anomaly_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("fired_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("payload", postgresql.JSON(astext_type=sa.Text()), nullable=False),
        sa.Column("response_status", sa.Integer(), nullable=False),
        sa.ForeignKeyConstraint(["anomaly_id"], ["anomalies.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_webhook_events_anomaly_id", "webhook_events", ["anomaly_id"])
    op.create_index("ix_webhook_events_fired_at", "webhook_events", ["fired_at"])


def downgrade() -> None:
    op.drop_table("webhook_events")
    op.drop_table("anomalies")
    op.drop_table("log_entries")
