"""Фаза 8: resolve calibration UP/DOWN."""

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
    plan_resolve_calibration,
)


class ResolveCalibrationExecutor(UpdateExecutor):
    """RESOLVE_CALIBRATION (UP или DOWN за тик)."""

    phase_name = "resolve_calibration"

    def check_skip(self, context: UpdateContext) -> str | None:
        state = context.adv_state
        if not state.resolve_valid:
            return "resolve_invalid"
        if not state.calibration_in_range:
            return "fact_gt_max"
        if state.guard_applied:
            return "guard_applied"
        if state.plan_fact_equal and state.views_equal:
            return "plan_fact_unchanged_and_views_unchanged"
        if state.plan_fact_equal:
            return "plan_fact_unchanged"
        if state.views_equal:
            return "views_unchanged"
        if state.calibration_direct is None:
            return "no_direct"
        return None

    def plan_actions(self, context: UpdateContext) -> list[V3Action]:
        state = context.adv_state
        assert state.calibration_direct is not None
        return plan_resolve_calibration(
            context.prepared,
            resolve=float(state.resolve),
            calibration_direct=state.calibration_direct,
            shelf_click_mode=state.shelf_click_mode,
            aggressiveness=state.aggressiveness,
            eligibility_by_ks_id=state.eligibility_by_ks_id,
            ladder_inputs=state.ladder_inputs,
            max_effective_steps=state.max_effective_steps,
        )
