"""Prod-хелперы ladder/cost для tick-report, gap enable и context manager."""

from __future__ import annotations

from typing import TYPE_CHECKING

from app.modules.common_slaves.wildberries.models.enums import KeywordStrategyMode
from app.modules.shop_runner.service_manager.services.auto_updater_v3.candidates import (
    build_mode_candidates,
)
from app.modules.shop_runner.service_manager.services.auto_updater_v3.dto import (
    AggressionTargetMode,
    ModeCandidate,
)
from app.modules.shop_runner.service_manager.services.auto_updater_v3.keyword_v3_decision_data import (
    effective_conv_for_v3,
)
from app.modules.shop_runner.service_manager.services.auto_updater_v3.transition_ranking import (
    PreparedList,
)
from app.modules.shop_runner.service_manager.services.auto_updater_v3.v3_operable_keywords import (
    HARD_STATUS_AUTO_MODE,
    HARD_STATUS_WHITE_LIST,
    is_v3_operable_hard_status,
)

if TYPE_CHECKING:
    from app.modules.shop_runner.service_manager.services.auto_updater_v3.keyword_v3_eligibility import (
        KeywordV3Eligibility,
    )
    from app.modules.shop_runner.service_manager.services.auto_updater_v3.keyword_v3_ladder_view import (
        LadderInputs,
    )
    from app.modules.shop_runner.service_manager.services.auto_updater_v3.selector import (
        KeywordV3Context,
    )


def hard_status_allows_up(hard_status: int) -> bool:
    """UP (ladder): авто (1) и белый список (2)."""
    return is_v3_operable_hard_status(hard_status)


def ladder_inputs_for_prepared(
    prepared: PreparedList,
    ladder_inputs: LadderInputs | None = None,
) -> LadderInputs:
    """Единый ``LadderInputs`` на проход; worst только в ``ladder_inputs.worst_costs``."""
    from app.modules.shop_runner.service_manager.services.auto_updater_v3.keyword_v3_ladder_view import (
        LadderInputs as _LadderInputs,
    )

    if ladder_inputs is not None:
        return ladder_inputs
    return _LadderInputs.from_contexts([ctx for ctx, _ in prepared])


def mode_catalog_for_ctx(
    ctx: KeywordV3Context,
    prepared: PreparedList | None = None,
    ladder_inputs: LadderInputs | None = None,
) -> dict[AggressionTargetMode, ModeCandidate]:
    """M/O/C state candidates; delegates to ``state_candidates_by_mode_for_ctx`` when ladder set."""
    if ladder_inputs is not None:
        from app.modules.shop_runner.service_manager.services.auto_updater_v3.keyword_v3_ladder_view import (
            state_candidates_by_mode_for_ctx,
        )

        return state_candidates_by_mode_for_ctx(ctx, ladder_inputs)
    conv = _conv_for_ctx(ctx, prepared)
    return build_mode_candidates(
        profile=ctx.position_profile,
        keyword_text=ctx.keyword.text,
        conv_views_to_orders=conv,
        rk_orders_per_cart=None,
    )


def _conv_for_ctx(
    ctx: KeywordV3Context,
    prepared: PreparedList | None = None,
) -> float:
    """Conv для кандидатов M/O/C: своя или импутация РК."""
    peer = [c for c, _ in prepared] if prepared else [ctx]
    eff = effective_conv_for_v3(ctx, peer)
    if eff is not None:
        return eff
    return float(ctx.keyword.conv_views_to_orders)


def eligibility_for_ctx(
    ctx: KeywordV3Context,
    eligibility_by_ks_id: dict[int, KeywordV3Eligibility] | None,
    *,
    eligibility: KeywordV3Eligibility | None = None,
) -> KeywordV3Eligibility | None:
    """Eligibility ключа из явного аргумента или map по ``keyword_setting_original_id``."""
    if eligibility is not None:
        return eligibility
    if eligibility_by_ks_id is None:
        return None
    ks_id = ctx.keyword.keyword_setting_original_id
    if ks_id is None:
        return None
    return eligibility_by_ks_id.get(int(ks_id))


def resolve_effective_state_cost_for_mode(
    *,
    ctx: KeywordV3Context,
    to_mode: KeywordStrategyMode,
    prepared: PreparedList | None = None,
    eligibility_by_ks_id: dict[int, KeywordV3Eligibility] | None = None,
    eligibility: KeywordV3Eligibility | None = None,
    ladder_inputs: LadderInputs | None = None,
) -> tuple[float, bool]:
    """Единый API себестоимости target mode для ladder-фаз V3 (делегирует ``cost_for_mode``)."""
    elig = eligibility_for_ctx(
        ctx, eligibility_by_ks_id, eligibility=eligibility
    )
    return _resolve_state_cost_for_mode(
        ctx=ctx,
        to_mode=to_mode,
        prepared=prepared,
        eligibility=elig,
        ladder_inputs=ladder_inputs,
    )


def _resolve_state_cost_for_mode(
    *,
    ctx: KeywordV3Context,
    to_mode: KeywordStrategyMode,
    prepared: PreparedList | None = None,
    eligibility: KeywordV3Eligibility | None = None,
    ladder_inputs: LadderInputs | None = None,
) -> tuple[float, bool]:
    """Себестоимость режима через ``keyword_v3_ladder_view.cost_for_mode`` (SSOT)."""
    from app.modules.shop_runner.service_manager.services.auto_updater_v3.keyword_v3_ladder_view import (
        LadderInputs,
        cost_for_mode,
    )

    if ladder_inputs is None:
        if prepared is not None:
            ladder_inputs = ladder_inputs_for_prepared(prepared)
        else:
            ladder_inputs = LadderInputs.from_contexts([ctx])
    return cost_for_mode(
        ctx,
        to_mode,
        ladder_inputs=ladder_inputs,
        eligibility=eligibility,
    )


def min_cpa_bound_by_pay_for_order(
    eligibility: KeywordV3Eligibility | None,
) -> bool:
    """MIN-only + ``target_place=0``: NO CH или collapsed CH ladder + pay_for_order."""
    return (
        eligibility is not None
        and eligibility.participates_in_ladder
        and eligibility.target_place_fallback_zero
        and eligibility.allowed_modes == frozenset({KeywordStrategyMode.MIN_CPA})
    )


__all__ = [
    "HARD_STATUS_AUTO_MODE",
    "HARD_STATUS_WHITE_LIST",
    "eligibility_for_ctx",
    "hard_status_allows_up",
    "ladder_inputs_for_prepared",
    "min_cpa_bound_by_pay_for_order",
    "mode_catalog_for_ctx",
    "resolve_effective_state_cost_for_mode",
]
