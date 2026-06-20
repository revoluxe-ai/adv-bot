"""Add substitute_fact_cpo_for_max to AdvSetting

Revision ID: 250ee8ae5c45
Revises: 62f0582c7641
Create Date: 2026-06-20 18:12:42.933842

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '250ee8ae5c45'
down_revision: Union[str, None] = '62f0582c7641'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


_NEW_COLUMN = "substitute_fact_cpo_for_max"
_LEGACY_COLUMN = "v3_substitute_fact_cpo_for_max"
_RAISE_MAX_COMMENT = (
    "V3 Raise MAX: in-memory max=fact CPO when fact>db max (per tick, no persist)"
)


def _advsetting_column_names() -> set[str]:
    """Имена колонок advsetting в текущей БД (для idempotent add/rename)."""
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    return {column["name"] for column in inspector.get_columns("advsetting")}


def upgrade() -> None:
    columns = _advsetting_column_names()
    if _NEW_COLUMN in columns:
        return
    if _LEGACY_COLUMN in columns:
        op.alter_column(
            "advsetting",
            _LEGACY_COLUMN,
            new_column_name=_NEW_COLUMN,
        )
        return
    op.add_column(
        "advsetting",
        sa.Column(
            _NEW_COLUMN,
            sa.Boolean(),
            server_default="false",
            nullable=False,
            comment=_RAISE_MAX_COMMENT,
        ),
    )


def downgrade() -> None:
    columns = _advsetting_column_names()
    if _NEW_COLUMN in columns:
        op.drop_column("advsetting", _NEW_COLUMN)
