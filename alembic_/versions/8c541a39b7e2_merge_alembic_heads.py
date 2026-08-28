"""Merge the parallel Alembic heads without schema or data changes.

Revision ID: 8c541a39b7e2
Revises: d1e2f3a4b5c6, f2a3b4c5d6e7
Create Date: 2026-08-17 07:44:00.000000
"""

from typing import Sequence, Union


# revision identifiers, used by Alembic.
revision: str = "8c541a39b7e2"
down_revision: Union[str, Sequence[str], None] = (
    "d1e2f3a4b5c6",
    "f2a3b4c5d6e7",
)
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Объединяет ветви только на уровне топологии графа."""


def downgrade() -> None:
    """Не выполняет операций: merge-ревизия не меняет схему или данные."""
