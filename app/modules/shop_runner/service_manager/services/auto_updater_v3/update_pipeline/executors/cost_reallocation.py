"""Фаза R: cost reallocation."""

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
from app.modules.shop_runner.service_manager.services.auto_updater_v3.rollout_planner import (
    plan_cost_reallocation,
)


class RebalanceExecutor(UpdateExecutor):
    """COST_REALLOCATION."""

    phase_name = "cost_reallocation"

    def check_skip(self, context: UpdateContext) -> str | None:
        if not context.adv_state.resolve_valid:
            return "resolve_invalid"
        return None

    def plan_actions(self, context: UpdateContext) -> list[V3Action]:
        state = context.adv_state
        return plan_cost_reallocation(
            context.prepared,
            resolve=state.resolve,
            policy=state.policy,
            eligibility_by_ks_id=state.eligibility_by_ks_id,
            ladder_inputs=state.ladder_inputs,
        )
