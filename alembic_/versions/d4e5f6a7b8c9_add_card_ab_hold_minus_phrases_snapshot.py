"""Add card_ab_hold_minus_phrases_snapshot to AdvSetting

Revision ID: d4e5f6a7b8c9
Revises: b8c4ac80176c
Create Date: 2026-07-14

Spec card-ab-hold-mode §8 / decision write-path §8: durable PG snapshot
минус-фраз на время A/B Hold (не переиспользовать migration режима).
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision: str = "d4e5f6a7b8c9"
down_revision: Union[str, None] = "b8c4ac80176c"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "advsetting",
        sa.Column(
            "card_ab_hold_minus_phrases_snapshot",
            postgresql.JSONB(astext_type=sa.Text()),
            server_default=sa.text("'[]'"),
            nullable=False,
            comment=(
                "A/B Hold: snapshot минус-фраз "
                "[{adv_id, nmid, phrases[]}] (spec card-ab-hold-mode §8)"
            ),
        ),
    )


def downgrade() -> None:
    op.drop_column("advsetting", "card_ab_hold_minus_phrases_snapshot")
