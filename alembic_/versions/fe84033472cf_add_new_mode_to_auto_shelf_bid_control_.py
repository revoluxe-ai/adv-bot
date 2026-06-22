"""Add new mode to auto_shelf_bid_control_strategy

Revision ID: fe84033472cf
Revises: 250ee8ae5c45
Create Date: 2026-06-22 02:06:34.551260
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = "fe84033472cf"
down_revision: Union[str, None] = "250ee8ae5c45"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


OLD_COMMENT = (
    "Стратегия выбора main bid для auto_shelf_bid_control: "
    "cycle_metric | plan_distance. "
    "auto_shelf_bid_control_strategy defaults to plan_distance intentionally. "
    "At the moment auto_shelf_bid_control is enabled only for controlled shelf-test campaigns. "
    "Legacy bidder paths do not read this field."
)

NEW_COMMENT = (
    "Стратегия выбора main bid для auto_shelf_bid_control: "
    "plan_distance | ctr | cpc. "
    "Legacy cycle_metric values are migrated to plan_distance. "
    "auto_shelf_bid_control_strategy defaults to plan_distance intentionally. "
    "At the moment auto_shelf_bid_control is enabled only for controlled shelf-test campaigns. "
    "Legacy bidder paths do not read this field."
)


def upgrade() -> None:
    with op.get_context().autocommit_block():
        op.execute(
            "ALTER TYPE auto_shelf_bid_control_strategy "
            "ADD VALUE IF NOT EXISTS 'ctr'"
        )
        op.execute(
            "ALTER TYPE auto_shelf_bid_control_strategy "
            "ADD VALUE IF NOT EXISTS 'cpc'"
        )

    op.execute(
        """
        UPDATE advsetting
        SET auto_shelf_bid_control_strategy = 'plan_distance'
        WHERE auto_shelf_bid_control_strategy = 'cycle_metric'
        """
    )

    op.alter_column(
        "advsetting",
        "auto_shelf_bid_control_strategy",
        existing_type=postgresql.ENUM(
            "cycle_metric",
            "plan_distance",
            "ctr",
            "cpc",
            name="auto_shelf_bid_control_strategy",
        ),
        comment=NEW_COMMENT,
        existing_comment=OLD_COMMENT,
        existing_nullable=True,
        existing_server_default=sa.text("'plan_distance'::auto_shelf_bid_control_strategy"),
    )


def downgrade() -> None:
    op.execute(
        """
        UPDATE advsetting
        SET auto_shelf_bid_control_strategy = 'plan_distance'
        WHERE auto_shelf_bid_control_strategy IN ('ctr', 'cpc')
        """
    )

    op.alter_column(
        "advsetting",
        "auto_shelf_bid_control_strategy",
        existing_type=postgresql.ENUM(
            "cycle_metric",
            "plan_distance",
            "ctr",
            "cpc",
            name="auto_shelf_bid_control_strategy",
        ),
        comment=OLD_COMMENT,
        existing_comment=NEW_COMMENT,
        existing_nullable=True,
        existing_server_default=sa.text("'plan_distance'::auto_shelf_bid_control_strategy"),
    )
