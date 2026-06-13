"""Фаза enable: один GAP-ключ OFF → MIN_CPA + target_place=0 за тик."""

from __future__ import annotations

from app.modules.common_slaves.wildberries.models.enums import KeywordStrategyMode
from app.modules.shop_runner.service_manager.services.auto_updater_v3.campaign_pfo_gates import (
    gap_enable_plan_headroom_floor,
)
from app.modules.shop_runner.service_manager.services.auto_updater_v3.cpo_max_boundary import (
    campaign_cpo_over_max,
    cmp_over_threshold,
)
from app.modules.shop_runner.service_manager.services.auto_updater_v3.keyword_dto.dto.adv_state import (
    AdvState,
)
from app.modules.shop_runner.service_manager.services.auto_updater_v3.keyword_dto.dto import (
    KeywordDTO,
)
from app.modules.shop_runner.service_manager.services.auto_updater_v3.keyword_dto.dto.update_context import (
    UpdateContext,
)
from app.modules.shop_runner.service_manager.services.auto_updater_v3.keyword_v3_eligibility import (
    KeywordDataTier,
)
from app.modules.shop_runner.service_manager.services.auto_updater_v3.keyword_v3_tier import (
    is_keyword_no_data,
)
from app.modules.shop_runner.service_manager.services.auto_updater_v3.ladder_tick_helpers import (
    hard_status_allows_up,
)
from app.modules.shop_runner.service_manager.services.auto_updater_v3.update_pipeline.executors.ladder_state_pick import (
    is_gap_ladder,
)
from app.modules.shop_runner.service_manager.services.auto_updater_v3.update_pipeline.next_state.manager import (
    NextStateManager,
)


class PayForOrderGapEnableExecutor:
    """PAY_FOR_ORDER_GAP_ENABLE: один GAP NO DATA OFF → MIN за тик in-place."""

    phase_name = "pay_for_order_gap_enable"
    _skip_reason: str | None = None

    def __init__(self) -> None:
        self._next_state_manager = NextStateManager(PayForOrderGapEnableExecutor)

    def execute(self, context: UpdateContext) -> None:
        self._skip_reason = _phase_skip_reason(context.adv_state)
        if self._skip_reason is not None:
            return
        candidate = _pick_gap_enable_candidate(
            context.keywords,
            context.adv_state,
        )
        if candidate is not None:
            self._next_state_manager.enable_gap_to_min_cpa(candidate)

    @property
    def skip_reason(self) -> str | None:
        return self._skip_reason


def _phase_skip_reason(adv_state: AdvState) -> str | None:
    """Skip если нет fact, overspend, вне headroom или resolve недоступен."""
    if float(adv_state.resolve) <= 0:
        return "resolve_invalid"
    if adv_state.fact_pay_for_order is None:
        return "no_fact_pay_for_order"
    fact = float(adv_state.fact_pay_for_order)
    if campaign_cpo_over_max(fact, float(adv_state.max_pay_for_order)):
        return "fact_gt_max_cpo"
    if cmp_over_threshold(
        fact,
        gap_enable_plan_headroom_floor(float(adv_state.max_pay_for_order)),
    ):
        return "fact_ge_plan_headroom_ratio"
    return None


def _pick_gap_enable_candidate(
    keywords: list[KeywordDTO],
    adv_state: AdvState,
) -> KeywordDTO | None:
    """Первый GAP-кандидат по ``(keyword_setting_id, text)`` или ``None``."""
    candidates: list[KeywordDTO] = []
    for dto in keywords:
        if dto.current_mode != KeywordStrategyMode.OFF:
            continue
        if not is_gap_ladder(dto):
            continue
        if not is_keyword_no_data(dto.calculated_keyword):
            continue
        if not hard_status_allows_up(int(dto.hard_status)):
            continue
        elig = adv_state.eligibility_by_ks_id.get(dto.keyword_setting_id)
        if elig is not None and elig.data_tier != KeywordDataTier.KEYWORD_NO_DATA:
            continue
        candidates.append(dto)
    if not candidates:
        return None
    return min(
        candidates,
        key=lambda dto: (
            dto.keyword_setting_id,
            dto.calculated_keyword.text,
        ),
    )
