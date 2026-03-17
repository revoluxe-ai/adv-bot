from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING, Any

from app.modules.plan_fact.provider import PlanFactProvider
from app.modules.common_slaves.wildberries.models.enums.strategy import Strategy
from app.modules.wb_adv_updater.calculated_keywords_manager.dto.states import KeywordStatus
from app.shared.domains.wb.utils.cost_resolver import resolve_target_cost

from .plan_fact_controller.plan_fact_reader import PlanFactReader

if TYPE_CHECKING:
    from app.modules.shop_runner.service_manager.wb_shop_data_manager.dto.complex_adv.complex_adv import (
        ComplexAdv,
    )
    from app.modules.wb_adv_updater.calculated_keywords_manager.dto.calculated_keyword import (
        CalculatedKeyword,
    )


@dataclass(frozen=True)
class StrategySelection:
    strategy: Strategy
    reason: str


class AdvStrategySelector:
    @staticmethod
    def _is_target_cost_exceeded(
        *,
        plan: Any | None,
        summary: Any | None,
    ) -> bool:
        """True if plan/fact data exist and fact_pay_for_order > target_cost."""
        if plan is None or summary is None:
            return False
        fact_orders = summary.fact_predict_orders
        fact_pay_for_order = summary.fact_pay_for_order
        if fact_orders is None or fact_pay_for_order is None:
            return False
        target_cost = resolve_target_cost(
            plan.orders,
            plan.target_pay_for_order,
            plan.max_pay_for_order,
            fact_orders,
        )
        if target_cost is None:
            return False
        return fact_pay_for_order > target_cost

    @staticmethod
    def _select_by_plan_and_cost(
        *,
        plan: Any | None,
        summary: Any | None,
    ) -> StrategySelection | None:
        if plan is None or summary is None:
            return None

        fact_orders = summary.fact_predict_orders
        fact_pay_for_order = summary.fact_pay_for_order
        if fact_orders is None or fact_pay_for_order is None:
            return None

        target_cost = resolve_target_cost(
            plan.orders,
            plan.target_pay_for_order,
            plan.max_pay_for_order,
            fact_orders,
        )
        if target_cost is None:
            return None

        if fact_orders >= plan.orders:
            return StrategySelection(
                strategy=Strategy.MIN_CPO,
                reason="orders_reached_plan",
            )

        if fact_pay_for_order > target_cost:
            return StrategySelection(
                strategy=Strategy.MIN_CPO,
                reason="cost_above_target",
            )

        return StrategySelection(
            strategy=Strategy.MAX_CONV,
            reason="cost_below_or_equal_target",
        )

    async def select_target_strategy(
        self,
        complex_adv: ComplexAdv,
        *,
        plan_fact_reader: PlanFactReader,
    ) -> StrategySelection | None:
        plan = PlanFactProvider.get_plan_data(complex_adv.adv_setting)
        summary = None
        if plan is not None:
            summary = await plan_fact_reader.get_latest_plan_fact(complex_adv.adv_id)

        if self._is_target_cost_exceeded(plan=plan, summary=summary):
            return StrategySelection(
                strategy=Strategy.MIN_CPO,
                reason="cost_above_target",
            )
        if not complex_adv.rec_system_promotion_mode_active:
            return self._select_by_plan_and_cost(
                plan=plan,
                summary=summary,
            )

        if not complex_adv.auto_adv_active_status:
            return self._select_by_plan_and_cost(
                plan=plan,
                summary=summary,
            )

        keywords = await complex_adv.get_keywords()
        if self._all_shelf_keywords_activated(keywords):
            return StrategySelection(
                strategy=Strategy.MAX_CONV,
                reason="all_shelf_keywords_activated",
            )
        return StrategySelection(
            strategy=Strategy.MIN_CPO,
            reason="not_all_shelf_keywords_activated",
        )

    @staticmethod
    def _all_shelf_keywords_activated(keywords: list[CalculatedKeyword]) -> bool:
        # "Полочные" ключи: выше конверсии доп.показов.
        # Ключи, которые не могут быть включены вручную (hard_status 0/3), исключаем.
        candidates = [
            keyword
            for keyword in keywords
            if keyword.above_rec_conversion is True and keyword.hard_status not in {0, 3}
        ]
        # При пустом candidates all() даёт True намеренно: включать нечего, дальше двигать
        # товар можно только за счёт повышения конверсии → выбираем MAX_CONV.
        return all(keyword.status == KeywordStatus.GOOD for keyword in candidates)
