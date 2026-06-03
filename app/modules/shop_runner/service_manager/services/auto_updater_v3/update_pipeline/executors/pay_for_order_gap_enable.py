"""Фаза enable: pay-for-order gap NO DATA enable."""

from __future__ import annotations

from app.modules.shop_runner.service_manager.services.auto_updater_v3.dto import (
    V3Action,
)
from app.modules.shop_runner.service_manager.services.auto_updater_v3.keywords_prepared.dto import (
    UpdateContext,
)
from app.modules.shop_runner.service_manager.services.auto_updater_v3.update_pipeline.executors.base import (
    UpdateExecutor,
)
from app.modules.shop_runner.service_manager.services.auto_updater_v3.v3_preamble_phases import (
    plan_pay_for_order_gap_enable,
)


class PayForOrderGapEnableExecutor(UpdateExecutor):
    """PAY_FOR_ORDER_GAP_ENABLE."""

    phase_name = "pay_for_order_gap_enable"

    def check_skip(self, context: UpdateContext) -> str | None:
        if not context.adv_state.resolve_valid:
            return "resolve_invalid"
        return None

    def plan_actions(self, context: UpdateContext) -> list[V3Action]:
        state = context.adv_state
        return plan_pay_for_order_gap_enable(
            context.prepared,
            eligibility_by_ks_id=state.eligibility_by_ks_id,
            fact_pay_for_order=state.fact_pay_for_order,
            resolve=float(state.resolve),
            plan_fact_changed=state.plan_fact_changed,
            views_changed=state.views_changed,
        )
