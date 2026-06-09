"""Implement plan distance auto shelf test module

Revision ID: 0e751bf6aac5
Revises: 00c31fb900b0
Create Date: 2026-06-07 18:42:55.532831
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision: str = "0e751bf6aac5"
down_revision: Union[str, None] = "00c31fb900b0"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


auto_shelf_bid_control_strategy_enum = postgresql.ENUM(
    "cycle_metric",
    "plan_distance",
    name="auto_shelf_bid_control_strategy",
    create_type=False,
)


def upgrade() -> None:
    bind = op.get_bind()

    auto_shelf_bid_control_strategy_enum.create(bind, checkfirst=True)

    op.add_column(
        "advsetting",
        sa.Column(
            "auto_shelf_bid_control_strategy",
            auto_shelf_bid_control_strategy_enum,
            nullable=True,
            server_default="plan_distance",
            comment=(
                "Стратегия выбора main bid для auto_shelf_bid_control: "
                "cycle_metric | plan_distance"
            ),
        ),
    )


def downgrade() -> None:
    bind = op.get_bind()

    op.drop_column("advsetting", "auto_shelf_bid_control_strategy")

    auto_shelf_bid_control_strategy_enum.drop(bind, checkfirst=True)
