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
    """Существующие строки остаются NULL до Job.

    Job с ``MIGRATION_BACKFILL_KIND=auto_update_minus_phrases_v1`` заполняет
    только NULL по ``bot_active``, затем DEFAULT false + NOT NULL. Без
    server_default на ADD: иначе PG зальёт legacy false и paid-active не
    получат true. Пока NULL возможны — Job можно повторять; после NOT NULL
    в проде backfill-path можно убрать.
    """
    op.add_column(
        "advsetting",
        sa.Column(
            "auto_update_minus_phrases",
            sa.Boolean(),
            nullable=True,
            comment=(
                "Включает фоновое обновление минус-фраз на WB. "
                "Отдельный флаг от auto_update_white_list."
            ),
        ),
    )


def downgrade() -> None:
    """Удаляет колонку для локального forward-recovery сценария."""
    op.drop_column("advsetting", "auto_update_minus_phrases")
