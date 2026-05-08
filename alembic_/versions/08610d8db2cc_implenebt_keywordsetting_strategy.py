"""Implement KeywordSetting.strategy_mode (PostgreSQL enum keywordstrategymode, default MIN_CPA).

Revision ID: 08610d8db2cc
Revises: 80d14604e6d0
Create Date: 2026-05-08 20:52:42.065606

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = "08610d8db2cc"
down_revision: Union[str, None] = "80d14604e6d0"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

# Matches SQLAlchemy SAEnum(KeywordStrategyMode) → Postgres type name keywordstrategymode
keyword_strategy_mode_enum = postgresql.ENUM(
    "OFF",
    "MIN_CPA",
    "OPTIMUM",
    "MAX_CONVERSION",
    name="keywordstrategymode",
    create_type=False,
)


def upgrade() -> None:
    keyword_strategy_mode_enum.create(op.get_bind(), checkfirst=True)
    op.add_column(
        "keywordsetting",
        sa.Column(
            "strategy_mode",
            keyword_strategy_mode_enum,
            nullable=False,
            # Match KeywordSetting.strategy_mode (SQLAlchemy server_default)
            server_default="MIN_CPA",
        ),
    )


def downgrade() -> None:
    op.drop_column("keywordsetting", "strategy_mode")
    keyword_strategy_mode_enum.drop(op.get_bind(), checkfirst=True)
