"""Долговечное подключение ChatGPT: хеш refresh и версия авторизации.

Список магазинов здесь не хранится. Сырой refresh token не сохраняется.
"""

from __future__ import annotations

import datetime
import hashlib
import secrets
import uuid
from dataclasses import dataclass

from app.modules.wb_sky_mcp.errors import McpError


def hash_refresh_token(token: str) -> str:
    """SHA-256 hex сырого refresh token."""
    return hashlib.sha256(token.encode("utf-8")).hexdigest()


def new_refresh_token() -> str:
    """Высокоэнтропийный refresh token. Хранится только его хеш."""
    return secrets.token_urlsafe(48)


@dataclass(slots=True)
class McpConnectionState:
    """Состояние подключения вне конкретного драйвера БД."""

    public_id: str
    user_id: int
    created_at: datetime.datetime
    updated_at: datetime.datetime
    revoked_at: datetime.datetime | None
    authorization_version: int
    refresh_token_hash: str | None
    refresh_token_expires_at: datetime.datetime | None
    refresh_rotated_at: datetime.datetime | None
    previous_refresh_token_hash: str | None

    @classmethod
    def create(
        cls,
        user_id: int,
        *,
        now: datetime.datetime,
    ) -> McpConnectionState:
        """Новое активное подключение без refresh."""
        return cls(
            public_id=str(uuid.uuid4()),
            user_id=user_id,
            created_at=now,
            updated_at=now,
            revoked_at=None,
            authorization_version=1,
            refresh_token_hash=None,
            refresh_token_expires_at=None,
            refresh_rotated_at=None,
            previous_refresh_token_hash=None,
        )


def store_refresh(
    state: McpConnectionState,
    token: str,
    *,
    now: datetime.datetime,
    ttl_seconds: int,
) -> str:
    """Записать хеш нового refresh. Возвращает сырой токен (его же)."""
    state.refresh_token_hash = hash_refresh_token(token)
    state.refresh_token_expires_at = now + datetime.timedelta(seconds=ttl_seconds)
    state.updated_at = now
    return token


def rotate_refresh(
    state: McpConnectionState,
    presented: str,
    *,
    now: datetime.datetime,
    ttl_seconds: int,
) -> str:
    """Обменять refresh. Повтор уже сменённого токена гасит подключение.

    Returns:
        Новый сырой refresh token.

    Raises:
        McpError: токен недействителен или это reuse.
    """
    presented_hash = hash_refresh_token(presented)
    if state.revoked_at is not None:
        raise McpError("UNAUTHENTICATED", "connection revoked")
    if (
        state.previous_refresh_token_hash is not None
        and presented_hash == state.previous_refresh_token_hash
    ):
        revoke_for_reuse(state, now=now)
        raise McpError("UNAUTHENTICATED", "refresh token reuse")
    if state.refresh_token_hash is None or presented_hash != state.refresh_token_hash:
        raise McpError("UNAUTHENTICATED", "refresh token rejected")
    expires = state.refresh_token_expires_at
    if expires is None or expires <= now:
        raise McpError("UNAUTHENTICATED", "refresh token expired")
    state.previous_refresh_token_hash = state.refresh_token_hash
    state.refresh_rotated_at = now
    fresh = new_refresh_token()
    state.refresh_token_hash = hash_refresh_token(fresh)
    state.refresh_token_expires_at = now + datetime.timedelta(seconds=ttl_seconds)
    state.updated_at = now
    return fresh


def revoke_for_reuse(state: McpConnectionState, *, now: datetime.datetime) -> None:
    """Погасить всё подключение после reuse refresh."""
    if state.revoked_at is None:
        state.revoked_at = now
        state.authorization_version += 1
    state.refresh_token_hash = None
    state.refresh_token_expires_at = None
    state.updated_at = now


def disconnect(state: McpConnectionState, *, now: datetime.datetime) -> None:
    """Отключение в боте: версия вверх, refresh погашен.

    Повторный вызов на уже отозванной строке не создаёт новое событие.
    """
    if state.revoked_at is not None:
        return
    state.revoked_at = now
    state.authorization_version += 1
    state.refresh_token_hash = None
    state.refresh_token_expires_at = None
    state.updated_at = now
