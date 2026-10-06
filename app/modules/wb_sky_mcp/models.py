"""Таблица долговечного подключения ChatGPT.

Права магазинов остаются в ``WBUserCabinet``. Здесь только личность
подключения, версия отзыва и хеш refresh.
"""

from __future__ import annotations

import datetime

from sqlalchemy import DateTime, ForeignKey, Index, Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from app.utils.db.base import BaseTable


class McpConnection(BaseTable):
    """Строка подключения MCP к пользователю WB Sky.

    ``public_id`` попадает в access token как ``connection_id``.
    ``user_id`` — ``User.id``, не Telegram id.
    """

    __tablename__ = "mcp_connection"  # pyright: ignore[reportAssignmentType]

    public_id: Mapped[str] = mapped_column(String(36), nullable=False, unique=True)
    user_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("user.id"), nullable=False
    )
    created_at: Mapped[datetime.datetime] = mapped_column(
        DateTime(timezone=True), nullable=False
    )
    updated_at: Mapped[datetime.datetime] = mapped_column(
        DateTime(timezone=True), nullable=False
    )
    revoked_at: Mapped[datetime.datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    authorization_version: Mapped[int] = mapped_column(Integer, nullable=False)
    refresh_token_hash: Mapped[str | None] = mapped_column(String(64), nullable=True)
    refresh_token_expires_at: Mapped[datetime.datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    refresh_rotated_at: Mapped[datetime.datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    previous_refresh_token_hash: Mapped[str | None] = mapped_column(
        String(64), nullable=True
    )
    __table_args__ = (
        Index("idx_mcp_connection_user_id", "user_id"),
        Index("idx_mcp_connection_refresh_hash", "refresh_token_hash"),
    )
