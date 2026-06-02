"""ClickHouse snapshot provider: Stub и Live (read-only batch).

Live делегирует в существующие компоненты shop_runner:
- ``PlanFactReader.get_latest_plan_facts`` — plan/fact;
- ``ClickHouseManager.get_cluster_texts_for_adv_ids`` — norm_query кластеров.
"""

from __future__ import annotations

import logging
from collections.abc import Sequence

from app.modules.shop_runner.service_manager.services.minus_phrase_manager.click_house_manager.click_house_manager import (
    ClickHouseManager,
)
from app.modules.shop_runner.service_manager.services.plan_fact_controller.plan_fact_reader import (
    PlanFactReader,
)
from app.snapshot_data_updater.dto import PlanFactSnapshotDTO

logger = logging.getLogger(__name__)


class StubClickHouseSnapshotProvider:
    """Фикстуры plan/fact и cluster texts для unit-тестов."""

    def __init__(
        self,
        *,
        plan_facts_by_shop: dict[str, dict[int, PlanFactSnapshotDTO]] | None = None,
        cluster_texts_by_auction: dict[int, set[str]] | None = None,
    ) -> None:
        self._by_shop = plan_facts_by_shop or {}
        self._cluster_texts = cluster_texts_by_auction or {}

    async def fetch_plan_facts(
        self, shop_id: str, adv_ids: Sequence[int]
    ) -> dict[int, PlanFactSnapshotDTO]:
        shop_map = self._by_shop.get(shop_id, {})
        return {aid: shop_map[aid] for aid in adv_ids if aid in shop_map}

    async def fetch_cluster_texts_by_auction_adv(
        self, auction_adv_ids: Sequence[int]
    ) -> dict[int, set[str]]:
        return {
            aid: set(self._cluster_texts.get(aid, set()))
            for aid in auction_adv_ids
            if aid in self._cluster_texts
        }


class ClickHouseSnapshotProviderLive:
    """Read-only CH: один batch plan/fact и один batch cluster texts на shop."""

    def __init__(
        self,
        *,
        plan_fact_reader: PlanFactReader | None = None,
        cluster_manager: ClickHouseManager | None = None,
    ) -> None:
        self._plan_fact_reader = plan_fact_reader or PlanFactReader()
        self._cluster_manager = cluster_manager or ClickHouseManager()

    async def fetch_plan_facts(
        self, shop_id: str, adv_ids: Sequence[int]
    ) -> dict[int, PlanFactSnapshotDTO]:
        if not adv_ids:
            return {}
        from app.utils.ch_semaphore import run_ch_with_timeout

        summaries = await run_ch_with_timeout(
            self._plan_fact_reader.get_latest_plan_facts(list(adv_ids))
        )
        out: dict[int, PlanFactSnapshotDTO] = {}
        for adv_id, summary in summaries.items():
            fact_orders = (
                summary.fact_original_orders
                if summary.fact_original_orders is not None
                else summary.fact_predict_orders
            )
            out[adv_id] = PlanFactSnapshotDTO(
                adv_id=adv_id,
                fact_orders=fact_orders,
                fact_predict_orders=summary.fact_predict_orders,
                fact_pay_for_order=summary.fact_pay_for_order,
                fact_method=summary.fact_method,
            )
        logger.debug(
            "ClickHouseSnapshotProviderLive plan_facts shop_id=%s count=%d",
            shop_id,
            len(out),
        )
        return out

    async def fetch_cluster_texts_by_auction_adv(
        self, auction_adv_ids: Sequence[int]
    ) -> dict[int, set[str]]:
        if not auction_adv_ids:
            return {}
        from app.utils.ch_semaphore import run_ch_with_timeout

        return await run_ch_with_timeout(
            self._cluster_manager.get_cluster_texts_for_adv_ids(
                list(auction_adv_ids)
            )
        )
