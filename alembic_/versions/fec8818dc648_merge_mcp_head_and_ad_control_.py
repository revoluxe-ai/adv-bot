"""Merge MCP integration head with ad control settings persistence.

Revision ID: fec8818dc648
Revises: 8de1846cff85, b1c2d3e4f5a7
Create Date: 2026-10-10

No-op merge: 8de1846cff85 (MCP OAuth + apply authority) and b1c2d3e4f5a7
(ad control settings persistence) after stage integration.
"""

from collections.abc import Sequence

revision: str = "fec8818dc648"
down_revision: str | Sequence[str] | None = ("8de1846cff85", "b1c2d3e4f5a7")
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """No-op merge revision."""


def downgrade() -> None:
    """No-op merge revision."""
