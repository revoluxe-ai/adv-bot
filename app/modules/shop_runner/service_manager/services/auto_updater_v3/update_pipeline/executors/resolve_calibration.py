"""Фаза 8: resolve calibration UP/DOWN in-place через ``StatesListGenerator``."""

from __future__ import annotations

from app.modules.shop_runner.service_manager.services.auto_updater_v3.calibration_step_resolver import (
    CalibrationDirect,
)
from app.modules.shop_runner.service_manager.services.auto_updater_v3.keyword_dto.dto.update_context import (
    UpdateContext,
)
from app.modules.shop_runner.service_manager.services.auto_updater_v3.update_pipeline.executors.calibration_runner import (
    run_calibration_down,
    run_calibration_up,
)
from app.modules.shop_runner.service_manager.services.auto_updater_v3.update_pipeline.next_state.manager import (
    NextStateManager,
)


class ResolveCalibrationExecutor:
    """RESOLVE_CALIBRATION (UP или DOWN за тик)."""

    phase_name = "resolve_calibration"
    _skip_reason: str | None = None

    def __init__(self) -> None:
        self._next_state_manager = NextStateManager(ResolveCalibrationExecutor)

    def execute(self, context: UpdateContext) -> None:
        self._skip_reason = _phase_skip_reason(context)
        if self._skip_reason is not None:
            return
        state = context.adv_state
        assert state.calibration_direct is not None
        if state.calibration_direct == CalibrationDirect.TIGHTEN:
            run_calibration_down(
                context,
                resolve=float(state.resolve),
                max_steps=state.max_effective_steps,
                nsm=self._next_state_manager,
            )
            return
        run_calibration_up(
            context,
            max_steps=state.max_effective_steps,
            nsm=self._next_state_manager,
        )

    @property
    def skip_reason(self) -> str | None:
        return self._skip_reason


def _phase_skip_reason(context: UpdateContext) -> str | None:
    """Gate preamble calibration (без изменений от legacy executor)."""
    state = context.adv_state
    if not state.resolve_valid:
        return "resolve_invalid"
    if not state.calibration_in_range:
        return "fact_gt_max"
    if state.plan_fact_equal and state.views_equal:
        return "plan_fact_unchanged_and_views_unchanged"
    if state.plan_fact_equal:
        return "plan_fact_unchanged"
    if state.views_equal:
        return "views_unchanged"
    if state.calibration_direct is None:
        return "no_direct"
    return None
