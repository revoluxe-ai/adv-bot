"""Global PG adv_id → (shop_id, adv_setting_id) overlap probe."""

from __future__ import annotations

from collections import defaultdict
from collections.abc import Callable
from typing import cast

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.modules.common_slaves.wildberries.models import AdvSetting, WBCabinet

_SEARCH_ADV_ID_COL = AdvSetting.__table__.c._search_adv_id


class PgAdvIdOverlapReader:
    """Read-only global ownership overlap for expanded adv_ids."""

    def __init__(
        self,
        session_maker: Callable[..., async_sessionmaker[AsyncSession]],
    ) -> None:
        self._session_maker = session_maker

    async def load_overlap(
        self,
        adv_ids: frozenset[int],
        session: AsyncSession | None = None,
    ) -> dict[int, list[tuple[str, int]]]:
        """Return adv_id → list of (shop_id, adv_setting_id) owners."""
        if not adv_ids:
            return {}
        if session is not None:
            return await self._load_with_session(session, adv_ids)
        session_factory = self._session_maker(read_only=True)
        async with session_factory() as owned_session:
            return await self._load_with_session(owned_session, adv_ids)

    async def _load_with_session(
        self,
        session: AsyncSession,
        adv_ids: frozenset[int],
    ) -> dict[int, list[tuple[str, int]]]:
        stmt = (
            select(
                WBCabinet.shop_id,
                AdvSetting.id,
                AdvSetting.adv_id,
                _SEARCH_ADV_ID_COL,
            )
            .join(AdvSetting.wb_cabinet)
            .where(
                AdvSetting.active_status != "done",
            )
        )
        result = await session.execute(stmt)
        overlap: dict[int, list[tuple[str, int]]] = defaultdict(list)
        for shop_id, adv_setting_id, adv_id, search_adv_id in result.all():
            shop = str(shop_id)
            setting_id = int(adv_setting_id)
            adv = int(adv_id)
            if adv in adv_ids:
                overlap[adv].append((shop, setting_id))
            if search_adv_id is not None:
                sid = int(cast(int, search_adv_id))
                if sid in adv_ids:
                    overlap[sid].append((shop, setting_id))
        deduped: dict[int, list[tuple[str, int]]] = {}
        for adv_id, owners in overlap.items():
            deduped[adv_id] = list(dict.fromkeys(owners))
        return deduped
