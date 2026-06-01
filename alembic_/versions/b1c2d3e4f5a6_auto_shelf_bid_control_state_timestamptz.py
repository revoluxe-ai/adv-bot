"""auto_shelf_bid_control: TIMESTAMP WITH TIME ZONE для полей state/settings.

Revision ID: b1c2d3e4f5a6
Revises: f47fe215715b
Create Date: 2026-05-25 13:30:00.000000

asyncpg не принимает timezone-aware datetime в TIMESTAMP WITHOUT TIME ZONE;
control-manager пишет datetime.now(timezone.utc).
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "b1c2d3e4f5a6"
down_revision: Union[str, None] = "f47fe215715b"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

_STATE_TS_COLUMNS = (
    "current_cycle_started_at",
    "previous_cycle_started_at",
    "main_started_at",
    "test_started_at",
    "created_at",
    "updated_at",
)

_SETTINGS_TS_COLUMNS = ("created_at", "updated_at")


def _alter_to_timestamptz(table: str, column: str, *, nullable: bool) -> None:
    op.alter_column(
        table,
        column,
        existing_type=postgresql.TIMESTAMP(),
        type_=sa.DateTime(timezone=True),
        existing_nullable=nullable,
        postgresql_using=f"{column} AT TIME ZONE 'UTC'",
    )


def _alter_to_timestamp(table: str, column: str, *, nullable: bool) -> None:
    op.alter_column(
        table,
        column,
        existing_type=sa.DateTime(timezone=True),
        type_=postgresql.TIMESTAMP(),
        existing_nullable=nullable,
    )


def upgrade() -> None:
    for column in _STATE_TS_COLUMNS:
        _alter_to_timestamptz(
            "auto_shelf_bid_control_state",
            column,
            nullable=column not in {
                "current_cycle_started_at",
                "created_at",
                "updated_at",
            },
        )
    for column in _SETTINGS_TS_COLUMNS:
        _alter_to_timestamptz(
            "auto_shelf_bid_control_settings",
            column,
            nullable=False,
        )


def downgrade() -> None:
    for column in reversed(_SETTINGS_TS_COLUMNS):
        _alter_to_timestamp(
            "auto_shelf_bid_control_settings",
            column,
            nullable=False,
        )
    for column in reversed(_STATE_TS_COLUMNS):
        _alter_to_timestamp(
            "auto_shelf_bid_control_state",
            column,
            nullable=column not in {
                "current_cycle_started_at",
                "created_at",
                "updated_at",
            },
        )
