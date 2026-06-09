"""Фаза 8: resolve calibration UP/DOWN in-place через ``StatesListGenerator``."""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

from app.modules.shop_runner.service_manager.services.auto_updater_v3.calibration_step_resolver import (
    CalibrationDirect,
)
from app.modules.shop_runner.service_manager.services.auto_updater_v3.keyword_dto.dto.update_context import (
    UpdateContext,
)
if TYPE_CHECKING:
    from app.modules.shop_runner.service_manager.services.auto_updater_v3.keyword_dto.dto.keyword_dto import (
        KeywordDTO,
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
            self._reset_step(context)
            return

        state = context.adv_state
        assert state.calibration_direct is not None

        conflict = _direction_conflict_reason(context)
        if conflict is not None:
            self._skip_reason = conflict
            self._reset_step(context)
            return

        if state.calibration_direct == CalibrationDirect.TIGHTEN:
            run_calibration_down(
                context,
                resolve=float(state.resolve),
                max_steps=state.max_effective_steps,
                nsm=self._next_state_manager,
            )
            return

        up_result = run_calibration_up(
            context,
            max_steps=state.max_effective_steps,
            nsm=self._next_state_manager,
        )
        state.calibration_phase_extra["ladder_steps_done"] = up_result.ladder_steps_done
        state.calibration_phase_extra["cal_up_iterations"] = up_result.iterations_done
        state.calibration_phase_extra["cal_up_stop_reason"] = up_result.stop_reason

    @property
    def skip_reason(self) -> str | None:
        return self._skip_reason

    @staticmethod
    def _reset_step(context: UpdateContext) -> None:
        """Сбросить in-memory budget; Redis-сброс выполняет ``ApplyManager``."""
        context.adv_state.max_effective_steps = 0
        context.adv_state.calibration_phase_extra["effective_steps"] = 0


def _phase_skip_reason(context: UpdateContext) -> str | None:
    """Gate preamble calibration: только базовые данные, без unchanged plan/views."""
    state = context.adv_state
    if not state.resolve_valid:
        return "resolve_invalid"
    if state.fact_pay_for_order is None:
        return "no_fact_pay_for_order"
    if state.calibration_direct is None:
        return "no_direct"
    return None


@dataclass(frozen=True, slots=True)
class PriorExecutorEffects:
    """Derived per-key view of previous executor effects on the current tick."""

    up_applied: bool = False
    down_applied: bool = False
    force_off_applied: bool = False
    safety_action_applied: bool = False
    growth_action_applied: bool = False
    state_changed: bool = False
    target_place_changed: bool = False


_GROWTH_EXECUTOR_NAMES = {
    "RaiseStateToTargetCpoExecutor",
    "SkipUpTargetPlaceExecutor",
    "PayForOrderGapEnableExecutor",
    "ShelfCleanupExecutor",
    "RebalanceExecutor",
}
_DOWN_EXECUTOR_NAMES = {
    "RebalanceExecutor",
    "ResetOverMaxCpoOnOverspendExecutor",
    "ShelfCleanupExecutor",
    "PayForOrderOverMaxOffOnDeepOverspendExecutor",
}
_FORCE_OFF_EXECUTOR_NAMES = {
    "HardStatusValidateExecutor",
    "PayForOrderOverMaxOffOnDeepOverspendExecutor",
    "ResetOverMaxCpoOnOverspendExecutor",
    "ShelfCleanupExecutor",
}
_NEUTRAL_EXECUTOR_NAMES = {
    "NotFullTargetPlaceMigrateExecutor",
}


def _prior_executor_effects(context: UpdateContext) -> dict[int, PriorExecutorEffects]:
    return {
        dto.keyword_setting_id: _prior_executor_effects_for_dto(dto)
        for dto in context.keywords
    }


def _prior_executor_effects_for_dto(dto: KeywordDTO) -> PriorExecutorEffects:
    up_applied = False
    down_applied = False
    force_off_applied = False
    for step in dto.next_state:
        if step.executor_name in _GROWTH_EXECUTOR_NAMES:
            up_applied = True
        if step.executor_name in _DOWN_EXECUTOR_NAMES:
            down_applied = True
        if step.executor_name in _FORCE_OFF_EXECUTOR_NAMES:
            force_off_applied = True
    for step in dto.history_target_place:
        if step.executor_name in _NEUTRAL_EXECUTOR_NAMES:
            continue
    return PriorExecutorEffects(
        up_applied=up_applied,
        down_applied=down_applied,
        force_off_applied=force_off_applied,
        safety_action_applied=down_applied or force_off_applied,
        growth_action_applied=up_applied,
        state_changed=bool(dto.next_state),
        target_place_changed=bool(dto.history_target_place),
    )


def _direction_conflict_reason(context: UpdateContext) -> str | None:
    effects_by_key = _prior_executor_effects(context)
    if context.adv_state.calibration_direct == CalibrationDirect.LOOSEN:
        for dto in context.keywords:
            effects = effects_by_key.get(dto.keyword_setting_id)
            if effects is None:
                continue
            if effects.up_applied or effects.growth_action_applied:
                return "prior_up_blocks_calibration_up"
            if effects.safety_action_applied or effects.force_off_applied:
                return "prior_safety_blocks_reverse_up"
    else:
        for dto in context.keywords:
            effects = effects_by_key.get(dto.keyword_setting_id)
            if effects is None:
                continue
            if effects.down_applied or effects.force_off_applied:
                return "prior_down_blocks_calibration_down"
    return None
