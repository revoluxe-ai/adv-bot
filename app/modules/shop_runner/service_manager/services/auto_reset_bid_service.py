from __future__ import annotations

import logging
import typing
from collections.abc import Awaitable, Callable

from app.core.di.wb_manager_hub.wb_manager_hub import WBManagerHub
from app.modules.shop_runner.service_manager.services.auto_updater_v3.card_ab_hold.auto_bid_freeze import (
    should_freeze_auto_bid_mutations,
)
from app.modules.shop_runner.service_manager.wb_shop_data_manager.dto.complex_adv import (
    ComplexAdv,
)
from app.modules.shop_runner.tasks_manager.tasks_manager import TasksManager, run_tasks

logger = logging.getLogger(__name__)


class AutoResetBidService:
    def __init__(self, wb_manager_hub: WBManagerHub, tasks_manager: TasksManager) -> None:
        self._wb_manager = wb_manager_hub.wb_manager
        self._wb_modifier = wb_manager_hub.wb_modifier
        self._tasks_manager = tasks_manager

    async def ensure_auto_bids_minimum(self, advs: list[ComplexAdv]) -> None:
        """Сброс CPM авто-РК до минимума WB для активных bidder-кампаний.

        При A/B Hold freeze (``ACTIVE`` или post-confirm ``PENDING_SETUP`` —
        ``PENDING_INTENT`` / ``WB_SYNC`` / ``READY_ACTIVE``) кампания исключается
        из кандидатов (spec §21 / FINDING-PBH-003): ordinary AutoReset MUST NOT
        менять confirmed Auto bid до activate. ``OFF`` и pre-confirm
        ``PENDING_SETUP`` остаются eligible.
        """
        candidates = [
            adv
            for adv in advs
            if adv.bot_active
            and adv.bidder_for_auto
            and not should_freeze_auto_bid_mutations(
                adv.card_ab_hold_mode,
                getattr(adv, "card_ab_hold_phase", None),
            )
        ]

        try:
            min_bids = await self._wb_manager.get_min_bids_cache_only(
                candidates, context="auto_reset_bid_service"
            )
        except Exception as error:  # noqa: BLE001
            logger.error(
                "Не удалось получить минимальные ставки для сброса CPM: %s", error, exc_info=True
            )
            return None

        if not min_bids.auto:
            return None

        handlers: list[Callable[[], Awaitable[None]]] = []
        target_advs: list[ComplexAdv] = []

        for adv in candidates:
            nmids_with_min = [nmid for nmid in adv.nmids if nmid in min_bids.auto]
            if not nmids_with_min:
                continue
            target_cpm = max(int(min_bids.auto[nmid]) for nmid in nmids_with_min)
            current_cpm = typing.cast(int | None, adv.adv_setting.cpm)
            if current_cpm == target_cpm:
                continue

            handlers.append(
                lambda auto_adv_id_=adv.auto_adv_id, target_cpm_=target_cpm,
                       nmids_=nmids_with_min: self._reset_adv_cpm # noqa
                    (
                    auto_adv_id=auto_adv_id_, target_cpm=target_cpm_, nmids=nmids_
                )
            )
            target_advs.append(adv)

        if not handlers:
            return None

        results = await run_tasks(
            handlers,
            max_workers=self._max_workers_for(len(handlers), cap=16),
            tasks_manager=self._tasks_manager,
            return_exceptions=True,
        )

        for adv, result in zip(target_advs, results):
            if isinstance(result, Exception):
                logger.error(
                    "Не удалось сбросить ставку для adv_id=%s shop_id=%s: %s",
                    adv.adv_id,
                    adv.shop_id,
                    result,
                    exc_info=True,
                )
        return None

    async def _reset_adv_cpm(
        self, auto_adv_id: int, target_cpm: int, nmids: list[int]
    ) -> None:
        adv_id = auto_adv_id
        nm_bid_pairs = {nmid: target_cpm for nmid in nmids}
        await self._wb_modifier.update_auto_adv_cpm(adv_id, nm_bid_pairs)
        return None

    @staticmethod
    def _max_workers_for(handler_count: int, cap: int) -> int:
        return max(1, min(handler_count, cap))
