"""Add A/B Hold epoch lifecycle columns to AdvSetting

Revision ID: d0e1f2a3b4c5
Revises: c9d0e1f2a3b4
Create Date: 2026-07-23

Spec card-ab-hold-mode §18.5/§19.5/§22.5: epoch phase, WARM_UP timer, generation,
idempotency key, PENDING intent, sync status, confirmed-params SoT.

Migration defaults MUST NOT activate epoch lifecycle on existing rows:
- card_ab_hold_phase NULL = legacy MVP-1
- generation 0 / sync_status 'none' / no intent / no confirmed params
Downgrade MUST NOT drop legacy mode/snapshot/degraded columns.
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision: str = "d0e1f2a3b4c5"
down_revision: Union[str, None] = "c9d0e1f2a3b4"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "advsetting",
        sa.Column(
            "card_ab_hold_phase",
            sa.String(length=64),
            nullable=True,
            comment=(
                "A/B Hold epoch phase: NULL=legacy MVP-1; non-NULL=epoch-managed "
                "(awaiting_keyword_confirm|warm_up|…|ready_active)"
            ),
        ),
    )
    op.add_column(
        "advsetting",
        sa.Column(
            "card_ab_hold_warmup_started_at",
            sa.DateTime(timezone=True),
            nullable=True,
            comment="A/B Hold WARM_UP timer start (timestamptz)",
        ),
    )
    op.add_column(
        "advsetting",
        sa.Column(
            "card_ab_hold_warmup_duration_hours",
            sa.Integer(),
            server_default=sa.text("24"),
            nullable=False,
            comment="A/B Hold WARM_UP duration hours (default/min 24)",
        ),
    )
    op.add_column(
        "advsetting",
        sa.Column(
            "card_ab_hold_generation",
            sa.Integer(),
            server_default=sa.text("0"),
            nullable=False,
            comment="A/B Hold epoch generation (monotonic; 0=no epoch)",
        ),
    )
    op.add_column(
        "advsetting",
        sa.Column(
            "card_ab_hold_wb_sync_idempotency_key",
            sa.String(length=128),
            nullable=True,
            comment="A/B Hold WB sync idempotency key '{adv_id}:{generation}'",
        ),
    )
    op.create_unique_constraint(
        "uq_advsetting_card_ab_hold_wb_sync_idempotency_key",
        "advsetting",
        ["card_ab_hold_wb_sync_idempotency_key"],
    )
    op.add_column(
        "advsetting",
        sa.Column(
            "card_ab_hold_pending_intent_json",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=True,
            comment="A/B Hold durable PENDING intent snapshot",
        ),
    )
    op.add_column(
        "advsetting",
        sa.Column(
            "card_ab_hold_sync_status",
            sa.String(length=32),
            server_default=sa.text("'none'"),
            nullable=False,
            comment="A/B Hold WB sync status: none|pending|partial|complete",
        ),
    )
    op.add_column(
        "advsetting",
        sa.Column(
            "card_ab_hold_confirmed_keywords_json",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=True,
            comment="A/B Hold confirmed keyword set",
        ),
    )
    op.add_column(
        "advsetting",
        sa.Column(
            "card_ab_hold_confirmed_target_places_json",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=True,
            comment="A/B Hold confirmed target places map",
        ),
    )
    op.add_column(
        "advsetting",
        sa.Column(
            "card_ab_hold_confirmed_auto_participation",
            sa.Boolean(),
            nullable=True,
            comment="A/B Hold confirmed Auto participation",
        ),
    )
    op.add_column(
        "advsetting",
        sa.Column(
            "card_ab_hold_confirmed_auto_bid",
            sa.Float(),
            nullable=True,
            comment="A/B Hold confirmed Auto bid",
        ),
    )
    op.create_check_constraint(
        "ck_advsetting_card_ab_hold_warmup_duration_hours_min",
        "advsetting",
        "card_ab_hold_warmup_duration_hours >= 24",
    )


def downgrade() -> None:
    op.drop_constraint(
        "ck_advsetting_card_ab_hold_warmup_duration_hours_min",
        "advsetting",
        type_="check",
    )
    op.drop_constraint(
        "uq_advsetting_card_ab_hold_wb_sync_idempotency_key",
        "advsetting",
        type_="unique",
    )
    op.drop_column("advsetting", "card_ab_hold_confirmed_auto_bid")
    op.drop_column("advsetting", "card_ab_hold_confirmed_auto_participation")
    op.drop_column("advsetting", "card_ab_hold_confirmed_target_places_json")
    op.drop_column("advsetting", "card_ab_hold_confirmed_keywords_json")
    op.drop_column("advsetting", "card_ab_hold_sync_status")
    op.drop_column("advsetting", "card_ab_hold_pending_intent_json")
    op.drop_column("advsetting", "card_ab_hold_wb_sync_idempotency_key")
    op.drop_column("advsetting", "card_ab_hold_generation")
    op.drop_column("advsetting", "card_ab_hold_warmup_duration_hours")
    op.drop_column("advsetting", "card_ab_hold_warmup_started_at")
    op.drop_column("advsetting", "card_ab_hold_phase")
