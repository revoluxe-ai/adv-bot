"""Фаза G.2: max CPA guard trim."""

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
    plan_max_cpa_guard_phase,
)


class MaxCpaGuardExecutor(UpdateExecutor):
    """MAX_CPA_GUARD."""

    phase_name = "max_cpa_guard"

    def check_skip(self, context: UpdateContext) -> str | None:
        if not context.adv_state.guard_condition:
            return "fact_le_max"
        return None

    def plan_actions(self, context: UpdateContext) -> list[V3Action]:
        state = context.adv_state
        return plan_max_cpa_guard_phase(
            context.prepared,
            max_pay_for_order=state.max_pay_for_order,
            shelf_click_mode=state.shelf_click_mode,
            aggressiveness=state.aggressiveness,
            eligibility_by_ks_id=state.eligibility_by_ks_id,
            ladder_inputs=state.ladder_inputs,
        )
