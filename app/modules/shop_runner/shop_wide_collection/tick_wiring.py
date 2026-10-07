"""Production wiring shop-wide unmanaged tick в shop-runner (задача 8.1).

Spec: ``connected-shop-campaign-ad-data-collection``.
Debt: ``openspec/architectural-debt/TEMPORARY_DUAL_CAMPAIGN_COLLECTION.md``.
Decision: ``openspec/changes/shop-wide-campaign-data-collection/decisions/shop-runner-shop-wide-collection/decision.md``.

Связывает ``collect_unmanaged_campaign_advertising`` с thin ends shop-runner:
WB discovery (promotion stack), ClickHouse inventory/availability, managed
``full_adv_wb_stat`` writer. **MUST NOT** вызывать ``scripts/`` Job entry,
``update_advs_in_db``, funnel или clusters collectors.
"""

from __future__ import annotations

import logging
from collections.abc import Iterable, Mapping, Sequence

from app.core.di.wb_manager_hub.wb_manager_hub import WBManagerHub
from app.core.mp.wb.api.domain_managers.promotion.promotion_manager import (
    PromotionManager,
)
from app.core.mp.wb.api.generated.promotion.v2.marketing_and_promotions_client.models import (
    GetAdvertsAdvertsItem,
)
from app.modules.attribution_facts.membership.history_ch_adapter import (
    CampaignSettingsHistoryAsOfAdapter,
)
from app.modules.attribution_facts.membership.inventory_ch_adapter import (
    ShopCampaignInventoryNmAdapter,
)
from app.modules.full_stat_adv_updater import wb_data_getter
from app.modules.full_stat_adv_updater.types.full_adv_stat import FullAdvStat
from app.modules.shop_runner.service_manager.wb_shop_data_manager.dto.complex_adv import (
    ComplexAdv,
)
from app.modules.shop_runner.shop_wide_collection.unmanaged_orchestrator import (
    UnmanagedCollectTickResult,
    collect_unmanaged_campaign_advertising,
)
from app.modules.shop_runner.wb_stat_manager.clickhouse_manager import full_wb_adv_stat
from app.settings import settings
from app.utils.click_house.clickhouse_protocol import ClickHouseClientProtocol
from app.utils.click_house.client import get_clickhouse_client

logger = logging.getLogger(__name__)


class _QueryRows:
    """Минимальный view ответа CH ``query`` для inventory/availability writers."""

    def __init__(self, result_rows: Sequence[Sequence[object]]) -> None:
        self.result_rows = result_rows


class _ClickHouseShopWideClient:
    """Единый CH-клиент для inventory upsert, route read и availability append."""

    def __init__(self, client: ClickHouseClientProtocol) -> None:
        self._client = client

    async def query(
        self,
        query: str,
        parameters: Mapping[str, object] | None = None,
    ) -> _QueryRows:
        rows = await self._client.query(query, parameters=parameters)
        return _QueryRows(rows.result_rows)


class _WbCabinetCampaignDiscovery:
    """WB discovery через ``PromotionManager.discover_cabinet_campaigns`` (design L1)."""

    def __init__(self, promotion_manager: PromotionManager) -> None:
        self._promotion_manager = promotion_manager

    async def get_all_campaigns(self) -> list[GetAdvertsAdvertsItem]:
        """Список кампаний кабинета для resolver/inventory tick."""
        return await self._promotion_manager.discover_cabinet_campaigns()


class _ProductionFullAdvStatFetcher:
    """Thin end: ``wb_data_getter.get_full_adv_stat_for_adv_ids``."""

    def __init__(self, wb_manager_hub: WBManagerHub) -> None:
        self._wb_manager_hub = wb_manager_hub

    async def get_full_adv_stat_for_adv_ids(
        self,
        adv_ids: set[int],
        threshold_dates: int,
    ) -> list[FullAdvStat]:
        return await wb_data_getter.get_full_adv_stat_for_adv_ids(
            self._wb_manager_hub.wb_data_manager,
            adv_ids,
            threshold_dates=threshold_dates,
        )


class _ProductionFullAdvStatWriter:
    """Thin end: ``full_wb_adv_stat.insert`` без management side effects."""

    async def insert(self, stats: Iterable[FullAdvStat]) -> None:
        await full_wb_adv_stat.insert(stats)


async def run_shop_wide_unmanaged_tick(
    *,
    shop_id: str,
    loader_complex_advs: Sequence[ComplexAdv],
    wb_manager_hub: WBManagerHub,
) -> UnmanagedCollectTickResult:
    """Один shop-wide unmanaged tick с production thin ends shop-runner.

    Side effects: WB read, CH inventory/availability/full_adv_wb_stat.
    **MUST NOT** PG enrollment или management writes.

    Args:
        shop_id: идентификатор магазина shop-runner.
        loader_complex_advs: post-filter ``get_complex_advs(only_bot_active=False)``.
        wb_manager_hub: DI hub магазина (WB data + token plane).

    Returns:
        Сводка resolver/inventory/unmanaged collect для tick/tests.
    """
    if shop_id == "":
        raise ValueError("shop_id must be a non-empty string")

    promotion_manager = wb_manager_hub.wb_data_manager.promotion_manager
    discovery = _WbCabinetCampaignDiscovery(promotion_manager)
    fetcher = _ProductionFullAdvStatFetcher(wb_manager_hub)
    writer = _ProductionFullAdvStatWriter()

    async with get_clickhouse_client() as ch_client:
        ch_adapter = _ClickHouseShopWideClient(ch_client)
        history_port = CampaignSettingsHistoryAsOfAdapter(ch_client)
        inventory_nm_port = ShopCampaignInventoryNmAdapter(ch_adapter)
        result = await collect_unmanaged_campaign_advertising(
            shop_id=shop_id,
            loader_complex_advs=loader_complex_advs,
            campaigns_discovery=discovery,
            inventory_client=ch_adapter,
            availability_client=ch_adapter,
            full_adv_stat_fetcher=fetcher,
            full_adv_stat_writer=writer,
            threshold_dates=settings.FULL_STAT_THRESHOLD_DATES,
            attribution_history_port=history_port,
            attribution_inventory_port=inventory_nm_port,
        )

    logger.info(
        "shop-wide unmanaged tick wired shop_id=%s discovered=%s eligible=%s "
        "full_adv_rows=%s",
        shop_id,
        result.wb_discovered_count,
        len(result.unmanaged_eligible_adv_ids),
        result.full_adv_stats_written,
    )
    return result
