"""Helpers for working with :class:`ParserProxy` records."""

from __future__ import annotations

import datetime as dt
from typing import Optional

from sqlalchemy import Select, and_, or_, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.wb_keywords_parser.models import ParserProxy
from app.utils.db.session_maker import get_async_session_maker


_UNSET = object()


class ParserProxyRepository:
    """Data-access helper for parser proxies."""

    def __init__(self, *, read_only: bool = False) -> None:
        self._read_only = read_only

    async def _execute(self, statement: Select[ParserProxy]) -> list[ParserProxy]:
        async with get_async_session_maker(read_only=self._read_only) as session:
            result = await session.execute(statement)
            return result.scalars().all()

    async def list_available(self) -> list[ParserProxy]:
        """Return proxies that are active and not on cooldown."""

        now = dt.datetime.utcnow()
        statement = (
            select(ParserProxy)
            .where(
                and_(
                    ParserProxy.is_active.is_(True),
                    or_(
                        ParserProxy.cooldown_until.is_(None),
                        ParserProxy.cooldown_until <= now,
                    ),
                )
            )
            .order_by(
                ParserProxy.last_used_at.is_(None).desc(),
                ParserProxy.last_used_at.asc(),
            )
        )
        return list(await self._execute(statement))

    async def mark_usage(
        self,
        proxy_id: int,
        *,
        last_used_at: Optional[dt.datetime] = None,
        fail_count: Optional[int] = None,
        cooldown_until: dt.datetime | None | object = _UNSET,
        is_active: Optional[bool] = None,
    ) -> None:
        """Persist rotation metadata for the given proxy."""

        values: dict[str, object] = {
            "last_used_at": last_used_at or dt.datetime.utcnow(),
        }
        if fail_count is not None:
            values["fail_count"] = fail_count
        if cooldown_until is not _UNSET:
            values["cooldown_until"] = cooldown_until
        if is_active is not None:
            values["is_active"] = is_active

        async with get_async_session_maker() as session:
            await self._update(session, proxy_id, values)

    async def reset_failures(self, proxy_id: int) -> None:
        """Reset failure count and cooldown for a proxy."""

        async with get_async_session_maker() as session:
            await self._update(
                session,
                proxy_id,
                {
                    "fail_count": 0,
                    "cooldown_until": None,
                },
            )

    async def _update(
        self, session: AsyncSession, proxy_id: int, values: dict[str, object]
    ) -> None:
        await session.execute(
            update(ParserProxy).where(ParserProxy.id == proxy_id).values(**values)
        )
        await session.commit()
