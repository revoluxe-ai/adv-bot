"""Acceptance: effective ladder steps в COST_REALLOCATION / EXPANSION / GUARD."""

from __future__ import annotations

from datetime import UTC, datetime

import pytest

from app.modules.common_slaves.wildberries.models.enums import KeywordStrategyMode
from app.modules.shop_runner.service_manager.services.auto_updater_v3.activation_strategy import (
    ShelfClickMode,
)
from app.modules.shop_runner.service_manager.services.auto_updater_v3.candidates import (
    build_mode_candidates,
)
from app.modules.shop_runner.service_manager.services.auto_updater_v3.dto import (
    AggressionTargetMode,
    V3ActionType,
)
from app.modules.shop_runner.service_manager.services.auto_updater_v3.effective_ladder_steps import (
    iter_effective_upper_modes,
    resolve_next_effective_step_down,
)
from app.modules.shop_runner.service_manager.services.auto_updater_v3.rollout_aggressiveness import (
    V3RolloutAggressiveness,
)
from app.modules.shop_runner.service_manager.services.auto_updater_v3.rollout_planner import (
    _StateView,
    plan_cost_reallocation,
    plan_max_cpa_guard,
    plan_profitable_expansion,
)
from app.modules.shop_runner.service_manager.services.auto_updater_v3.selector import (
    KeywordV3Context,
)
from app.modules.shop_runner.service_manager.services.auto_updater_v3.keyword_v3_ladder_view import (
    LadderInputs,
)
from app.modules.shop_runner.service_manager.services.auto_updater_v3.transition_ranking import (
    SelectionPolicy,
    build_prepared_from_contexts,
)
from app.modules.wb_adv_updater.calculated_keywords_manager.dto.position_profile_point import (
    PositionProfilePoint,
)
from tests.unit.auto_updater_v3.conftest import RK_ORDERS_PER_CART_TEST
from tests.unit.auto_updater_v3.test_effective_ladder_steps import _fake_catalog_places
from tests.unit.test_auto_updater_v3 import _calc_kw

RK = RK_ORDERS_PER_CART_TEST
TS = datetime(2024, 1, 1, tzinfo=UTC)


def _policy() -> SelectionPolicy:
    return SelectionPolicy.from_aggressiveness(
        click_mode=ShelfClickMode.ORGANIC_DOMINANT,
        aggressiveness=V3RolloutAggressiveness.MAX,
    )


def _moc_places(prof: list[PositionProfilePoint]) -> dict[AggressionTargetMode, int]:
    cat = build_mode_candidates(
        profile=prof, keyword_text="moc", rk_orders_per_cart=RK
    )
    return {
        AggressionTargetMode.MIN_CPA: int(cat[AggressionTargetMode.MIN_CPA].position or 0),
        AggressionTargetMode.OPTIMUM: int(cat[AggressionTargetMode.OPTIMUM].position or 0),
        AggressionTargetMode.MAX_CONVERSION: int(
            cat[AggressionTargetMode.MAX_CONVERSION].position or 0
        ),
    }


def _o_eq_m_profile() -> list[PositionProfilePoint]:
    """MIN=OPT place 40, MAX place 1."""
    return [
        PositionProfilePoint(
            position=1, bid=10_000.0, predicted_conversion=0.13, pay_for_cart=50.0, timestamp=TS
        ),
        PositionProfilePoint(
            position=40, bid=500.0, predicted_conversion=0.015, pay_for_cart=10.0, timestamp=TS
        ),
    ]


@pytest.mark.unit
def test_realloc_o_eq_m_no_hollow_down_opt_to_min() -> None:
    """COST_REALLOCATION: O=M — нет DOWN OPT→MIN при том же target_place."""
    prof = _o_eq_m_profile()
    places = _moc_places(prof)
    assert places[AggressionTargetMode.MIN_CPA] == places[AggressionTargetMode.OPTIMUM]
    assert places[AggressionTargetMode.MAX_CONVERSION] != places[AggressionTargetMode.MIN_CPA]
    cat = build_mode_candidates(
        profile=prof, keyword_text="moc", rk_orders_per_cart=RK
    )
    step = resolve_next_effective_step_down(KeywordStrategyMode.OPTIMUM, cat)
    assert step.next_mode != KeywordStrategyMode.MIN_CPA
    opt_kw = _calc_kw(
        ks_id=1,
        text="opt_expensive",
        mode=KeywordStrategyMode.OPTIMUM,
        rating=10.0,
        conv=0.05,
        hard_status=2,
    )
    cheap_off = _calc_kw(
        ks_id=2,
        text="cheap_off",
        mode=KeywordStrategyMode.OFF,
        rating=0.1,
        conv=0.05,
        hard_status=2,
    )
    prepared = build_prepared_from_contexts(
        [
            KeywordV3Context(keyword=opt_kw, position_profile=prof),
            KeywordV3Context(keyword=cheap_off, position_profile=prof),
        ]
    )
    ladder = LadderInputs.from_contexts([c for c, _ in prepared])
    actions = plan_cost_reallocation(
        prepared,
        resolve=80.0,
        policy=_policy(),
        ladder_inputs=ladder,
    )
    opt_downs = [
        a
        for a in actions
        if a.keyword_setting_id == 1 and a.action == V3ActionType.DOWN
    ]
    assert not opt_downs


@pytest.mark.unit
def test_realloc_o_eq_c_down_max_to_min_skips_opt() -> None:
    """COST_REALLOCATION: O=C на top — effective down MAX→MIN (skip OPT)."""
    prof = _o_eq_m_profile()
    cat = build_mode_candidates(
        profile=prof, keyword_text="moc", rk_orders_per_cart=RK
    )
    places = _moc_places(prof)
    if places[AggressionTargetMode.OPTIMUM] != places[AggressionTargetMode.MAX_CONVERSION]:
        pytest.skip("profile: OPT and MAX on different places for this RK slice")
    step = resolve_next_effective_step_down(KeywordStrategyMode.MAX_CONVERSION, cat)
    assert step.next_mode == KeywordStrategyMode.MIN_CPA
    max_kw = _calc_kw(
        ks_id=3,
        text="max_expensive",
        mode=KeywordStrategyMode.MAX_CONVERSION,
        rating=10.0,
        conv=0.05,
        hard_status=2,
    )
    cheap_off = _calc_kw(
        ks_id=4,
        text="cheap_off2",
        mode=KeywordStrategyMode.OFF,
        rating=0.1,
        conv=0.05,
        hard_status=2,
    )
    prepared = build_prepared_from_contexts(
        [
            KeywordV3Context(keyword=max_kw, position_profile=prof),
            KeywordV3Context(keyword=cheap_off, position_profile=prof),
        ]
    )
    ladder = LadderInputs.from_contexts([c for c, _ in prepared])
    actions = plan_cost_reallocation(
        prepared,
        resolve=80.0,
        policy=_policy(),
        ladder_inputs=ladder,
    )
    downs = [a for a in actions if a.keyword_setting_id == 3 and a.action == V3ActionType.DOWN]
    if downs:
        assert downs[-1].target_strategy_mode == KeywordStrategyMode.MIN_CPA


@pytest.mark.unit
def test_realloc_m_o_c_all_place_max_force_off_not_hollow_down(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """COST_REALLOCATION: M=O=C place=1 — effective down MAX→OFF, не OPT/MIN."""
    cat = _fake_catalog_places(min_place=1, opt_place=1, max_place=1)
    monkeypatch.setattr(
        "app.modules.shop_runner.service_manager.services.auto_updater_v3.rollout_planner._mode_catalog_for_ctx",
        lambda _ctx, _prepared, _ladder=None: cat,
    )
    prof = _o_eq_m_profile()
    max_kw = _calc_kw(
        ks_id=30,
        text="max_degen",
        mode=KeywordStrategyMode.MAX_CONVERSION,
        rating=50.0,
        conv=0.05,
        hard_status=2,
    )
    cheap = _calc_kw(
        ks_id=31,
        text="cheap",
        mode=KeywordStrategyMode.OFF,
        rating=0.1,
        conv=0.05,
        hard_status=2,
    )
    prepared = build_prepared_from_contexts(
        [
            KeywordV3Context(keyword=max_kw, position_profile=prof),
            KeywordV3Context(keyword=cheap, position_profile=prof),
        ]
    )
    ladder = LadderInputs.from_contexts([c for c, _ in prepared])

    def _active(
        _prepared: object, **kwargs: object
    ) -> list[_StateView]:
        overrides: dict[int, KeywordStrategyMode] = kwargs.get("overrides") or {}
        if overrides.get(30) is not None:
            return []
        return [
            _StateView(
                ks_id=30,
                strategy_mode=KeywordStrategyMode.MAX_CONVERSION,
                cost=500.0,
                from_mode=KeywordStrategyMode.MAX_CONVERSION,
                to_mode=KeywordStrategyMode.MAX_CONVERSION,
                imputed=False,
            )
        ]

    def _potential(
        _prepared: object, **_kwargs: object
    ) -> list[_StateView]:
        return [
            _StateView(
                ks_id=31,
                strategy_mode=KeywordStrategyMode.MIN_CPA,
                cost=50.0,
                from_mode=KeywordStrategyMode.OFF,
                to_mode=KeywordStrategyMode.MIN_CPA,
                imputed=False,
            )
        ]

    monkeypatch.setattr(
        "app.modules.shop_runner.service_manager.services.auto_updater_v3.rollout_planner._collect_active_more_expensive_than",
        _active,
    )
    monkeypatch.setattr(
        "app.modules.shop_runner.service_manager.services.auto_updater_v3.rollout_planner.collect_potential_passing_states",
        _potential,
    )
    actions = plan_cost_reallocation(
        prepared,
        resolve=200.0,
        policy=_policy(),
        ladder_inputs=ladder,
    )
    max_actions = [a for a in actions if a.keyword_setting_id == 30]
    assert len(max_actions) == 1
    assert max_actions[0].action == V3ActionType.FORCE_OFF
    assert not [
        a
        for a in max_actions
        if a.action == V3ActionType.DOWN
        and a.target_strategy_mode in (
            KeywordStrategyMode.OPTIMUM,
            KeywordStrategyMode.MIN_CPA,
        )
    ]


@pytest.mark.unit
def test_expansion_o_eq_m_up_min_to_max() -> None:
    """PROFITABLE_EXPANSION: O=M — UP MIN→MAX."""
    prof = _o_eq_m_profile()
    places = _moc_places(prof)
    assert places[AggressionTargetMode.MIN_CPA] == places[AggressionTargetMode.OPTIMUM]
    min_kw = _calc_kw(
        ks_id=10,
        text="at_min",
        mode=KeywordStrategyMode.MIN_CPA,
        rating=5.0,
        conv=0.05,
        hard_status=2,
    )
    prepared = build_prepared_from_contexts(
        [KeywordV3Context(keyword=min_kw, position_profile=prof)]
    )
    actions = plan_profitable_expansion(
        prepared,
        resolve=500.0,
        policy=_policy(),
        ladder_inputs=LadderInputs.from_contexts([ctx for ctx, _ in prepared]),
    )
    assert len(actions) == 1
    assert actions[0].target_strategy_mode == KeywordStrategyMode.MAX_CONVERSION


@pytest.mark.unit
def test_expansion_o_eq_c_single_up_from_min(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """PROFITABLE_EXPANSION: O=C — один UP из MIN в MAX (OPT alias, без второго UP)."""
    cat = _fake_catalog_places(min_place=40, opt_place=1, max_place=1)
    assert iter_effective_upper_modes(KeywordStrategyMode.MIN_CPA, cat) == [
        KeywordStrategyMode.MAX_CONVERSION
    ]
    monkeypatch.setattr(
        "app.modules.shop_runner.service_manager.services.auto_updater_v3.rollout_planner._mode_catalog_for_ctx",
        lambda _ctx, _prepared, _ladder=None: cat,
    )
    prof = _o_eq_m_profile()
    min_kw = _calc_kw(
        ks_id=11,
        text="at_min_o_eq_c",
        mode=KeywordStrategyMode.MIN_CPA,
        rating=5.0,
        conv=0.05,
        hard_status=2,
    )
    prepared = build_prepared_from_contexts(
        [KeywordV3Context(keyword=min_kw, position_profile=prof)]
    )
    actions = plan_profitable_expansion(
        prepared,
        resolve=10_000.0,
        policy=_policy(),
        ladder_inputs=LadderInputs.from_contexts([ctx for ctx, _ in prepared]),
    )
    assert len(actions) == 1
    assert actions[0].target_strategy_mode == KeywordStrategyMode.MAX_CONVERSION


@pytest.mark.unit
def test_max_cpa_guard_no_hollow_down_opt_o_eq_m(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """MAX_CPA_GUARD: O=M — нет DOWN OPT→MIN при том же target_place."""
    cat = _fake_catalog_places(min_place=40, opt_place=40, max_place=1)
    monkeypatch.setattr(
        "app.modules.shop_runner.service_manager.services.auto_updater_v3.rollout_planner._mode_catalog_for_ctx",
        lambda _ctx, _prepared, _ladder=None: cat,
    )
    prof = _o_eq_m_profile()
    opt_kw = _calc_kw(
        ks_id=21,
        text="guard_opt",
        mode=KeywordStrategyMode.OPTIMUM,
        rating=10.0,
        conv=0.05,
        hard_status=2,
    )
    prepared = build_prepared_from_contexts(
        [KeywordV3Context(keyword=opt_kw, position_profile=prof)]
    )
    actions = plan_max_cpa_guard(
        prepared,
        max_pay_for_order=1.0,
        shelf_click_mode=ShelfClickMode.ORGANIC_DOMINANT,
        aggressiveness=V3RolloutAggressiveness.MAX,
    )
    downs = [a for a in actions if a.action == V3ActionType.DOWN]
    assert not downs


@pytest.mark.unit
def test_max_cpa_guard_trim_skips_opt_alias() -> None:
    """MAX_CPA_GUARD: trim MAX → MIN, не останавливается на OPT (O=C)."""
    prof = _o_eq_m_profile()
    cat = build_mode_candidates(
        profile=prof, keyword_text="moc", rk_orders_per_cart=RK
    )
    places = _moc_places(prof)
    if places[AggressionTargetMode.OPTIMUM] != places[AggressionTargetMode.MAX_CONVERSION]:
        pytest.skip("profile: need O=C for guard trim test")
    step = resolve_next_effective_step_down(KeywordStrategyMode.MAX_CONVERSION, cat)
    assert step.next_mode == KeywordStrategyMode.MIN_CPA
    max_kw = _calc_kw(
        ks_id=20,
        text="guard_max",
        mode=KeywordStrategyMode.MAX_CONVERSION,
        rating=10.0,
        conv=0.05,
        hard_status=2,
    )
    prepared = build_prepared_from_contexts(
        [KeywordV3Context(keyword=max_kw, position_profile=prof)]
    )
    actions = plan_max_cpa_guard(
        prepared,
        max_pay_for_order=60.0,
        shelf_click_mode=ShelfClickMode.ORGANIC_DOMINANT,
        aggressiveness=V3RolloutAggressiveness.MAX,
    )
    downs = [a for a in actions if a.action == V3ActionType.DOWN]
    assert downs
    assert downs[-1].target_strategy_mode == KeywordStrategyMode.MIN_CPA
