from __future__ import annotations

import logging
from collections.abc import Callable, Iterable, Awaitable
from datetime import datetime, time, timedelta, timezone

from app.core.mp.wb.api.managers import WBModifier
from app.modules.shop_runner.service_manager.services.plan_fact_controller.plan_fact_reader import (
    PlanFactReader,
    PlanFactSummary,
)
from app.modules.shop_runner.service_manager.wb_shop_data_manager.dto.complex_adv import (
    ComplexAdv,
)
from app.modules.shop_runner.tasks_manager.tasks_manager import TasksManager, run_tasks
from app.modules.shop_runner.wb_stat_manager.clickhouse_manager import full_wb_adv_stat
from app.shared.enums.wb_adv_active_status import WBAdvActiveStatus

logger = logging.getLogger(__name__)

MSK_TZ = timezone(timedelta(hours=3))


class AutoAdvActiveControlService:
    def __init__(
        self,
        wb_modifier: WBModifier,
        tasks_manager: TasksManager,
        plan_fact_reader: PlanFactReader | None = None,
    ) -> None:
        self._wb_modifier = wb_modifier
        self._tasks_manager = tasks_manager
        self._plan_fact_reader = plan_fact_reader or PlanFactReader() # просят тесты, потом все это исправить, техдолг

    async def ensure_campaigns_active(self, advs: Iterable[ComplexAdv]) -> None:
        complex_advs = [
            adv
            for adv in advs
            if adv.bot_active and adv.auto_budget_watchdog_enabled
        ]
        if not complex_advs:
            return None

        handlers: list[Callable[[], Awaitable[None]]] = []

        now_msk = datetime.now(MSK_TZ)
        start_of_day = datetime.combine(now_msk.date(), time.min, tzinfo=MSK_TZ)
        end_of_day = datetime.combine(now_msk.date(), time.max, tzinfo=MSK_TZ)

        for adv in complex_advs:
            handlers.append(
                lambda complex_adv=adv: self._auto_campaign_handler(
                    complex_adv, start_of_day, end_of_day
                )
            )
            handlers.append(
                lambda complex_adv=adv: self._search_campaign_handler(
                    complex_adv, start_of_day, end_of_day
                )
            )

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

    @staticmethod
    async def _get_spend_for_adv(
        adv_id: int | None,
        start_date: datetime,
        end_date: datetime,
    ) -> float:
        if adv_id is None:
            return 0.0
        return await full_wb_adv_stat.get_spend_by_last_days(
            [adv_id],
            start_date,
            end_date,
        )
    @staticmethod
    async def _get_average_order_cost(adv_id: int) -> float | None:
        now = datetime.now(MSK_TZ)
        start_date = (now - timedelta(days=6)).replace(
            hour=0, minute=0, second=0, microsecond=0
        )
        stats = await full_wb_adv_stat.get_stats_by_last_days(
            [adv_id], start_date, now
        )
        if stats.orders == 0:
            return float("inf") if stats.spend > 0 else 0.0
        return stats.spend / stats.orders

    @staticmethod
    def _resolve_target_cost(summary: PlanFactSummary | None) -> float | None:
        if not summary:
            return None
        if (
            summary.plan_orders is None
            or summary.plan_target_pay_for_order is None
            or summary.plan_max_pay_for_order is None
        ):
            return None
        fact_orders = summary.fact_predict_orders or 0.0
        if fact_orders >= summary.plan_orders:
            return summary.plan_target_pay_for_order
        return summary.plan_max_pay_for_order

    async def _auto_campaign_handler(
        self,
        adv: ComplexAdv,
        start_of_day: datetime,
        end_of_day: datetime,
    ) -> None:
        auto_adv_id = adv.auto_adv_id
        plan_fact_summary = await self._plan_fact_reader.get_latest_plan_fact(auto_adv_id )
        spend_today = await self._get_spend_for_adv(auto_adv_id , start_of_day, end_of_day)
        auto_limit = adv.auto_budget_daily_limit or 0
        auto_status = adv.auto_adv_active_status_str

        if 0 < auto_limit <= spend_today:
            if auto_status == WBAdvActiveStatus.STARTED:
                logger.info(
                    "Auto budget watcher: pausing auto campaign because spend %.2f >= limit %s adv_id=%s shop_id=%s",
                    spend_today,
                    auto_limit,
                    auto_adv_id ,
                    adv.shop_id,
                )
                await self._wb_modifier.pause_auto_campaign(adv)
            return

        auto_limit_action_taken = False
        if auto_limit > 0 and auto_status in [WBAdvActiveStatus.PAUSE, WBAdvActiveStatus.READY_FOR_START]:
            logger.info(
                "Auto budget watcher: starting auto campaign adv_id=%s shop_id=%s",
                auto_adv_id ,
                adv.shop_id,
            )
            await self._wb_modifier.start_auto_campaign(adv)
            auto_status = WBAdvActiveStatus.STARTED
            auto_limit_action_taken = True
        elif auto_limit == 0 and auto_status == WBAdvActiveStatus.STARTED:
            logger.info(
                "Auto budget watcher: pausing auto campaign adv_id=%s shop_id=%s",
                auto_adv_id,
                adv.shop_id,
            )
            await self._wb_modifier.pause_auto_campaign(adv)
            auto_status = WBAdvActiveStatus.PAUSE
            auto_limit_action_taken = True

        if auto_limit_action_taken:
            return

        target_cost = self._resolve_target_cost(plan_fact_summary)
        if target_cost is None:
            return

        avg_cost = await self._get_average_order_cost(auto_adv_id)
        if avg_cost is None:
            return

        if avg_cost > target_cost and auto_status == WBAdvActiveStatus.STARTED:
            logger.info(
                "Auto watchdog: pausing auto campaign due to high avg cost %.2f vs target %.2f adv_id=%s shop_id=%s",
                avg_cost,
                target_cost,
                auto_adv_id ,
                adv.shop_id,
            )
            await self._wb_modifier.pause_auto_campaign(adv)
        elif avg_cost <= target_cost and auto_status == WBAdvActiveStatus.PAUSE:
            logger.info(
                "Auto watchdog: starting auto campaign since avg cost %.2f <= target %.2f adv_id=%s shop_id=%s",
                avg_cost,
                target_cost,
                auto_adv_id ,
                adv.shop_id,
            )
            await self._wb_modifier.start_auto_campaign(adv)

    async def _search_campaign_handler(
        self,
        adv: ComplexAdv,
        start_of_day: datetime,
        end_of_day: datetime,
    ) -> None:
        adv_id = adv.search_adv_id
        if adv_id is None:
            return None

        spend_today = await self._get_spend_for_adv(adv_id, start_of_day, end_of_day)
        search_limit = adv.search_auto_budget_daily_limit or 0
        search_status = adv.search_adv_active_status_str

        if 0 < search_limit <= spend_today:
            if search_status == WBAdvActiveStatus.STARTED:
                logger.info(
                    "Auto budget watcher: pausing auction campaign because spend %.2f >= limit %s adv_id=%s shop_id=%s",
                    spend_today,
                    search_limit,
                    adv_id,
                    adv.shop_id,
                )
                await self._wb_modifier.pause_auction_campaign(adv)
            return

        if search_limit > 0 and search_status == WBAdvActiveStatus.PAUSE:
            logger.info(
                "Auto budget watcher: starting auction campaign adv_id=%s shop_id=%s",
                adv_id,
                adv.shop_id,
            )
            await self._wb_modifier.start_auction_campaign(adv)
        elif search_limit == 0 and search_status == WBAdvActiveStatus.STARTED:
            logger.info(
                "Auto budget watcher: pausing auction campaign adv_id=%s shop_id=%s",
                adv_id,
                adv.shop_id,
            )
            await self._wb_modifier.pause_auction_campaign(adv)
