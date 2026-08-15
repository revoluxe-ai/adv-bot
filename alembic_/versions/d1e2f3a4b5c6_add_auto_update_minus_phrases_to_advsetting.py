"""Add auto_update_minus_phrases to AdvSetting with safe rollout defaults.

Revision ID: d1e2f3a4b5c6
Revises: 92bdd3917621
Create Date: 2026-06-26 13:00:00.000000
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "d1e2f3a4b5c6"
down_revision: Union[str, None] = "92bdd3917621"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "advsetting",
        sa.Column(
            "auto_update_minus_phrases",
            sa.Boolean(),
            nullable=True,
            server_default=sa.text("false"),
            comment=(
                "Включает фоновое обновление минус-фраз на WB. "
                "Отдельный флаг от auto_update_white_list."
            ),
        ),
    )
    op.execute(
        sa.text(
            "UPDATE advsetting "
            "SET auto_update_minus_phrases = true "
            "WHERE auto_update_minus_phrases IS NULL"
        )
    )
    op.alter_column(
        "advsetting",
        "auto_update_minus_phrases",
        existing_type=sa.Boolean(),
        nullable=False,
        server_default=sa.text("false"),
        existing_comment=(
            "Включает фоновое обновление минус-фраз на WB. "
            "Отдельный флаг от auto_update_white_list."
        ),
    )


def downgrade() -> None:
    op.drop_column("advsetting", "auto_update_minus_phrases")
