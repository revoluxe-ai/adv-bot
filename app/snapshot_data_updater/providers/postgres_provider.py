"""Postgres snapshot provider: Stub (без БД) и Live (read-only active adv).

Live повторяет фильтр ``WBShopDataManager._get_active_advs``:
``bot_active``, ``active_status != done``, join по ``shop_id`` кабинета.
Дополнительно строит ``ComplexAdv`` для keyword warmup (ORM только in-process).
"""

from __future__ import annotations

import logging
from collections.abc import Sequence

from sqlalchemy import select
from sqlalchemy.orm import selectinload

from app.modules.common_slaves.wildberries.models import AdvSetting, WBCabinet
from app.modules.shop_runner.service_manager.wb_shop_data_manager.dto.complex_adv import (
    ComplexAdv,
)
from app.shared.domains.wb.utils.cost_resolver import resolve_target_cost
from app.snapshot_data_updater.dto import AdvSettingsSnapshotDTO
from app.snapshot_data_updater.providers.postgres_shop_load import (
    PostgresShopSnapshotLoad,
)
from app.utils.db.session_maker import get_async_session_maker as sm

logger = logging.getLogger(__name__)


class StubPostgresSnapshotProvider:
    """Фикстуры настроек adv для unit/smoke (``use_live_updater=False``)."""

    def __init__(
        self,
        *,
        adv_settings_by_shop: dict[str, list[AdvSettingsSnapshotDTO]] | None = None,
        shop_load_by_shop: dict[str, PostgresShopSnapshotLoad] | None = None,
    ) -> None:
        self._by_shop = adv_settings_by_shop or {}
        self._shop_load = shop_load_by_shop or {}

    async def fetch_active_adv_settings(
        self, shop_id: str
    ) -> list[AdvSettingsSnapshotDTO]:
        load = await self.fetch_shop_collect_load(shop_id)
        return load.settings

    async def fetch_shop_collect_load(self, shop_id: str) -> PostgresShopSnapshotLoad:
        """Один shop load для collector (без ComplexAdv в stub)."""
        if shop_id in self._shop_load:
            return self._shop_load[shop_id]
        if shop_id in self._by_shop:
            return PostgresShopSnapshotLoad(
                shop_id=shop_id,
                settings=list(self._by_shop[shop_id]),
            )
        return PostgresShopSnapshotLoad(
            shop_id=shop_id,
            settings=[
                AdvSettingsSnapshotDTO(
                    adv_id=1001,
                    shop_id=shop_id,
                    nm_id=12345,
                    nmids=[12345],
                    bot_active=True,
                    active_status="active",
                )
            ],
        )


class PostgresSnapshotProviderLive:
    """Read-only Postgres: active adv + ``ComplexAdv`` для warmup (live only)."""

    async def fetch_active_adv_settings(
        self, shop_id: str
    ) -> list[AdvSettingsSnapshotDTO]:
        load = await self.fetch_shop_collect_load(shop_id)
        return load.settings

    async def fetch_shop_collect_load(self, shop_id: str) -> PostgresShopSnapshotLoad:
        """Один round-trip PG на shop: settings DTO + map adv_id → ComplexAdv."""
        stmt = (
            select(AdvSetting)
            .join(AdvSetting.wb_cabinet)
            .options(selectinload(AdvSetting.wb_cabinet))
            .where(
                WBCabinet.shop_id == shop_id,
                AdvSetting.active_status != "done",
                AdvSetting.bot_active.is_(True),
            )
        )
        async with sm() as session:
            result = await session.execute(stmt)
            adv_settings: Sequence[AdvSetting] = result.scalars().all()

        search_ids = {
            adv.search_adv_id for adv in adv_settings if adv.search_adv_id is not None
        }
        search_map: dict[int, AdvSetting] = {}
        if search_ids:
            stmt_search = select(AdvSetting).where(AdvSetting.adv_id.in_(search_ids))
            async with sm() as session:
                search_result = await session.execute(stmt_search)
                search_rows = search_result.scalars().all()
            search_map = {int(a.adv_id): a for a in search_rows if a.adv_id is not None}

        settings_dtos: list[AdvSettingsSnapshotDTO] = []
        complex_by_id: dict[int, ComplexAdv] = {}
        for adv in adv_settings:
            if adv.adv_id is None:
                continue
            adv_id = int(adv.adv_id)
            nmids = list(adv.nmids or [])
            nm_id = nmids[0] if nmids else None
            search_adv = (
                search_map.get(adv.search_adv_id) if adv.search_adv_id else None
            )
            settings_dtos.append(
                AdvSettingsSnapshotDTO(
                    adv_id=adv_id,
                    shop_id=shop_id,
                    nm_id=nm_id,
                    nmids=nmids,
                    search_adv_id=adv.search_adv_id,
                    bot_active=bool(adv.bot_active),
                    active_status=str(adv.active_status),
                    bidder_active=adv.bidder_active,
                )
            )
            target_pay = resolve_target_cost(
                adv.plan_for_sales_for_day,
                adv.target_price_for_order,
                adv.max_price_for_order,
                None,
            )
            complex_by_id[adv_id] = ComplexAdv(
                adv_setting=adv,
                search_adv=search_adv,
                target_pay_for_order=target_pay,
                shop_id=shop_id,
                get_keywords_func=None,
            )

        logger.debug(
            "PostgresSnapshotProviderLive shop_id=%s adv_count=%d",
            shop_id,
            len(settings_dtos),
        )
        return PostgresShopSnapshotLoad(
            shop_id=shop_id,
            settings=settings_dtos,
            complex_advs_by_id=complex_by_id,
        )
