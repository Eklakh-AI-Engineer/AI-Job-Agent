"""Add application workflow: events audit log + status lifecycle columns

Revision ID: c7d4e1a9f2b8
Revises: b3f8c2d9e1a4
Create Date: 2026-10-06 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "c7d4e1a9f2b8"
down_revision: Union[str, None] = "b3f8c2d9e1a4"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # --- Extend application_statuses ---
    op.add_column(
        "application_statuses",
        sa.Column("approved_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.add_column(
        "application_statuses",
        sa.Column("applied_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.add_column(
        "application_statuses",
        sa.Column("rejected_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.add_column(
        "application_statuses",
        sa.Column("idempotency_key", sa.String(length=255), nullable=True),
    )
    op.add_column(
        "application_statuses",
        sa.Column("last_error", sa.Text(), nullable=True),
    )
    op.add_column(
        "application_statuses",
        sa.Column("notes", sa.Text(), nullable=True),
    )
    op.create_index(
        op.f("ix_application_statuses_status"),
        "application_statuses",
        ["status"],
        unique=False,
    )
    op.create_index(
        op.f("ix_application_statuses_idempotency_key"),
        "application_statuses",
        ["idempotency_key"],
        unique=True,
    )
    op.create_unique_constraint(
        "uq_application_user_job",
        "application_statuses",
        ["user_id", "job_posting_id"],
    )

    # --- Create application_events audit log ---
    op.create_table(
        "application_events",
        sa.Column("application_id", sa.Integer(), nullable=False),
        sa.Column("from_status", sa.String(length=50), nullable=True),
        sa.Column("to_status", sa.String(length=50), nullable=False),
        sa.Column("actor", sa.String(length=255), nullable=False, server_default="system"),
        sa.Column("reason", sa.Text(), nullable=True),
        sa.Column("idempotency_key", sa.String(length=255), nullable=True),
        sa.Column("event_meta", sa.JSON(), nullable=True),
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(
            ["application_id"], ["application_statuses.id"], ondelete="CASCADE"
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        op.f("ix_application_events_application_id"),
        "application_events",
        ["application_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_application_events_to_status"),
        "application_events",
        ["to_status"],
        unique=False,
    )
    op.create_index(
        op.f("ix_application_events_idempotency_key"),
        "application_events",
        ["idempotency_key"],
        unique=False,
    )
    op.create_index(
        op.f("ix_application_events_id"), "application_events", ["id"], unique=False
    )


def downgrade() -> None:
    op.drop_index(op.f("ix_application_events_id"), table_name="application_events")
    op.drop_index(
        op.f("ix_application_events_idempotency_key"), table_name="application_events"
    )
    op.drop_index(
        op.f("ix_application_events_to_status"), table_name="application_events"
    )
    op.drop_index(
        op.f("ix_application_events_application_id"), table_name="application_events"
    )
    op.drop_table("application_events")

    op.drop_constraint(
        "uq_application_user_job", "application_statuses", type_="unique"
    )
    op.drop_index(
        op.f("ix_application_statuses_idempotency_key"),
        table_name="application_statuses",
    )
    op.drop_index(
        op.f("ix_application_statuses_status"), table_name="application_statuses"
    )
    op.drop_column("application_statuses", "notes")
    op.drop_column("application_statuses", "last_error")
    op.drop_column("application_statuses", "idempotency_key")
    op.drop_column("application_statuses", "rejected_at")
    op.drop_column("application_statuses", "applied_at")
    op.drop_column("application_statuses", "approved_at")