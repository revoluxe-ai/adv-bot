"""PG AdvSetting.id inventory + Redis rebound read for keyword export scope."""

from __future__ import annotations

from collections.abc import Callable
from typing import Protocol, cast

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.modules.ai_package_v1.scope.pg_adv_setting_inventory_reader import (
    PgAdvSettingInventoryReader,
    SessionMakerProtocol,
)
from app.modules.ai_package_v1.keyword_performance.readers.pg_adv_id_overlap_reader import (
    PgAdvIdOverlapReader,
)
from app.modules.ai_package_v1.keyword_performance.readers.pg_session_adapter import (
    default_pg_session_factory,
)
from app.modules.ai_package_v1.keyword_performance.scope.dto import KeywordScopeRow
from app.modules.common_slaves.wildberries.models import AdvSetting
from app.modules.common_slaves.wildberries.rebind_wb_adv_ids_history import (
    get_rebound_wb_adv_ids,
)


class ReboundReaderProtocol(Protocol):
    """Seam for Redis rebound membership."""

    async def get_rebound_wb_adv_ids(
        self, adv_setting_id: int
    ) -> tuple[set[int], set[int]]:
        ...


class _DefaultReboundReader:
    async def get_rebound_wb_adv_ids(
        self, adv_setting_id: int
    ) -> tuple[set[int], set[int]]:
        return await get_rebound_wb_adv_ids(adv_setting_id)


def _resolve_main_nmid(nmids: list[int]) -> int | None:
    if not nmids:
        return None
    return sorted(nmids)[0]


def _row_from_adv_setting(
    row: AdvSetting,
    shop_id: str,
    rebound_auto: set[int],
    rebound_search: set[int],
) -> KeywordScopeRow | None:
    adv_id_value = cast(object, row.adv_id)
    if not isinstance(adv_id_value, int):
        return None
    return KeywordScopeRow(
        shop_id=shop_id,
        adv_setting_id=row.id,
        auto_adv_id=adv_id_value,
        search_adv_id=row.search_adv_id,
        main_nmid=_resolve_main_nmid(list(row.nmids or [])),
        rebound_auto_adv_ids=frozenset(rebound_auto),
        rebound_search_adv_ids=frozenset(rebound_search),
    )


class KeywordExportScopeReader:
    """Load keyword scope: PG inventory PK + rebound Redis membership."""

    def __init__(
        self,
        inventory_reader: PgAdvSettingInventoryReader | None = None,
        rebound_reader: ReboundReaderProtocol | None = None,
        overlap_reader: PgAdvIdOverlapReader | None = None,
        *,
        session_maker: SessionMakerProtocol
        | Callable[..., async_sessionmaker[AsyncSession]]
        | None = None,
    ) -> None:
        if inventory_reader is not None:
            self._inventory = inventory_reader
            maker = session_maker or getattr(inventory_reader, "_session_maker", None)
        elif session_maker is not None:
            self._inventory = PgAdvSettingInventoryReader(session_maker)
            maker = session_maker
        else:
            maker = default_pg_session_factory
            self._inventory = PgAdvSettingInventoryReader(maker)
        self._rebound = rebound_reader or _DefaultReboundReader()
        self._overlap = overlap_reader or PgAdvIdOverlapReader(
            maker or default_pg_session_factory
        )

    async def load_keyword_scope(
        self, shop_id: str
    ) -> tuple[list[KeywordScopeRow], bool]:
        """Load scope rows; returns (rows, rebound_unavailable flag)."""
        inventory = await self._inventory.load_inventory(shop_id)
        rebound_unavailable = False
        rows: list[KeywordScopeRow] = []
        for adv in inventory:
            cabinet = cast(object | None, adv.wb_cabinet)
            cabinet_shop_id = getattr(cabinet, "shop_id", None)
            if cabinet_shop_id != shop_id:
                continue
            rebound_auto: set[int] = set()
            rebound_search: set[int] = set()
            try:
                rebound_auto, rebound_search = await self._rebound.get_rebound_wb_adv_ids(
                    adv.id
                )
            except Exception:
                rebound_unavailable = True
            built = _row_from_adv_setting(
                adv, shop_id, rebound_auto, rebound_search
            )
            if built is not None:
                rows.append(built)
        return rows, rebound_unavailable

    async def load_global_adv_id_overlap(
        self,
        adv_ids: frozenset[int],
        session: AsyncSession | None = None,
    ) -> dict[int, list[tuple[str, int]]]:
        """Global PG probe: adv_id → [(shop_id, adv_setting_id), ...]."""
        return await self._overlap.load_overlap(adv_ids, session=session)
