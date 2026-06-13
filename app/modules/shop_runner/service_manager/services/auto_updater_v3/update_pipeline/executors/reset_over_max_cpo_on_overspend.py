"""Фаза: при overspend сбросить GAP без CPO и ключи с state.cpo > plan.max в OFF/trim."""

from __future__ import annotations

from app.modules.common_slaves.wildberries.models.enums import KeywordStrategyMode
from app.modules.shop_runner.service_manager.services.auto_updater_v3.keyword_dto.dto import (
    AdvState,
    KeywordDTO,
)
from app.modules.shop_runner.service_manager.services.auto_updater_v3.keyword_dto.dto.keyword_v3_ladder_state import (
    KeywordV3LadderState,
)
from app.modules.shop_runner.service_manager.services.auto_updater_v3.keyword_dto.dto.update_context import (
    UpdateContext,
)
from app.modules.shop_runner.service_manager.services.auto_updater_v3.update_pipeline.executors.ladder_state_pick import (
    is_gap_without_operable_cpo,
    ladder_state_for_mode,
    pick_max_ladder_state_at_or_below_cpo,
    pick_off_ladder_state,
)
from app.modules.shop_runner.service_manager.services.auto_updater_v3.cpo_max_boundary import (
    ladder_cpo_within_ceiling,
)
from app.modules.shop_runner.service_manager.services.auto_updater_v3.update_pipeline.next_state.manager import (
    NextStateManager,
)


class ResetOverMaxCpoOnOverspendExecutor:
    """При ``fact > plan.max_pay_for_order``: GAP без CPO → OFF; иначе trim по ladder CPO."""

    phase_name = "reset_over_max_cpo_on_overspend"
    _skip_reason: str | None = None

    def __init__(self) -> None:
        self._next_state_manager = NextStateManager(ResetOverMaxCpoOnOverspendExecutor)

    def execute(self, context: UpdateContext) -> None:
        self._skip_reason = _phase_skip_reason(context.adv_state)
        if self._skip_reason is not None:
            return
        ceiling = float(context.adv_state.max_pay_for_order)
        for dto in context.keywords:
            state = _resolve_target_state(dto, ceiling)
            if state is not None:
                self._next_state_manager.raise_state_to_target_cpo(dto, state)

    @property
    def skip_reason(self) -> str | None:
        return self._skip_reason


def _phase_skip_reason(adv_state: AdvState) -> str | None:
    """Skip если нет fact или ``fact < plan.max_pay_for_order`` (не overspend)."""
    current_cpo_percent = _current_cpo_percent(adv_state)
    if current_cpo_percent is None:
        return "no_current_cpo_percent"
    if current_cpo_percent < 100.0:
        return "cpo_percent_lt_100"
    if adv_state.fact_pay_for_order is None:
        return "no_fact_pay_for_order"
    if not adv_state.guard_condition:
        return "fact_le_plan_max_cpo"
    return None


def _current_cpo_percent(adv_state: AdvState) -> float | None:
    fact_pay_for_order = adv_state.fact_pay_for_order
    if fact_pay_for_order is None:
        return None
    max_pay_for_order: object = getattr(adv_state, "max_pay_for_order", None)
    if not isinstance(max_pay_for_order, (int, float)):
        return None
    max_pay_for_order = float(max_pay_for_order)
    if max_pay_for_order <= 0:
        return None
    return float(fact_pay_for_order) / max_pay_for_order * 100.0


def _resolve_target_state(
    dto: KeywordDTO,
    ceiling: float,
) -> KeywordV3LadderState | None:
    """Target ladder-state или ``None`` если ключ уже соответствует условию."""
    if is_gap_without_operable_cpo(dto):
        if dto.current_mode == KeywordStrategyMode.OFF:
            return None
        return pick_off_ladder_state(dto)

    if dto.current_mode == KeywordStrategyMode.OFF:
        return None

    current = ladder_state_for_mode(dto, dto.current_mode)
    if current is None or current.cpo is None:
        return None
    if ladder_cpo_within_ceiling(float(current.cpo), float(ceiling)):
        return None

    target = pick_max_ladder_state_at_or_below_cpo(
        dto, ceiling, strict_ceiling=True
    )
    if target is not None:
        return target
    return pick_off_ladder_state(dto)
