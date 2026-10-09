"""Merge MCP OAuth head with Apply Authority Slice B head.

Revision ID: 8de1846cff85
Revises: 010e7ee6eac0, f9c0a1b2d3e4
Create Date: 2026-10-09

No-op merge: 010e7ee6eac0 (MCP + campaign registry) and f9c0a1b2d3e4
(Apply Authority PG ledger) after stage integration.
"""

from collections.abc import Sequence

revision: str = "8de1846cff85"
down_revision: str | Sequence[str] | None = ("010e7ee6eac0", "f9c0a1b2d3e4")
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """No-op merge revision."""


def downgrade() -> None:
    """No-op merge revision."""
