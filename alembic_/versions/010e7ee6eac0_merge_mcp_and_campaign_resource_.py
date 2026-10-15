"""Merge parallel Alembic heads after stage integration.

Revision ID: 010e7ee6eac0
Revises: a9c0e7b41d22, e8a1b2c3d4e5
Create Date: 2026-10-09

Объединяет MCP connection (a9c0e7b41d22) и campaign resource registry
(e8a1b2c3d4e5) без изменения схемы. Вызывается тестами heads и provider cert.
"""

from collections.abc import Sequence

revision: str = "010e7ee6eac0"
down_revision: str | Sequence[str] | None = ("a9c0e7b41d22", "e8a1b2c3d4e5")
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """No-op merge revision."""


def downgrade() -> None:
    """No-op merge revision."""
