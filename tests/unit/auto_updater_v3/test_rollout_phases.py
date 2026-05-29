"""Unit: COST_REALLOCATION, PROFITABLE_EXPANSION, effective state cost API."""

from __future__ import annotations

import pytest

from app.modules.common_slaves.wildberries.models.enums import KeywordStrategyMode
from app.modules.shop_runner.service_manager.services.auto_updater_v3.activation_strategy import (
    ShelfClickMode,
)
from app.modules.shop_runner.service_manager.services.auto_updater_v3.dto import (
    V3ActionType,
)
from app.modules.shop_runner.service_manager.services.auto_updater_v3.keyword_v3_decision_data import (
    KeywordV3DecisionTier,
)
from app.modules.shop_runner.service_manager.services.auto_updater_v3.keyword_v3_eligibility import (
    KeywordDataTier,
    resolve_keyword_v3_eligibility,
)
from app.modules.shop_runner.service_manager.services.auto_updater_v3.rollout_aggressiveness import (
    V3RolloutAggressiveness,
)
from app.modules.shop_runner.service_manager.services.auto_updater_v3.rollout_planner import (
    collect_potential_passing_states,
    plan_cost_reallocation,
    plan_max_cpa_guard,
    plan_profitable_expansion,
    resolve_effective_state_cost_for_mode,
)
from app.modules.shop_runner.service_manager.services.auto_updater_v3.selector import (
    KeywordV3Context,
    build_prepared_from_contexts,
)
from app.modules.shop_runner.service_manager.services.auto_updater_v3.transition_ranking import (
    SelectionPolicy,
    build_worst_per_state_costs,
)
from tests.unit.test_auto_updater_v3 import (
    _calc_kw,
    _conv_for_pay_for_order,
    _sample_profile,
)


def _policy() -> SelectionPolicy:
    return SelectionPolicy.from_aggressiveness(
        click_mode=ShelfClickMode.ORGANIC_DOMINANT,
        aggressiveness=V3RolloutAggressiveness.MAX,
    )


@pytest.mark.unit
def test_plan_cost_reallocation_emits_down_only() -> None:
    """COST_REALLOCATION: только DOWN/FORCE_OFF, без UP."""
    prof = _sample_profile()
    expensive = _calc_kw(
        ks_id=1,
        text="expensive",
        mode=KeywordStrategyMode.OPTIMUM,
        rating=1.0,
        conv=_conv_for_pay_for_order(200.0),
    )
    cheap = _calc_kw(
        ks_id=2,
        text="cheap",
        mode=KeywordStrategyMode.OFF,
        rating=1.0,
        conv=_conv_for_pay_for_order(20.0),
    )
    prepared = build_prepared_from_contexts(
        [
            KeywordV3Context(keyword=expensive, position_profile=prof),
            KeywordV3Context(keyword=cheap, position_profile=prof),
        ]
    )
    worst_costs = build_worst_per_state_costs(prepared)
    actions = plan_cost_reallocation(
        prepared,
        resolve=50.0,
        policy=_policy(),
        worst_costs=worst_costs,
    )
    assert actions
    assert all(a.action in (V3ActionType.DOWN, V3ActionType.FORCE_OFF) for a in actions)
    assert all(a.reason.startswith("cost_reallocation") for a in actions)
    assert not any(a.action == V3ActionType.UP for a in actions)


@pytest.mark.unit
def test_plan_profitable_expansion_respects_max_allowed_mode() -> None:
    """Eligibility cap MIN-only: expansion не поднимает выше MIN_CPA."""
    prof = _sample_profile()
    kw = _calc_kw(
        ks_id=10,
        text="full_kw",
        mode=KeywordStrategyMode.OFF,
        rating=1.0,
        conv=_conv_for_pay_for_order(25.0),
    )
    ctx = KeywordV3Context(keyword=kw, position_profile=prof)
    prepared = build_prepared_from_contexts([ctx])
    min_only_elig = resolve_keyword_v3_eligibility(ctx, [ctx]).__class__(
        data_tier=KeywordDataTier.KEYWORD_NO_CH_PROFILE_WITH_OWN_CONV,
        allowed_modes=frozenset({KeywordStrategyMode.MIN_CPA}),
        max_allowed_mode=KeywordStrategyMode.MIN_CPA,
        participates_in_ladder=True,
        target_place_fallback_zero=True,
        imputed=False,
        fallback_kind="none",
        decision_tier=KeywordV3DecisionTier.FULL,
    )
    worst_costs = build_worst_per_state_costs(prepared)
    actions = plan_profitable_expansion(
        prepared,
        resolve=500.0,
        policy=_policy(),
        worst_costs=worst_costs,
        eligibility_by_ks_id={10: min_only_elig},
    )
    assert len(actions) == 1
    assert actions[0].action == V3ActionType.UP
    assert actions[0].target_strategy_mode == KeywordStrategyMode.MIN_CPA
    assert actions[0].reason == "profitable_expansion"


@pytest.mark.unit
def test_collect_potential_passing_states_skips_invalid() -> None:
    """INVALID tier не участвует в pooled passing states."""
    invalid_kw = _calc_kw(
        ks_id=20,
        text="invalid",
        mode=KeywordStrategyMode.OFF,
        rating=1.0,
        views=0,
        conv=0.0,
        cpm_set_bid=0,
    )
    invalid_ctx = KeywordV3Context(
        keyword=invalid_kw, position_profile=_sample_profile()
    )
    prepared = build_prepared_from_contexts([invalid_ctx])
    elig = resolve_keyword_v3_eligibility(invalid_ctx, [invalid_ctx])
    assert elig.data_tier == KeywordDataTier.KEYWORD_INVALID
    worst_costs = build_worst_per_state_costs(prepared)
    passing = collect_potential_passing_states(
        prepared,
        resolve=500.0,
        policy=_policy(),
        worst_costs=worst_costs,
        eligibility_by_ks_id={20: elig},
    )
    assert passing == []


@pytest.mark.unit
def test_resolve_effective_state_cost_for_mode_returns_finite_for_min() -> None:
    """Публичный API state_cost для MIN_CPA по CH-профилю."""
    kw = _calc_kw(
        ks_id=30,
        text="kw30",
        mode=KeywordStrategyMode.OFF,
        rating=1.0,
    )
    c = KeywordV3Context(keyword=kw, position_profile=_sample_profile())
    prepared = build_prepared_from_contexts([c])
    worst_costs = build_worst_per_state_costs(prepared)
    cost, imputed = resolve_effective_state_cost_for_mode(
        ctx=c,
        to_mode=KeywordStrategyMode.MIN_CPA,
        worst_costs=worst_costs,
        prepared=prepared,
    )
    assert cost < float("inf")
    assert isinstance(imputed, bool)


@pytest.mark.unit
def test_plan_max_cpa_guard_renames_trim_reason() -> None:
    """MAX_CPA_GUARD: trim-причины переименованы в max_cpa_guard."""
    prof = _sample_profile()
    kw = _calc_kw(
        ks_id=40,
        text="expensive",
        mode=KeywordStrategyMode.OPTIMUM,
        rating=1.0,
        conv=_conv_for_pay_for_order(200.0),
    )
    prepared = build_prepared_from_contexts(
        [KeywordV3Context(keyword=kw, position_profile=prof)]
    )
    actions = plan_max_cpa_guard(
        prepared,
        max_pay_for_order=30.0,
        shelf_click_mode=ShelfClickMode.ORGANIC_DOMINANT,
        aggressiveness=V3RolloutAggressiveness.MAX,
    )
    assert actions
    assert all(a.reason.startswith("max_cpa_guard") for a in actions)


@pytest.mark.unit
def test_invalid_eligibility_excluded_from_reallocation() -> None:
    """plan_cost_reallocation не трогает ключи с participates_in_ladder=False."""
    prof = _sample_profile()
    kw = _calc_kw(
        ks_id=50,
        text="solo",
        mode=KeywordStrategyMode.OPTIMUM,
        rating=1.0,
        conv=_conv_for_pay_for_order(200.0),
    )
    ctx = KeywordV3Context(keyword=kw, position_profile=prof)
    prepared = build_prepared_from_contexts([ctx])
    elig = resolve_keyword_v3_eligibility(ctx, [ctx])
    elig = elig.__class__(
        data_tier=KeywordDataTier.KEYWORD_INVALID,
        allowed_modes=frozenset(),
        max_allowed_mode=KeywordStrategyMode.OFF,
        participates_in_ladder=False,
        target_place_fallback_zero=False,
        imputed=False,
        fallback_kind=None,
        decision_tier=KeywordV3DecisionTier.NO_CONV,
    )
    worst_costs = build_worst_per_state_costs(prepared)
    actions = plan_cost_reallocation(
        prepared,
        resolve=5.0,
        policy=_policy(),
        worst_costs=worst_costs,
        eligibility_by_ks_id={50: elig},
    )
    assert actions == []
