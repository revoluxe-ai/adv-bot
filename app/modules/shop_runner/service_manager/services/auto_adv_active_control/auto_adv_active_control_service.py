from __future__ import annotations

import logging
from collections.abc import Callable, Iterable, Awaitable

from app.core.mp.wb.api.managers import WBModifier
from app.modules.shop_runner.service_manager.wb_shop_data_manager.dto.complex_adv import (
    ComplexAdv,
)
from app.modules.shop_runner.tasks_manager.tasks_manager import TasksManager, run_tasks
from app.shared.enums.wb_adv_active_status import WBAdvActiveStatus

logger = logging.getLogger(__name__)


class AutoAdvActiveControlService:
    def __init__(
        self,
        wb_modifier: WBModifier,
        tasks_manager: TasksManager,
    ) -> None:
        self._wb_modifier = wb_modifier
        self._tasks_manager = tasks_manager

    async def ensure_campaigns_active(self, advs: Iterable[ComplexAdv]) -> None:
        complex_advs = [
            adv
            for adv in advs
            if adv.bot_active and adv.auto_budget_watchdog_enabled
        ]
        if not complex_advs:
            return None

        handlers: list[Callable[[], Awaitable[None]]] = []

        for adv in complex_advs:
            self._schedule_auto_campaign_actions(adv, handlers)
            self._schedule_search_campaign_actions(adv, handlers)

        if not handlers:
            return None

        max_workers = self._max_workers_for(len(handlers), cap=16)
        results = await run_tasks(
            handlers,
            max_workers=max_workers,
            tasks_manager=self._tasks_manager,
        )

        for result in results:
            if isinstance(result, Exception):
                logger.error(
                    "Auto adv active control handler failed: %s", result
                )
        return None

    @staticmethod
    def _max_workers_for(handler_count: int, cap: int) -> int:
        return max(1, min(handler_count, cap))

    def _schedule_auto_campaign_actions(
        self,
        adv: ComplexAdv,
        handlers: list[Callable[[], Awaitable[None]]],
    ) -> None:

        auto_limit = adv.auto_budget_daily_limit or 0
        auto_status: str = adv.auto_adv_active_status_str
        adv_id = adv.auto_adv_id
        if auto_limit > 0 and auto_status == "pause":
            logger.info(
                "Auto budget watcher: starting auto campaign adv_id=%s shop_id=%s",
                adv_id,
                adv.shop_id,
            )
            handlers.append(
                lambda complex_adv=adv: self._wb_modifier.start_auto_campaign(
                    complex_adv
                )
            )
        elif auto_limit == 0 and auto_status == "started":
            logger.info(
                "Auto budget watcher: pausing auto campaign adv_id=%s shop_id=%s",
                adv_id,
                adv.shop_id,
            )
            handlers.append(
                lambda complex_adv=adv: self._wb_modifier.pause_auto_campaign(
                    complex_adv
                )
            )

    def _schedule_search_campaign_actions(
        self,
        adv: ComplexAdv,
        handlers: list[Callable[[], Awaitable[None]]],
    ) -> None:
        adv_id = adv.search_adv_id
        if adv_id is None:
            return None

        search_limit = adv.search_auto_budget_daily_limit or 0
        search_status = adv.search_adv_active_status_str

        if search_limit > 0 and search_status == WBAdvActiveStatus.PAUSE:
            logger.info(
                "Auto budget watcher: starting auction campaign adv_id=%s shop_id=%s",
                adv_id,
                adv.shop_id,
            )
            handlers.append(
                lambda complex_adv=adv: self._wb_modifier.start_auction_campaign(
                    complex_adv
                )
            )
        elif search_limit == 0 and search_status == WBAdvActiveStatus.STARTED:
            logger.info(
                "Auto budget watcher: pausing auction campaign adv_id=%s shop_id=%s",
                adv_id,
                adv.shop_id,
            )
            handlers.append(
                lambda complex_adv=adv: self._wb_modifier.pause_auction_campaign(
                    complex_adv
                )
            )
