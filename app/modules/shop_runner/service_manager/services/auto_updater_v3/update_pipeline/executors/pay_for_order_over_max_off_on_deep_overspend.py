"""Фаза: в зоне «1 от MAX плана» (fact ≥ ratio×plan.max, default ratio=1) — OFF ключей с PFO > max."""

from __future__ import annotations

from app.modules.common_slaves.wildberries.models.enums import KeywordStrategyMode
from app.modules.shop_runner.service_manager.services.auto_updater_v3.campaign_pfo_gates import (
    is_deep_overspend,
    keyword_pay_for_order_over_plan_max,
)
from app.modules.shop_runner.service_manager.services.auto_updater_v3.keyword_dto.dto import (
    AdvState,
    KeywordDTO,
)
from app.modules.shop_runner.service_manager.services.auto_updater_v3.keyword_dto.dto.update_context import (
    UpdateContext,
)
from app.modules.shop_runner.service_manager.services.auto_updater_v3.update_pipeline.executors.ladder_state_pick import (
    pick_off_ladder_state,
    resolve_current_ladder_state,
)
from app.modules.shop_runner.service_manager.services.auto_updater_v3.update_pipeline.next_state.manager import (
    NextStateManager,
)
from app.modules.shop_runner.service_manager.services.auto_updater_v3.v3_operable_keywords import (
    is_v3_operable_hard_status,
)


class PayForOrderOverMaxOffOnDeepOverspendExecutor:
    """OFF operable ключей с ``pay_for_order > max`` при ``fact ≥ ratio×plan.max``."""

    phase_name = "pay_for_order_over_max_off_on_deep_overspend"
    _skip_reason: str | None = None

    def __init__(self) -> None:
        self._next_state_manager = NextStateManager(
            PayForOrderOverMaxOffOnDeepOverspendExecutor
        )

    def execute(self, context: UpdateContext) -> None:
        self._skip_reason = _phase_skip_reason(context.adv_state)
        if self._skip_reason is not None:
            return
        ceiling = float(context.adv_state.max_pay_for_order)
        for dto in context.keywords:
            if not _should_off_keyword(dto, max_pay=ceiling):
                continue
            off_state = pick_off_ladder_state(dto)
            if off_state is None:
                continue
            self._next_state_manager.raise_state_to_target_cpo(dto, off_state)

    @property
    def skip_reason(self) -> str | None:
        return self._skip_reason


def _phase_skip_reason(adv_state: AdvState) -> str | None:
    """Skip если нет fact или fact < ratio×plan.max (вне зоны «1 от MAX»)."""
    if adv_state.fact_pay_for_order is None:
        return "no_fact_pay_for_order"
    if not is_deep_overspend(adv_state):
        return "fact_lt_plan_headroom_ratio"
    return None


def _should_off_keyword(dto: KeywordDTO, *, max_pay: float) -> bool:
    """Operable, не OFF; OFF только если нет ladder-ступени с ``cpo <= max`` и PFO > max.

    После R↑ ключ может иметь aggregate ``pay_for_order`` выше плана, но operable
    ступень CH с ``cpo <= max_pay`` — такой ключ не гасим (regression: R↑ → pfo_off).
    """
    if not is_v3_operable_hard_status(dto.hard_status):
        return False
    if dto.keyword_setting_id == 0:
        return False
    if dto.current_mode == KeywordStrategyMode.OFF:
        return False
    ceiling = float(max_pay)
    current = resolve_current_ladder_state(dto)
    if (
        current is not None
        and current.cpo is not None
        and float(current.cpo) <= ceiling
    ):
        return False
    return keyword_pay_for_order_over_plan_max(dto, max_pay=ceiling)
