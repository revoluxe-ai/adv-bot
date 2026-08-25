"""Add shelf-exhausted pause SoT columns (INC-AUTO-SHELF-PAUSE-01).

Revision ID: e8f9a0b1c2d3
Revises: f2a3b4c5d6e7
Create Date: 2026-08-11

Change auto-shelf-exhausted-pause-retest / decision write-path:
PG canonical our-block / epoch / resolve CPO / due / retest interval days.
Redis Auto-lane reason remains mirror only.
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "e8f9a0b1c2d3"
down_revision: Union[str, None] = "f2a3b4c5d6e7"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "auto_shelf_bid_control_settings",
        sa.Column(
            "retest_interval_days",
            sa.Integer(),
            server_default=sa.text("7"),
            nullable=False,
            comment=(
                "Календарный интервал суток до clear our-block shelf-exhausted "
                "(product default 7; INC-AUTO-SHELF-PAUSE-01)."
            ),
        ),
    )
    op.create_check_constraint(
        "ck_asbcs_retest_interval_days_min_1",
        "auto_shelf_bid_control_settings",
        "retest_interval_days >= 1",
    )

    op.add_column(
        "auto_shelf_bid_control_state",
        sa.Column(
            "shelf_exhausted_pause_active",
            sa.Boolean(),
            server_default=sa.text("false"),
            nullable=False,
            comment="Our-block: shelf-exhausted pause SoT (PG canonical).",
        ),
    )
    op.add_column(
        "auto_shelf_bid_control_state",
        sa.Column(
            "shelf_exhausted_paused_at",
            sa.DateTime(timezone=True),
            nullable=True,
        ),
    )
    op.add_column(
        "auto_shelf_bid_control_state",
        sa.Column(
            "shelf_exhausted_due_at",
            sa.DateTime(timezone=True),
            nullable=True,
            comment="Календарный due clear our-block.",
        ),
    )
    op.add_column(
        "auto_shelf_bid_control_state",
        sa.Column(
            "shelf_exhausted_epoch_start",
            sa.DateTime(timezone=True),
            nullable=True,
            comment="Старт эпохи покрытия; пишется при реальном Auto start.",
        ),
    )
    op.add_column(
        "auto_shelf_bid_control_state",
        sa.Column(
            "shelf_exhausted_resolve_cpo_kind",
            sa.String(length=16),
            nullable=True,
            comment="target|max — какой resolve CPO зафиксировали при latch.",
        ),
    )
    op.add_column(
        "auto_shelf_bid_control_state",
        sa.Column(
            "shelf_exhausted_resolve_cpo_value",
            sa.Float(),
            nullable=True,
        ),
    )
    op.add_column(
        "auto_shelf_bid_control_state",
        sa.Column(
            "shelf_exhausted_notify_sent_at",
            sa.DateTime(timezone=True),
            nullable=True,
            comment="Дедуп paid notify при enter pause.",
        ),
    )
    op.add_column(
        "auto_shelf_bid_control_state",
        sa.Column(
            "shelf_exhausted_epoch_pending",
            sa.Boolean(),
            server_default=sa.text("false"),
            nullable=False,
            comment=(
                "True после clear our-block: следующая реальная Auto start "
                "открывает новую эпоху покрытия."
            ),
        ),
    )
    op.create_check_constraint(
        "ck_asbcs_state_shelf_exhausted_resolve_cpo_kind",
        "auto_shelf_bid_control_state",
        "shelf_exhausted_resolve_cpo_kind IS NULL OR "
        "shelf_exhausted_resolve_cpo_kind IN ('target', 'max')",
    )


def downgrade() -> None:
    op.drop_constraint(
        "ck_asbcs_state_shelf_exhausted_resolve_cpo_kind",
        "auto_shelf_bid_control_state",
        type_="check",
    )
    op.drop_column("auto_shelf_bid_control_state", "shelf_exhausted_epoch_pending")
    op.drop_column("auto_shelf_bid_control_state", "shelf_exhausted_notify_sent_at")
    op.drop_column("auto_shelf_bid_control_state", "shelf_exhausted_resolve_cpo_value")
    op.drop_column("auto_shelf_bid_control_state", "shelf_exhausted_resolve_cpo_kind")
    op.drop_column("auto_shelf_bid_control_state", "shelf_exhausted_epoch_start")
    op.drop_column("auto_shelf_bid_control_state", "shelf_exhausted_due_at")
    op.drop_column("auto_shelf_bid_control_state", "shelf_exhausted_paused_at")
    op.drop_column("auto_shelf_bid_control_state", "shelf_exhausted_pause_active")
    op.drop_constraint(
        "ck_asbcs_retest_interval_days_min_1",
        "auto_shelf_bid_control_settings",
        type_="check",
    )
    op.drop_column("auto_shelf_bid_control_settings", "retest_interval_days")
