"""PgBouncer-safe PostgreSQL transaction coordinator.

Spec: campaign-settings-history.
Uses transaction-scoped advisory locks because repository PG connectivity is
configured for PgBouncer transaction pooling.
"""

from __future__ import annotations

from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager
from dataclasses import dataclass

from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.ext.asyncio import AsyncSession

from app.utils.db.session_maker import get_async_session_maker

_HISTORY_LOCK_NAMESPACE = 1129531441
_INT32_MIN = -(2**31)
_INT32_MAX = 2**31 - 1


@dataclass(frozen=True, slots=True)
class LockedCabinetTransaction:
    """One PG transaction that owns history collection lock for a cabinet."""

    session: AsyncSession
    acquired: bool


class PostgresTransactionCoordinator:
    """Liveness proof for the same transaction that acquired xact advisory lock."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def transaction_alive(self) -> bool:
        if not self._session.is_active or not self._session.in_transaction():
            return False
        try:
            await self._session.execute(text("SELECT 1"))
        except SQLAlchemyError:
            return False
        return self._session.is_active and bool(self._session.in_transaction())


def validate_cabinet_lock_key(wb_cabinet_id: int) -> None:
    """Fail closed rather than silently hashing an unsupported advisory key."""
    if type(wb_cabinet_id) is not int:
        raise ValueError("wb_cabinet_id must be int")
    if not (_INT32_MIN <= wb_cabinet_id <= _INT32_MAX):
        raise ValueError("wb_cabinet_id must fit PostgreSQL advisory int32 key")


@asynccontextmanager
async def locked_cabinet_transaction(
    wb_cabinet_id: int,
) -> AsyncGenerator[LockedCabinetTransaction, None]:
    """Open one RW PG transaction and try to own this cabinet non-blockingly."""
    validate_cabinet_lock_key(wb_cabinet_id)
    async with get_async_session_maker(read_only=False) as session:
        # Explicit begin is required by contract: the xact lock must cover PG reads
        # and the external ClickHouse compare/insert interval.
        async with session.begin():
            result = await session.execute(
                text(
                    "SELECT pg_try_advisory_xact_lock("
                    ":namespace_key, :object_key)"
                ),
                {
                    "namespace_key": _HISTORY_LOCK_NAMESPACE,
                    "object_key": wb_cabinet_id,
                },
            )
            acquired = bool(result.scalar_one())
            yield LockedCabinetTransaction(
                session=session,
                acquired=acquired,
            )
