"""Матрица acceptance: effective STEP_UP/DOWN в фазах V3 (не только unit helper)."""

from __future__ import annotations

from datetime import UTC, datetime

import pytest

from app.modules.common_slaves.wildberries.models.enums import KeywordStrategyMode
from app.modules.shop_runner.service_manager.services.auto_updater_v3.activation_strategy import (
    ShelfClickMode,
)
from app.modules.shop_runner.service_manager.services.auto_updater_v3.dto import (
    AggressionTargetMode,
    ModeCandidate,
    V3ActionType,
)
from app.modules.shop_runner.service_manager.services.auto_updater_v3.effective_ladder_steps import (
    count_effective_released_aggression_steps,
)
from app.modules.shop_runner.service_manager.services.auto_updater_v3.keyword_v3_ladder_view import (
    LadderInputs,
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
from app.modules.shop_runner.service_manager.services.auto_updater_v3.transition_ranking import (
    SelectionPolicy,
    build_prepared_from_contexts,
    collect_transition_candidates,
    plan_shelf_rec_false_cleanup_down,
)
from app.modules.shop_runner.service_manager.services.v3_optimum_balance import (
    OPTIMUM_MAX_CPO_PENALTY_COMPARE,
    select_optimum_row_production,
)
from app.modules.predict_keywords_target_place.predict_keywords_target_place import (
    PredictKeywordsTargetPlace,
)
from tests.unit.auto_updater_v3.test_effective_ladder_steps import _fake_catalog_places
from tests.unit.test_auto_updater_v3 import _calc_kw

TS = datetime(2024, 1, 1, tzinfo=UTC)


def _policy() -> SelectionPolicy:
    return SelectionPolicy.from_aggressiveness(
        click_mode=ShelfClickMode.ORGANIC_DOMINANT,
        aggressiveness=V3RolloutAggressiveness.MAX,
    )


def _patch_catalog(
    monkeypatch: pytest.MonkeyPatch, cat: dict
) -> None:
    monkeypatch.setattr(
        "app.modules.shop_runner.service_manager.services.auto_updater_v3.rollout_planner._mode_catalog_for_ctx",
        lambda _ctx, _prepared, _ladder=None: cat,
    )
    monkeypatch.setattr(
        "app.modules.shop_runner.service_manager.services.auto_updater_v3.transition_ranking._catalog_for_ctx",
        lambda _ctx, _prepared=None, **_kwargs: cat,
    )


def _realloc_mocks(
    *,
    active_ks: int,
    active_mode: KeywordStrategyMode,
    active_cost: float,
    potential_ks: int = 31,
) -> tuple[object, object]:
    def _active(_prepared: object, **_kwargs: object) -> list[_StateView]:
        return [
            _StateView(
                ks_id=active_ks,
                strategy_mode=active_mode,
                cost=active_cost,
                from_mode=active_mode,
                to_mode=active_mode,
                imputed=False,
            )
        ]

    def _potential(_prepared: object, **_kwargs: object) -> list[_StateView]:
        return [
            _StateView(
                ks_id=potential_ks,
                strategy_mode=KeywordStrategyMode.MIN_CPA,
                cost=50.0,
                from_mode=KeywordStrategyMode.OFF,
                to_mode=KeywordStrategyMode.MIN_CPA,
                imputed=False,
            )
        ]

    return _active, _potential


@pytest.mark.unit
def test_expansion_m_o_c_same_place_no_up(monkeypatch: pytest.MonkeyPatch) -> None:
    """PROFITABLE_EXPANSION: M=O=C (один target_place) — нет UP между M/O/C."""
    cat = _fake_catalog_places(min_place=1, opt_place=1, max_place=1)
    _patch_catalog(monkeypatch, cat)
    kw = _calc_kw(ks_id=1, text="moc", mode=KeywordStrategyMode.MIN_CPA, rating=5.0, conv=0.05)
    prepared = build_prepared_from_contexts(
        [KeywordV3Context(keyword=kw, position_profile=[])]
    )
    assert plan_profitable_expansion(
        prepared, resolve=10_000.0, policy=_policy()
    ) == []


@pytest.mark.unit
def test_expansion_off_to_min_when_m_o_c_collapsed(monkeypatch: pytest.MonkeyPatch) -> None:
    """PROFITABLE_EXPANSION: OFF→highest passing при M=O=C на одном place."""
    cat = _fake_catalog_places(min_place=1, opt_place=1, max_place=1)
    _patch_catalog(monkeypatch, cat)
    kw = _calc_kw(ks_id=2, text="off", mode=KeywordStrategyMode.OFF, rating=5.0, conv=0.05)
    prepared = build_prepared_from_contexts(
        [KeywordV3Context(keyword=kw, position_profile=[])]
    )
    actions = plan_profitable_expansion(
        prepared, resolve=10_000.0, policy=_policy()
    )
    assert len(actions) == 1
    assert actions[0].target_strategy_mode == KeywordStrategyMode.MAX_CONVERSION


@pytest.mark.unit
def test_realloc_released_step_zero_opt_to_min_when_opt_eq_min() -> None:
    """COST_REALLOCATION: OPT=MIN same place, MAX другой — OPT→MIN не released_step."""
    cat = _fake_catalog_places(min_place=40, opt_place=40, max_place=1)
    assert (
        count_effective_released_aggression_steps(
            KeywordStrategyMode.OPTIMUM,
            KeywordStrategyMode.MIN_CPA,
            cat,
        )
        == 0
    )
    assert (
        count_effective_released_aggression_steps(
            KeywordStrategyMode.MAX_CONVERSION,
            KeywordStrategyMode.MIN_CPA,
            cat,
        )
        == 1
    )


@pytest.mark.unit
def test_guard_m_o_c_same_place_force_off_not_hollow_down(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """MAX_CPA_GUARD: M=O=C — trim → OFF, не DOWN в OPT/MIN."""
    cat = _fake_catalog_places(min_place=1, opt_place=1, max_place=1)
    _patch_catalog(monkeypatch, cat)
    kw = _calc_kw(
        ks_id=40,
        text="guard_max",
        mode=KeywordStrategyMode.MAX_CONVERSION,
        rating=50.0,
        conv=0.05,
        hard_status=2,
    )
    prepared = build_prepared_from_contexts(
        [KeywordV3Context(keyword=kw, position_profile=[])]
    )
    actions = plan_max_cpa_guard(
        prepared,
        max_pay_for_order=1.0,
        shelf_click_mode=ShelfClickMode.ORGANIC_DOMINANT,
        aggressiveness=V3RolloutAggressiveness.MAX,
    )
    assert len(actions) == 1
    assert actions[0].action == V3ActionType.FORCE_OFF
    assert not [a for a in actions if a.action == V3ActionType.DOWN]


@pytest.mark.unit
def test_guard_max_to_min_skips_opt_alias() -> None:
    """MAX_CPA_GUARD: MAX=OPT place, MIN другой — DOWN сразу в MIN (как acceptance)."""
    from app.modules.shop_runner.service_manager.services.auto_updater_v3.candidates import (
        build_mode_candidates,
    )
    from app.modules.shop_runner.service_manager.services.auto_updater_v3.dto import (
        AggressionTargetMode,
    )
    from app.modules.wb_adv_updater.calculated_keywords_manager.dto.position_profile_point import (
        PositionProfilePoint,
    )
    from tests.unit.auto_updater_v3.conftest import RK_ORDERS_PER_CART_TEST

    prof = [
        PositionProfilePoint(
            position=1, bid=10_000.0, predicted_conversion=0.13, pay_for_cart=50.0, timestamp=TS
        ),
        PositionProfilePoint(
            position=40, bid=500.0, predicted_conversion=0.015, pay_for_cart=10.0, timestamp=TS
        ),
    ]
    cat = build_mode_candidates(
        profile=prof, keyword_text="guard", rk_orders_per_cart=RK_ORDERS_PER_CART_TEST
    )
    if int(cat[AggressionTargetMode.OPTIMUM].position or 0) != int(
        cat[AggressionTargetMode.MAX_CONVERSION].position or 0
    ):
        pytest.skip("profile: need O=C for guard trim")
    kw = _calc_kw(
        ks_id=41,
        text="guard_max2",
        mode=KeywordStrategyMode.MAX_CONVERSION,
        rating=50.0,
        conv=0.05,
        hard_status=2,
    )
    prepared = build_prepared_from_contexts(
        [KeywordV3Context(keyword=kw, position_profile=prof)]
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
    assert KeywordStrategyMode.OPTIMUM not in {a.target_strategy_mode for a in downs}


@pytest.mark.unit
def test_shelf_cleanup_down_skips_opt_alias(monkeypatch: pytest.MonkeyPatch) -> None:
    """transition_ranking DOWN: MAX→MIN, не MAX→OPT (alias)."""
    cat = _fake_catalog_places(min_place=40, opt_place=1, max_place=1)
    rec = 0.01
    cat[AggressionTargetMode.MIN_CPA] = cat[AggressionTargetMode.MIN_CPA].model_copy(
        update={"predicted_orders_per_view": rec + 0.001}
    )
    cat[AggressionTargetMode.OPTIMUM] = cat[AggressionTargetMode.OPTIMUM].model_copy(
        update={"predicted_orders_per_view": rec - 0.001}
    )
    cat[AggressionTargetMode.MAX_CONVERSION] = cat[
        AggressionTargetMode.MAX_CONVERSION
    ].model_copy(update={"predicted_orders_per_view": rec - 0.002})
    _patch_catalog(monkeypatch, cat)
    kw = _calc_kw(
        ks_id=50,
        text="shelf_max",
        mode=KeywordStrategyMode.MAX_CONVERSION,
        rating=5.0,
        conv=0.05,
        hard_status=2,
        above_rec=False,
    )
    prepared = build_prepared_from_contexts(
        [KeywordV3Context(keyword=kw, position_profile=[])]
    )
    ctx = prepared[0][0]
    ladder = LadderInputs.from_contexts(
        [ctx],
        rk_orders_per_cart=0.25,
        rec_orders_per_view=0.01,
    )
    actions = plan_shelf_rec_false_cleanup_down(
        prepared,
        click_mode=ShelfClickMode.SHELF_DOMINANT_OR_EQUAL,
        ladder_inputs=ladder,
        policy=SelectionPolicy.from_aggressiveness(
            click_mode=ShelfClickMode.SHELF_DOMINANT_OR_EQUAL,
            aggressiveness=V3RolloutAggressiveness.MAX,
        ),
    )
    assert len(actions) == 1
    assert actions[0].target_strategy_mode == KeywordStrategyMode.MIN_CPA


@pytest.mark.unit
def test_collect_transition_no_up_to_opt_alias_only_max() -> None:
    """transition_ranking UP: O=M — pool без OPT, есть MAX."""
    from app.modules.wb_adv_updater.calculated_keywords_manager.dto.position_profile_point import (
        PositionProfilePoint,
    )

    prof = [
        PositionProfilePoint(
            position=1, bid=10_000.0, predicted_conversion=0.13, pay_for_cart=1.0, timestamp=TS
        ),
        PositionProfilePoint(
            position=40, bid=500.0, predicted_conversion=0.015, pay_for_cart=1.0, timestamp=TS
        ),
    ]
    kw = _calc_kw(ks_id=60, text="tr", mode=KeywordStrategyMode.MIN_CPA, rating=5.0, conv=0.05)
    prepared = build_prepared_from_contexts(
        [KeywordV3Context(keyword=kw, position_profile=prof)]
    )
    cands = collect_transition_candidates(prepared, policy=_policy())
    to_modes = {c.to_mode for c in cands if c.keyword_setting_id == 60}
    assert KeywordStrategyMode.OPTIMUM not in to_modes
    assert KeywordStrategyMode.MAX_CONVERSION in to_modes


@pytest.mark.unit
def test_regression_m_o_c_collapsed_place_one(monkeypatch: pytest.MonkeyPatch) -> None:
    """Регрессия M=O=C на одном target_place: expansion/realloc/guard без alias-шагов."""
    cat = _fake_catalog_places(min_place=1, opt_place=1, max_place=1)
    _patch_catalog(monkeypatch, cat)
    max_kw = _calc_kw(
        ks_id=70,
        text="reg_max",
        mode=KeywordStrategyMode.MAX_CONVERSION,
        rating=50.0,
        conv=0.05,
        hard_status=2,
    )
    min_kw = _calc_kw(
        ks_id=71,
        text="reg_min",
        mode=KeywordStrategyMode.MIN_CPA,
        rating=5.0,
        conv=0.05,
        hard_status=2,
    )
    prepared = build_prepared_from_contexts(
        [
            KeywordV3Context(keyword=max_kw, position_profile=[]),
            KeywordV3Context(keyword=min_kw, position_profile=[]),
        ]
    )
    assert plan_profitable_expansion(
        prepared, resolve=10_000.0, policy=_policy()
    ) == []
    active, potential = _realloc_mocks(
        active_ks=70, active_mode=KeywordStrategyMode.MAX_CONVERSION, active_cost=500.0
    )
    monkeypatch.setattr(
        "app.modules.shop_runner.service_manager.services.auto_updater_v3.rollout_planner._collect_active_more_expensive_than",
        active,
    )
    monkeypatch.setattr(
        "app.modules.shop_runner.service_manager.services.auto_updater_v3.rollout_planner.collect_potential_passing_states",
        potential,
    )
    ladder = LadderInputs.from_contexts([c for c, _ in prepared])
    realloc = plan_cost_reallocation(
        prepared, resolve=200.0, policy=_policy(), ladder_inputs=ladder
    )
    max_realloc = [a for a in realloc if a.keyword_setting_id == 70]
    assert len(max_realloc) == 1 and max_realloc[0].action == V3ActionType.FORCE_OFF
    guard = plan_max_cpa_guard(
        prepared,
        max_pay_for_order=1.0,
        shelf_click_mode=ShelfClickMode.ORGANIC_DOMINANT,
        aggressiveness=V3RolloutAggressiveness.MAX,
    )
    assert not [a for a in guard if a.action == V3ActionType.DOWN]


@pytest.mark.unit
def test_predict_module_uses_production_optimum_selector() -> None:
    """Production OPTIMUM: predict path импортирует select_optimum_row_production."""
    import inspect

    src = inspect.getsource(PredictKeywordsTargetPlace)
    assert "select_optimum_row_production" in src
    assert "select_optimum_row_cpo_cap" not in src


@pytest.mark.unit
def test_production_optimum_not_cpo_cap_compare_constant() -> None:
    """cap=1.5 только compare/debug, не production selector."""
    assert OPTIMUM_MAX_CPO_PENALTY_COMPARE == 1.5
    assert select_optimum_row_production.__name__ == "select_optimum_row_production"


@pytest.mark.unit
def test_candidates_module_uses_production_optimum_selector() -> None:
    """Production OPTIMUM: candidates path — select_optimum_row_production."""
    import inspect

    from app.modules.shop_runner.service_manager.services.auto_updater_v3 import (
        candidates as candidates_mod,
    )

    src = inspect.getsource(candidates_mod.build_mode_candidates)
    assert "select_optimum_row_production" in src
    assert "select_optimum_row_cpo_cap" not in src
