"""Delete raise CPO property from AdvSetting

Revision ID: 9acc1eb97755
Revises: 9b1a17cc1d6a
Create Date: 2026-06-14 03:08:58.399354

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '9acc1eb97755'
down_revision: Union[str, None] = '9b1a17cc1d6a'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


_RAISE_MAX_COLUMN_NAMES = (
    "v3_substitute_fact_cpo_for_max",
    "substitute_fact_cpo_for_max",
)
_RAISE_MAX_COMMENT = (
    "V3 Raise MAX: in-memory max=fact CPO when fact>db max (per tick, no persist)"
)


def _advsetting_column_names() -> set[str]:
    """Имена колонок advsetting в текущей БД (для idempotent drop/add)."""
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    return {column["name"] for column in inspector.get_columns("advsetting")}


def upgrade() -> None:
    # a3d86 мог добавить v3_* (старый текст ревизии) или substitute_* (новый).
    # Alembic не перезапускает уже применённые revision — дропаем оба имени, если есть.
    columns = _advsetting_column_names()
    for name in _RAISE_MAX_COLUMN_NAMES:
        if name in columns:
            op.drop_column("advsetting", name)


def downgrade() -> None:
    columns = _advsetting_column_names()
    if not columns.intersection(_RAISE_MAX_COLUMN_NAMES):
        op.add_column(
            "advsetting",
            sa.Column(
                "substitute_fact_cpo_for_max",
                sa.BOOLEAN(),
                server_default=sa.text("false"),
                autoincrement=False,
                nullable=False,
                comment=_RAISE_MAX_COMMENT,
            ),
        )
