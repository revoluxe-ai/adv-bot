"""NORMAL activation: one NO_CH/PFO OFF keyword → MIN_CPA + target_place=0 per tick."""

from __future__ import annotations

from collections.abc import Mapping

from app.modules.common_slaves.wildberries.models.enums import KeywordStrategyMode
from app.modules.shop_runner.service_manager.services.auto_updater_v3.cpo_max_boundary import (
    keyword_pfo_over_max,
)
from app.modules.shop_runner.service_manager.services.auto_updater_v3.keyword_dto.dto.adv_state import (
    AdvState,
)
from app.modules.shop_runner.service_manager.services.auto_updater_v3.keyword_v3_eligibility import (
    KeywordDataTier,
    KeywordV3Eligibility,
)
from app.modules.shop_runner.service_manager.services.auto_updater_v3.keyword_v3_tier import (
    keyword_pfo_value,
)
from app.modules.shop_runner.service_manager.services.auto_updater_v3.ladder_tick_helpers import (
    hard_status_allows_up,
)
from app.modules.shop_runner.service_manager.services.auto_updater_v3.keyword_dto.dto import (
    KeywordDTO,
)
from app.modules.shop_runner.service_manager.services.auto_updater_v3.keyword_dto.dto.update_context import (
    UpdateContext,
)
from app.modules.shop_runner.service_manager.services.auto_updater_v3.update_pipeline.next_state.manager import (
    NextStateManager,
)


class PayForOrderNoChEnableExecutor:
    """Enable one OFF keyword with no CH profile when ``keyword.pay_for_order`` below ceiling."""

    phase_name = "pay_for_order_no_ch_enable"
    _skip_reason: str | None = None

    def __init__(self) -> None:
        self._next_state_manager = NextStateManager(PayForOrderNoChEnableExecutor)

    def execute(self, context: UpdateContext) -> None:
        self._skip_reason = _phase_skip_reason(context)
        if self._skip_reason is not None:
            return
        candidate = _pick_no_ch_enable_candidate(
            context.keywords,
            context.adv_state,
            eligibility_by_ks_id=context.adv_state.eligibility_by_ks_id,
        )
        if candidate is None:
            self._skip_reason = "no_candidates"
            return
        self._next_state_manager.enable_off_to_min_cpa(candidate)

    @property
    def skip_reason(self) -> str | None:
        return self._skip_reason


def _phase_skip_reason(context: UpdateContext) -> str | None:
    if not context.adv_state.resolve_valid:
        return "resolve_invalid"
    return None


def _pick_no_ch_enable_candidate(
    keywords: list[KeywordDTO],
    adv_state: AdvState,
    *,
    eligibility_by_ks_id: Mapping[int, KeywordV3Eligibility],
) -> KeywordDTO | None:
    max_pay = float(adv_state.resolve)
    if adv_state.guard_condition:
        ceiling = adv_state.raise_cpo_ceiling
        if ceiling is not None:
            max_pay = min(max_pay, float(ceiling))
    candidates: list[KeywordDTO] = []
    for dto in keywords:
        if dto.current_mode != KeywordStrategyMode.OFF:
            continue
        if not hard_status_allows_up(int(dto.hard_status)):
            continue
        if bool(dto.position_profile):
            continue
        elig = eligibility_by_ks_id.get(dto.keyword_setting_id)
        if getattr(elig, "data_tier", None) != KeywordDataTier.KEYWORD_PFO:
            continue
        pfo = keyword_pfo_value(dto.calculated_keyword)
        if pfo is None:
            continue
        if keyword_pfo_over_max(pfo, max_pay):
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
