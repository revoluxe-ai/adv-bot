"""Выбор стратегии РК (MIN_CPO / MAX_CONV) по план-факту и полочному режиму.

Полочный режим (``rec_system_mode`` + авто ``started``) — отдельная ветка в
``select_target_strategy``. Вызывается из корутины ``change_adv_strategy`` (~1 мин),
после ``get_complex_advs(load_extras=True)`` и ``TrafficClicksManager.enrich``.

Сравнение кликов (``traffic_clicks_dto``):
    * **Полки** — клики авто-РК минус клики по ключевым фразам (рекомендации/полки).
    * **Органика** — переходы из воронки карточки минус все рекламные клики комплекса.

Влияние ``organic_clicks`` vs ``shelf_clicks`` (только если DTO заполнен):
    * ``organic_clicks > shelf_clicks`` → **MIN_CPO** (``organic_clicks_above_shelf_clicks``).
      Даже при отсутствии «недокрученных» полочных ключей **MAX_CONV не ставится**.
      Параллельно ``is_shelf_activation_allowed`` = False → в отбор кандидатов в БС
      попадают не только полочные ключи (см. ``KeywordsManager``).
    * ``shelf_clicks >= organic_clicks`` (или DTO нет) → сравнение кликов не режет в MIN_CPO;
      дальше смотрим pending полочные ключи.

«Докрутить» полочный ключ = довести до нормы, не просто включить: в авто (``hard_status=1``),
полочный (``above_rec_conversion``), статус **BAD**, не ``ABOVE_TARGET_AT_MIN_BID``.
Пока такие есть → **MIN_CPO**; когда список пуст → **MAX_CONV**.

Не путать с V3 ``auto_updater_v3`` (лестница UP/DOWN): здесь только поле ``AdvSetting.strategy``.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING, Any

from app.modules.plan_fact.provider import PlanFactProvider
from app.modules.common_slaves.wildberries.models.enums.strategy import Strategy
from app.modules.wb_adv_updater.calculated_keywords_manager.dto.states import KeywordStatus, KeywordStatusReason
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
    def _select_by_plan_and_cost(
        *,
        plan: Any | None,
        summary: Any | None,
    ) -> StrategySelection | None:
        """Базовая стратегия без полочной ветки: план/факт и порог себестоимости (``resolve_target_cost``)."""
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
        """Целевая стратегия РК.

        Без полок (``rec_system_mode`` выкл или авто не ``started``): только ``_select_by_plan_and_cost``.

        С полками (оба условия выше):
            1. Если план/факт уже требуют экономии → **MIN_CPO**, полочная логика не выполняется.
            2. Иначе при ``organic_clicks > shelf_clicks`` (есть DTO) → **MIN_CPO**.
            3. Иначе при отсутствии pending полочных ключей → **MAX_CONV**.
            4. Иначе → **MIN_CPO** (есть что докручивать в полочных ключах).

        ``reason`` в ``StrategySelection`` — для логов и диагностики.
        """
        plan = PlanFactProvider.get_effective_plan_data(
            complex_adv.adv_setting, complex_adv=complex_adv
        )
        summary = None
        if plan is not None:
            summary = await plan_fact_reader.get_latest_plan_fact(complex_adv.adv_id)

        plan_selection = self._select_by_plan_and_cost(
            plan=plan,
            summary=summary,
        )

        if not complex_adv.rec_system_promotion_mode_active:
            return plan_selection

        if not complex_adv.auto_adv_active_status:
            return plan_selection

        if plan_selection is not None and plan_selection.strategy == Strategy.MIN_CPO:
            return plan_selection

        traffic_clicks = complex_adv.traffic_clicks_dto
        if (
            traffic_clicks is not None
            and traffic_clicks.organic_clicks > traffic_clicks.shelf_clicks
        ):
            return StrategySelection(
                strategy=Strategy.MIN_CPO,
                reason="organic_clicks_above_shelf_clicks",
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
        """True, если не осталось полочных ключей, которые ещё нужно докрутить.

        Pending = ``above_rec_conversion``, ``hard_status == 1`` (авто), ``status == BAD``,
        ``reason != ABOVE_TARGET_AT_MIN_BID``. Пустой pending → можно **MAX_CONV** (в полочной ветке).
        """
        pending_shelf = [
            keyword
            for keyword in keywords
            if keyword.above_rec_conversion is True and keyword.hard_status == 1
               and keyword.status == KeywordStatus.BAD
               and keyword.reason != KeywordStatusReason.ABOVE_TARGET_AT_MIN_BID
        ]
        return not pending_shelf
