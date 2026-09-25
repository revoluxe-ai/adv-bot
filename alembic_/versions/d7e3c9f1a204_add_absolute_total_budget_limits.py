"""Add absolute (lifetime) total budget limits to AdvSetting

Абсолютный лимит суммарного расхода на РК: зеркало суточных лимитов,
переключается тем же флагом ``use_common_budget``. Новые записи получают
500 руб (``server_default``), существующие строки выставляются в 0
(= отключено), чтобы уже работающие РК не встали на паузу сразу после
деплоя.

Revision ID: d7e3c9f1a204
Revises: c4f8a1b2d3e4
Create Date: 2026-09-22 18:25:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "d7e3c9f1a204"
down_revision: Union[str, None] = "c4f8a1b2d3e4"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "advsetting",
        sa.Column(
            "auto_budget_total_limit",
            sa.Integer(),
            nullable=False,
            server_default=sa.text("500"),
            comment=(
                "Абсолютный лимит суммарного РАСХОДА (руб, за всё время) "
                "для автоматической кампании, 0 = отключено"
            ),
        ),
    )
    op.add_column(
        "advsetting",
        sa.Column(
            "search_auto_budget_total_limit",
            sa.Integer(),
            nullable=False,
            server_default=sa.text("500"),
            comment=(
                "Абсолютный лимит суммарного РАСХОДА (руб, за всё время) "
                "для аукционной кампании, 0 = отключено"
            ),
        ),
    )
    op.add_column(
        "advsetting",
        sa.Column(
            "common_budget_total_limit",
            sa.Integer(),
            nullable=False,
            server_default=sa.text("500"),
            comment=(
                "Общий абсолютный лимит расхода (руб, за всё время) на обе РК; "
                "действует при use_common_budget, 0 = отключено"
            ),
        ),
    )
    # Существующие РК: лимит выключен, иначе кампании с историческим расходом
    # выше 500 руб будут приостановлены на первом же тике watchdog.
    op.execute(
        "UPDATE advsetting SET "
        "auto_budget_total_limit = 0, "
        "search_auto_budget_total_limit = 0, "
        "common_budget_total_limit = 0"
    )


def downgrade() -> None:
    op.drop_column("advsetting", "common_budget_total_limit")
    op.drop_column("advsetting", "search_auto_budget_total_limit")
    op.drop_column("advsetting", "auto_budget_total_limit")
