"""Add strategy to AdvSetting

Revision ID: e6bf474460a8
Revises: e1ca6f2354d3
Create Date: 2026-02-28 23:37:06.746768
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


# revision identifiers, used by Alembic.
revision: str = 'e6bf474460a8'
down_revision: Union[str, None] = 'e1ca6f2354d3'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


# Создаём объект ENUM
strategy_enum = postgresql.ENUM(
    'MIN_CPO',
    'MAX_CONV',
    name='strategy',
    create_type=False,  # будем создавать вручную
)


def upgrade() -> None:
    # 1️⃣ Создать тип ENUM в Postgres
    strategy_enum.create(op.get_bind(), checkfirst=True)

    # 2️⃣ Добавить колонку
    op.add_column(
        'advsetting',
        sa.Column(
            'strategy',
            strategy_enum,
            nullable=False,
            server_default='MIN_CPO',
        )
    )

    # 3️⃣ (опционально) убрать server_default если не нужен навсегда
    op.alter_column('advsetting', 'strategy', server_default=None)


def downgrade() -> None:
    # 1️⃣ Удалить колонку
    op.drop_column('advsetting', 'strategy')

    # 2️⃣ Удалить тип ENUM
    strategy_enum.drop(op.get_bind(), checkfirst=True)
