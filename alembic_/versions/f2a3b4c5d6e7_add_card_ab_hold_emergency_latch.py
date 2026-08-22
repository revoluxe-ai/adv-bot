"""Add card_ab_hold_emergency_latch (+ educated) to AdvSetting

Revision ID: f2a3b4c5d6e7
Revises: d0e1f2a3b4c5
Create Date: 2026-07-30

Change ab-hold-emergency-kill-switch / decision write-path: durable Emergency
latch (suppress top-up/restart) and launch-education ACK flag.
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "f2a3b4c5d6e7"
down_revision: Union[str, None] = "d0e1f2a3b4c5"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "advsetting",
        sa.Column(
            "card_ab_hold_emergency_latch",
            sa.Boolean(),
            server_default=sa.text("false"),
            nullable=False,
            comment=(
                "A/B Hold Emergency kill-switch latch: True → no budget top-up / "
                "no activity restart (ab-hold-emergency-kill-switch)"
            ),
        ),
    )
    op.add_column(
        "advsetting",
        sa.Column(
            "card_ab_hold_emergency_educated",
            sa.Boolean(),
            server_default=sa.text("false"),
            nullable=False,
            comment=(
                "A/B Hold Emergency launch education ACK "
                "(ab-hold-emergency-kill-switch)"
            ),
        ),
    )


def downgrade() -> None:
    op.drop_column("advsetting", "card_ab_hold_emergency_educated")
    op.drop_column("advsetting", "card_ab_hold_emergency_latch")
