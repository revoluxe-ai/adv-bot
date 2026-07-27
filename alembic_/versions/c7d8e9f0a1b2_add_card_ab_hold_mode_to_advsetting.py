"""Add card_ab_hold_mode to advsetting

Revision ID: c7d8e9f0a1b2
Revises: fe84033472cf
Create Date: 2026-07-13 21:30:00.000000

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "c7d8e9f0a1b2"
down_revision: Union[str, None] = "fe84033472cf"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "advsetting",
        sa.Column(
            "card_ab_hold_mode",
            sa.String(length=32),
            server_default=sa.text("'off'"),
            nullable=False,
            comment="A/B Hold mode: off | pending_setup | active (spec card-ab-hold-mode)",
        ),
    )


def downgrade() -> None:
    op.drop_column("advsetting", "card_ab_hold_mode")
