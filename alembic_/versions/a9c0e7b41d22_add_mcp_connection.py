"""Add durable MCP ChatGPT connection state.

Revision ID: a9c0e7b41d22
Revises: d7e3c9f1a204
Create Date: 2026-10-06

Хранит подключение и хеш refresh. Список магазинов не копируется.
Миграция вперёд-только. На production в этом change не применяется.
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op


revision: str = "a9c0e7b41d22"
down_revision: str | None = "d7e3c9f1a204"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Создать mcp_connection."""
    op.create_table(
        "mcp_connection",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("public_id", sa.String(length=36), nullable=False),
        sa.Column("user_id", sa.Integer(), sa.ForeignKey("user.id"), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("revoked_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("authorization_version", sa.Integer(), nullable=False),
        sa.Column("refresh_token_hash", sa.String(length=64), nullable=True),
        sa.Column("refresh_token_expires_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("refresh_rotated_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("previous_refresh_token_hash", sa.String(length=64), nullable=True),
        sa.UniqueConstraint("public_id", name="uq_mcp_connection_public_id"),
    )
    op.create_index(
        "idx_mcp_connection_user_id", "mcp_connection", ["user_id"]
    )
    op.create_index(
        "idx_mcp_connection_refresh_hash",
        "mcp_connection",
        ["refresh_token_hash"],
    )


def downgrade() -> None:
    """Удалить mcp_connection. На production этот change downgrade не вызывает."""
    op.drop_index("idx_mcp_connection_refresh_hash", table_name="mcp_connection")
    op.drop_index("idx_mcp_connection_user_id", table_name="mcp_connection")
    op.drop_table("mcp_connection")
