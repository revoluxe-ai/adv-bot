"""Репозиторий подключения MCP: память для тестов и PostgreSQL для процесса.

Ротация refresh выполняется в одной критической секции: в PostgreSQL это
``SELECT … FOR UPDATE`` и запись в той же транзакции, в памяти — общий lock.
Сырой refresh token сюда не передаётся, только хеш и уже посчитанное состояние.
"""

from __future__ import annotations

import asyncio
import datetime
from collections.abc import Callable
from typing import Protocol

from sqlalchemy import or_, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.sql import Select

from app.modules.wb_sky_mcp.connection_logic import McpConnectionState
from app.modules.wb_sky_mcp.errors import McpError, McpStorageError
from app.modules.wb_sky_mcp.models import McpConnection

RefreshRotation = Callable[[McpConnectionState], str]


class ConnectionRepository(Protocol):
    """Чтение и запись подключения. Ошибка драйвера — fail-closed."""

    async def add(self, state: McpConnectionState) -> None: ...

    async def get(self, public_id: str) -> McpConnectionState | None: ...

    async def save(self, state: McpConnectionState) -> None: ...

    async def list_for_user(self, user_id: int) -> list[McpConnectionState]: ...

    async def find_by_refresh_hash(self, token_hash: str) -> McpConnectionState | None: ...

    async def apply_refresh_rotation(
        self,
        token_hash: str,
        apply: RefreshRotation,
    ) -> tuple[McpConnectionState, str] | None:
        """Под блокировкой строки применить ротацию и зафиксировать её.

        ``apply`` видит строку уже после захвата блокировки. Если ротация
        отказывает после изменения состояния (повтор refresh), это изменение
        тоже фиксируется. ``None`` — строки с таким хешем нет.
        """
        ...


class MemoryConnectionRepository:
    """In-memory репозиторий с той же семантикой, что и PostgreSQL-адаптер.

    Ротация сериализуется одним lock, чтобы два одновременных обмена одного
    refresh не прошли оба.
    """

    def __init__(self) -> None:
        self.rows: dict[str, McpConnectionState] = {}
        self._rotation_lock = asyncio.Lock()

    async def add(self, state: McpConnectionState) -> None:
        self.rows[state.public_id] = state

    async def get(self, public_id: str) -> McpConnectionState | None:
        return self.rows.get(public_id)

    async def save(self, state: McpConnectionState) -> None:
        if state.public_id not in self.rows:
            raise McpStorageError("connection missing")
        self.rows[state.public_id] = state

    async def list_for_user(self, user_id: int) -> list[McpConnectionState]:
        return [row for row in self.rows.values() if row.user_id == user_id]

    async def find_by_refresh_hash(self, token_hash: str) -> McpConnectionState | None:
        for row in self.rows.values():
            if token_hash in (
                row.refresh_token_hash,
                row.previous_refresh_token_hash,
            ):
                return row
        return None

    async def apply_refresh_rotation(
        self,
        token_hash: str,
        apply: RefreshRotation,
    ) -> tuple[McpConnectionState, str] | None:
        """Сериализовать ротацию и сохранить её результат, включая отзыв."""
        async with self._rotation_lock:
            state = await self.find_by_refresh_hash(token_hash)
            if state is None:
                return None
            try:
                fresh = apply(state)
            except McpError:
                await self.save(state)
                raise
            await self.save(state)
            return state, fresh


def _as_utc(value: datetime.datetime | None) -> datetime.datetime | None:
    if value is None:
        return None
    if value.tzinfo is None:
        return value.replace(tzinfo=datetime.timezone.utc)
    return value


def _row_to_state(row: McpConnection) -> McpConnectionState:
    return McpConnectionState(
        public_id=row.public_id,
        user_id=row.user_id,
        created_at=_as_utc(row.created_at) or datetime.datetime.now(datetime.timezone.utc),
        updated_at=_as_utc(row.updated_at) or datetime.datetime.now(datetime.timezone.utc),
        revoked_at=_as_utc(row.revoked_at),
        authorization_version=row.authorization_version,
        refresh_token_hash=row.refresh_token_hash,
        refresh_token_expires_at=_as_utc(row.refresh_token_expires_at),
        refresh_rotated_at=_as_utc(row.refresh_rotated_at),
        previous_refresh_token_hash=row.previous_refresh_token_hash,
    )


class SqlConnectionRepository:
    """PostgreSQL-адаптер. Исключение драйвера становится ``McpStorageError``.

    Не пишет кабинеты и не читает список магазинов.
    """

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def add(self, state: McpConnectionState) -> None:
        row = McpConnection(
            public_id=state.public_id,
            user_id=state.user_id,
            created_at=state.created_at,
            updated_at=state.updated_at,
            revoked_at=state.revoked_at,
            authorization_version=state.authorization_version,
            refresh_token_hash=state.refresh_token_hash,
            refresh_token_expires_at=state.refresh_token_expires_at,
            refresh_rotated_at=state.refresh_rotated_at,
            previous_refresh_token_hash=state.previous_refresh_token_hash,
        )
        try:
            self._session.add(row)
            await self._session.commit()
        except Exception as exc:
            raise McpStorageError("postgresql unavailable") from exc

    async def get(self, public_id: str) -> McpConnectionState | None:
        try:
            stmt = select(McpConnection).where(McpConnection.public_id == public_id)
            result = await self._session.execute(stmt)
            row = result.scalar_one_or_none()
        except Exception as exc:
            raise McpStorageError("postgresql unavailable") from exc
        if row is None:
            return None
        return _row_to_state(row)

    async def save(self, state: McpConnectionState) -> None:
        try:
            stmt = select(McpConnection).where(McpConnection.public_id == state.public_id)
            result = await self._session.execute(stmt)
            row = result.scalar_one_or_none()
            if row is None:
                raise McpStorageError("connection missing")
            _assign_row(row, state)
            await self._session.commit()
        except McpStorageError:
            raise
        except Exception as exc:
            raise McpStorageError("postgresql unavailable") from exc

    async def list_for_user(self, user_id: int) -> list[McpConnectionState]:
        try:
            stmt = select(McpConnection).where(McpConnection.user_id == user_id)
            result = await self._session.execute(stmt)
            rows = result.scalars().all()
        except Exception as exc:
            raise McpStorageError("postgresql unavailable") from exc
        return [_row_to_state(row) for row in rows]

    async def find_by_refresh_hash(self, token_hash: str) -> McpConnectionState | None:
        """Найти подключение по текущему или предыдущему хешу refresh."""
        try:
            stmt = _refresh_hash_select(token_hash)
            result = await self._session.execute(stmt)
            row = result.scalar_one_or_none()
        except Exception as exc:
            raise McpStorageError("postgresql unavailable") from exc
        if row is None:
            return None
        return _row_to_state(row)

    async def apply_refresh_rotation(
        self,
        token_hash: str,
        apply: RefreshRotation,
    ) -> tuple[McpConnectionState, str] | None:
        """Заблокировать строку, ротировать refresh и зафиксировать транзакцию.

        Второй одновременный обмен ждёт ``FOR UPDATE``, затем видит уже
        сменённый хеш и не получает второй успешный токен.
        """
        try:
            stmt = _refresh_hash_select(token_hash).with_for_update()
            result = await self._session.execute(stmt)
            row = result.scalar_one_or_none()
            if row is None:
                return None
            state = _row_to_state(row)
            try:
                fresh = apply(state)
            except McpError:
                _assign_row(row, state)
                await self._session.commit()
                raise
            _assign_row(row, state)
            await self._session.commit()
            return state, fresh
        except McpError:
            raise
        except Exception as exc:
            raise McpStorageError("postgresql unavailable") from exc


def _refresh_hash_select(token_hash: str) -> Select[tuple[McpConnection]]:
    """Выборка подключения по текущему или предыдущему хешу refresh."""
    return select(McpConnection).where(
        or_(
            McpConnection.refresh_token_hash == token_hash,
            McpConnection.previous_refresh_token_hash == token_hash,
        )
    )


def _assign_row(row: McpConnection, state: McpConnectionState) -> None:
    """Перенести изменяемые поля подключения в загруженную строку."""
    row.updated_at = state.updated_at
    row.revoked_at = state.revoked_at
    row.authorization_version = state.authorization_version
    row.refresh_token_hash = state.refresh_token_hash
    row.refresh_token_expires_at = state.refresh_token_expires_at
    row.refresh_rotated_at = state.refresh_rotated_at
    row.previous_refresh_token_hash = state.previous_refresh_token_hash
