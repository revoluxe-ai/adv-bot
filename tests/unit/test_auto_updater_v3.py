"""Unit tests for AutoUpdater v3 ladder, selector, and keyword JSON roundtrip."""

import json
from datetime import UTC, datetime

import pytest

from app.modules.common_slaves.wildberries.models.enums import KeywordStrategyMode
from app.modules.common_slaves.wildberries.models.fact_methods_enum import (
    FactMethods,
)
from app.modules.shop_runner.service_manager.old_modules.setting_auto_updater.data_classes import (
    FactData,
    PlanData,
)
from app.modules.shop_runner.service_manager.old_modules.setting_auto_updater_v2.adv_control_system.sales_state.sales_states import (
    SalesStates,
)
from app.modules.shop_runner.service_manager.services.auto_updater_v3.activation_strategy import (
    ActivationStrategy,
    ShelfClickMode,
    activation_strategy_for_shelf_underperform,
    resolve_shelf_click_mode,
)
from app.modules.shop_runner.service_manager.services.auto_updater_v3.dto import (
    V3ActionType,
)
from app.modules.shop_runner.service_manager.services.auto_updater_v3.ladder import (
    step_down,
    step_up,
)
from app.modules.shop_runner.service_manager.services.auto_updater_v3.rollout_aggressiveness import (
    V3RolloutAggressiveness,
    normalize_v3_rollout_aggressiveness,
)
from app.modules.shop_runner.service_manager.services.auto_updater_v3.selector import (
    KeywordV3Context,
    select_v3_actions,
)
from app.modules.shop_runner.service_manager.wb_shop_data_manager.dto.complex_adv import (
    TrafficClicksDTO,
)
from app.modules.wb_adv_updater.calculated_keywords_manager.dto.calculated_keyword import (
    CalculatedKeyword,
)
from app.modules.wb_adv_updater.calculated_keywords_manager.dto.inner_dto.keyword_state import (
    KeywordState,
)
from app.modules.wb_adv_updater.calculated_keywords_manager.dto.position_profile_point import (
    PositionProfilePoint,
)
from app.modules.wb_adv_updater.calculated_keywords_manager.dto.states import (
    KeywordStatus,
    KeywordStatusReason,
)
from app.modules.wb_adv_updater.calculated_keywords_manager.keyword_setting_dto import (
    KeywordSettingDTO,
)
from app.modules.wb_adv_updater.calculated_keywords_manager.dto.inner_dto.keyword_cpm_sources import (
    KeywordCpmSources,
)
from app.modules.wb_adv_updater.calculated_keywords_manager.keyword_stat import (
    make_zero_keyword_stat,
)


def _sample_profile() -> list[PositionProfilePoint]:
    return [
        PositionProfilePoint(
            position=1,
            bid=100,
            predicted_conversion=0.01,
            pay_for_cart=40.0,
            timestamp=datetime(2024, 1, 1, tzinfo=UTC),
        ),
        PositionProfilePoint(
            position=2,
            bid=80,
            predicted_conversion=0.02,
            pay_for_cart=25.0,
            timestamp=datetime(2024, 1, 1, tzinfo=UTC),
        ),
    ]


def _conv_for_pay_for_order(target_pfo: float, *, cpm: int = 200) -> float:
    """Подобрать conv при фиксированном CPM, чтобы pay_for_order ≈ target_pfo."""
    return cpm * 1000.0 / (target_pfo * 1_000_000.0)


def _calc_kw(
    *,
    ks_id: int,
    text: str,
    mode: KeywordStrategyMode,
    rating: float,
    views: int = 50,
    conv: float = 0.05,
    hard_status: int = 2,
    status: KeywordStatus = KeywordStatus.GOOD,
    reason: KeywordStatusReason = KeywordStatusReason.WHITE_LIST,
    above_rec: bool | None = True,
    cpm_set_bid: int = 200,
) -> CalculatedKeyword:
    stat = make_zero_keyword_stat(text).model_copy(
        update={"views": views, "clicks": 10, "orders": 2, "conv_views_to_orders": conv}
    )
    return CalculatedKeyword(
        adv_id=1,
        keyword_setting=KeywordSettingDTO(
            text=text,
            relevant=True,
            hard_status=hard_status,
            id=ks_id,
            strategy_mode=mode,
        ),
        cluster_stat=stat,
        state=KeywordState(
            status=status,
            reason=reason,
            best_keyword_status=True,
        ),
        rating=rating,
        target_pay_for_order=None,
        above_rec_conversion=above_rec,
        cpm_sources=KeywordCpmSources(cpm_set_bid=cpm_set_bid),
    )


@pytest.mark.unit
def test_normalize_v3_rollout_aggressiveness_clamps() -> None:
    assert normalize_v3_rollout_aggressiveness(None) == V3RolloutAggressiveness.MAX
    assert normalize_v3_rollout_aggressiveness(0) == V3RolloutAggressiveness.MIN
    assert normalize_v3_rollout_aggressiveness(2) == V3RolloutAggressiveness.MID
    assert normalize_v3_rollout_aggressiveness(99) == V3RolloutAggressiveness.MAX


@pytest.mark.unit
def test_ladder_step_up_down() -> None:
    assert step_up(KeywordStrategyMode.OFF) == KeywordStrategyMode.MIN_CPA
    assert step_up(KeywordStrategyMode.MAX_CONVERSION) is None
    assert step_down(KeywordStrategyMode.OFF) is None
    assert step_down(KeywordStrategyMode.MIN_CPA) == KeywordStrategyMode.OFF


@pytest.mark.unit
def test_select_optimal_state_returns_nothing() -> None:
    ctx = KeywordV3Context(
        keyword=_calc_kw(ks_id=1, text="a", mode=KeywordStrategyMode.MIN_CPA, rating=1.0),
        position_profile=_sample_profile(),
    )
    actions = select_v3_actions(
        state=SalesStates.OPTIMAL,
        contexts=[ctx],
        shelf_promotion_active=False,
    )
    assert len(actions) == 1
    assert actions[0].action == V3ActionType.DO_NOTHING


@pytest.mark.unit
def test_select_overspend_single_down_most_expensive_first() -> None:
    high = _calc_kw(
        ks_id=1, text="bad", mode=KeywordStrategyMode.MAX_CONVERSION, rating=1.0, conv=0.001
    )
    low = _calc_kw(
        ks_id=2, text="good", mode=KeywordStrategyMode.OPTIMUM, rating=10.0, conv=0.08
    )
    prof = _sample_profile()
    actions = select_v3_actions(
        state=SalesStates.OVERSPEND,
        contexts=[
            KeywordV3Context(keyword=high, position_profile=prof),
            KeywordV3Context(keyword=low, position_profile=prof),
        ],
        shelf_promotion_active=False,
        plan_max_pay_for_order=10_000.0,
    )
    assert len(actions) == 1
    assert actions[0].action == V3ActionType.DOWN
    assert actions[0].keyword_setting_id == 1


@pytest.mark.unit
def test_select_overspend_force_off_all_keys_above_max() -> None:
    prof = _sample_profile()
    over_a = _calc_kw(
        ks_id=1,
        text="a",
        mode=KeywordStrategyMode.MAX_CONVERSION,
        rating=1.0,
        conv=_conv_for_pay_for_order(150.0),
    )
    over_b = _calc_kw(
        ks_id=2,
        text="b",
        mode=KeywordStrategyMode.OPTIMUM,
        rating=1.0,
        conv=_conv_for_pay_for_order(120.0),
    )
    under = _calc_kw(
        ks_id=3,
        text="c",
        mode=KeywordStrategyMode.MIN_CPA,
        rating=1.0,
        conv=_conv_for_pay_for_order(50.0),
    )
    actions = select_v3_actions(
        state=SalesStates.OVERSPEND,
        contexts=[
            KeywordV3Context(keyword=over_a, position_profile=prof),
            KeywordV3Context(keyword=over_b, position_profile=prof),
            KeywordV3Context(keyword=under, position_profile=prof),
        ],
        shelf_promotion_active=False,
        plan_max_pay_for_order=100.0,
    )
    assert len(actions) == 2
    assert all(a.action == V3ActionType.FORCE_OFF for a in actions)
    assert {a.keyword_setting_id for a in actions} == {1, 2}
    assert all(a.reason == "overspend_max_pfo" for a in actions)


@pytest.mark.unit
def test_select_overspend_with_plan_fact_uses_m2_m3_not_legacy_off() -> None:
    """С plan/fact OVERSPEND в selector — только M2/M3 (trim/M1 в orchestrator)."""
    prof = _sample_profile()
    over = _calc_kw(
        ks_id=1,
        text="over",
        mode=KeywordStrategyMode.MAX_CONVERSION,
        rating=1.0,
        conv=_conv_for_pay_for_order(150.0),
    )
    plan = PlanData(orders=10, target_pay_for_order=80, max_pay_for_order=100)
    fact = FactData(
        predict_orders=5.0,
        original_orders=5.0,
        pay_for_order=120.0,
        fact_method=FactMethods.DIRECT_SALES,
    )
    actions = select_v3_actions(
        state=SalesStates.OVERSPEND,
        contexts=[KeywordV3Context(keyword=over, position_profile=prof)],
        shelf_promotion_active=False,
        plan_max_pay_for_order=float(plan.max_pay_for_order),
        plan=plan,
        fact=fact,
    )
    assert not any(a.reason == "overspend_max_pfo" for a in actions)
    assert not any(a.reason.startswith("m1_") for a in actions)


@pytest.mark.unit
def test_select_overspend_skips_none_pay_for_order() -> None:
    prof = _sample_profile()
    no_pfo = _calc_kw(
        ks_id=1,
        text="no_pfo",
        mode=KeywordStrategyMode.MAX_CONVERSION,
        rating=1.0,
        conv=0.0,
    )
    assert no_pfo.pay_for_order is None
    over = _calc_kw(
        ks_id=2,
        text="over",
        mode=KeywordStrategyMode.OPTIMUM,
        rating=1.0,
        conv=_conv_for_pay_for_order(200.0),
    )
    actions = select_v3_actions(
        state=SalesStates.OVERSPEND,
        contexts=[
            KeywordV3Context(keyword=no_pfo, position_profile=prof),
            KeywordV3Context(keyword=over, position_profile=prof),
        ],
        shelf_promotion_active=False,
        plan_max_pay_for_order=100.0,
    )
    assert len(actions) == 1
    assert actions[0].action == V3ActionType.FORCE_OFF
    assert actions[0].keyword_setting_id == 2


@pytest.mark.unit
def test_select_overspend_shelf_force_off_above_max() -> None:
    prof = _sample_profile()
    over = _calc_kw(
        ks_id=1,
        text="over",
        mode=KeywordStrategyMode.MAX_CONVERSION,
        rating=1.0,
        conv=_conv_for_pay_for_order(180.0),
    )
    actions = select_v3_actions(
        state=SalesStates.OVERSPEND,
        contexts=[KeywordV3Context(keyword=over, position_profile=prof)],
        shelf_promotion_active=True,
        shelf_click_mode=ShelfClickMode.SHELF_DOMINANT_OR_EQUAL,
        plan_max_pay_for_order=100.0,
    )
    assert len(actions) == 1
    assert actions[0].action == V3ActionType.FORCE_OFF


@pytest.mark.unit
def test_rollout_underperform_level1_picks_cheapest_min_cost_tie_break_pfo() -> None:
    """Одинаковый state_cost → tie-break по меньшему pay_for_order (не по ks_id)."""
    prof = _sample_profile()
    low_c = KeywordV3Context(
        keyword=_calc_kw(
            ks_id=1,
            text="a",
            mode=KeywordStrategyMode.OFF,
            rating=1.0,
            conv=0.02,
            hard_status=1,
        ),
        position_profile=prof,
    )
    high_c = KeywordV3Context(
        keyword=_calc_kw(
            ks_id=2,
            text="b",
            mode=KeywordStrategyMode.OFF,
            rating=1.0,
            conv=0.09,
            hard_status=1,
        ),
        position_profile=prof,
    )
    actions = select_v3_actions(
        state=SalesStates.UNDERPERFORM,
        contexts=[low_c, high_c],
        shelf_promotion_active=False,
        rollout_aggressiveness=1,
    )
    assert len(actions) == 1
    assert actions[0].action == V3ActionType.UP
    assert actions[0].keyword_setting_id == 2
    assert actions[0].target_strategy_mode == KeywordStrategyMode.MIN_CPA
    assert actions[0].selection_log is not None
    assert actions[0].selection_log.to_mode == "MIN_CPA"
    assert actions[0].reason == "up_cost_first_pooled"


@pytest.mark.unit
def test_rollout_underperform_up_skips_black_list_hard_status() -> None:
    prof = _sample_profile()
    black_list = KeywordV3Context(
        keyword=_calc_kw(
            ks_id=1,
            text="blocked",
            mode=KeywordStrategyMode.OFF,
            rating=1.0,
            conv=0.2,
            hard_status=0,
        ),
        position_profile=prof,
    )
    white_list = KeywordV3Context(
        keyword=_calc_kw(
            ks_id=2,
            text="allowed",
            mode=KeywordStrategyMode.OFF,
            rating=1.0,
            conv=0.1,
            hard_status=2,
        ),
        position_profile=prof,
    )
    actions = select_v3_actions(
        state=SalesStates.UNDERPERFORM,
        contexts=[black_list, white_list],
        shelf_promotion_active=False,
        rollout_aggressiveness=1,
    )
    assert len(actions) == 1
    assert actions[0].action == V3ActionType.UP
    assert actions[0].keyword_setting_id == 2


@pytest.mark.unit
def test_rollout_underperform_level2_can_pick_min_to_opt_when_few_off(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """MID (2): UP MIN→OPT; OFF в blacklist не конкурирует с imputed OFF→MIN."""
    from tests.unit.auto_updater_v3.test_effective_ladder_steps import _fake_catalog_places

    monkeypatch.setattr(
        "app.modules.shop_runner.service_manager.services.auto_updater_v3.transition_ranking._catalog_for_ctx",
        lambda _ctx, _prepared=None, **_kwargs: _fake_catalog_places(
            min_place=40, opt_place=1, max_place=2
        ),
    )
    cheap_opt = [
        PositionProfilePoint(
            position=1,
            bid=10_000,
            predicted_conversion=0.13,
            pay_for_cart=50.0,
            timestamp=datetime(2024, 1, 1, tzinfo=UTC),
        ),
        PositionProfilePoint(
            position=40,
            bid=500,
            predicted_conversion=0.015,
            pay_for_cart=10.0,
            timestamp=datetime(2024, 1, 1, tzinfo=UTC),
        ),
    ]
    off_ctx = KeywordV3Context(
        keyword=_calc_kw(
            ks_id=1,
            text="weak",
            mode=KeywordStrategyMode.OFF,
            rating=1.0,
            conv=0.01,
            hard_status=0,
        ),
        position_profile=None,
    )
    min_ctx = KeywordV3Context(
        keyword=_calc_kw(
            ks_id=2,
            text="strong",
            mode=KeywordStrategyMode.MIN_CPA,
            rating=1.0,
            conv=0.015,
            hard_status=1,
        ),
        position_profile=cheap_opt,
    )
    actions = select_v3_actions(
        state=SalesStates.UNDERPERFORM,
        contexts=[off_ctx, min_ctx],
        shelf_promotion_active=False,
        rollout_aggressiveness=2,
    )
    assert len(actions) == 1
    assert actions[0].action == V3ActionType.UP
    assert actions[0].keyword_setting_id == 2
    assert actions[0].target_strategy_mode == KeywordStrategyMode.OPTIMUM
    assert actions[0].reason == "up_cost_first_pooled"
    assert actions[0].selection_log is not None
    assert actions[0].selection_log.imputed is False


@pytest.mark.unit
def test_rollout_down_skips_non_white_list_hard_status() -> None:
    prof = _sample_profile()
    blocked = KeywordV3Context(
        keyword=_calc_kw(
            ks_id=1,
            text="blocked",
            mode=KeywordStrategyMode.MAX_CONVERSION,
            rating=1.0,
            conv=0.01,
            hard_status=1,
        ),
        position_profile=prof,
    )
    allowed = KeywordV3Context(
        keyword=_calc_kw(
            ks_id=2,
            text="allowed",
            mode=KeywordStrategyMode.OPTIMUM,
            rating=1.0,
            conv=0.01,
            hard_status=2,
        ),
        position_profile=prof,
    )
    actions = select_v3_actions(
        state=SalesStates.OVERSPEND,
        contexts=[blocked, allowed],
        shelf_promotion_active=False,
        plan_max_pay_for_order=10_000.0,
    )
    assert len(actions) == 1
    assert actions[0].action == V3ActionType.DOWN
    assert actions[0].keyword_setting_id == 2


@pytest.mark.unit
def test_shelf_underperform_cost_first_picks_lower_pfo() -> None:
    """Полка: cost-first по state_cost / pay_for_order, не приоритет shelf pending."""
    prof = _sample_profile()
    pending = KeywordV3Context(
        keyword=_calc_kw(
            ks_id=1,
            text="shelf",
            mode=KeywordStrategyMode.OFF,
            rating=1.0,
            conv=0.03,
            hard_status=1,
            status=KeywordStatus.BAD,
            reason=KeywordStatusReason.WHITE_LIST,
        ),
        position_profile=prof,
    )
    other = KeywordV3Context(
        keyword=_calc_kw(ks_id=2, text="other", mode=KeywordStrategyMode.OFF, rating=1.0, conv=0.9),
        position_profile=prof,
    )
    actions = select_v3_actions(
        state=SalesStates.UNDERPERFORM,
        contexts=[other, pending],
        shelf_promotion_active=True,
    )
    assert len(actions) == 1
    assert actions[0].keyword_setting_id == 2


@pytest.mark.unit
def test_resolve_shelf_click_mode_and_activation_strategy() -> None:
    assert resolve_shelf_click_mode(None) == ShelfClickMode.UNKNOWN
    assert (
        resolve_shelf_click_mode(
            TrafficClicksDTO(organic_clicks=10, shelf_clicks=5, keyword_clicks=3)
        )
        == ShelfClickMode.ORGANIC_DOMINANT
    )
    assert (
        resolve_shelf_click_mode(
            TrafficClicksDTO(organic_clicks=5, shelf_clicks=10, keyword_clicks=3)
        )
        == ShelfClickMode.SHELF_DOMINANT_OR_EQUAL
    )
    assert (
        resolve_shelf_click_mode(
            TrafficClicksDTO(organic_clicks=7, shelf_clicks=7, keyword_clicks=3)
        )
        == ShelfClickMode.SHELF_DOMINANT_OR_EQUAL
    )
    assert (
        activation_strategy_for_shelf_underperform(ShelfClickMode.ORGANIC_DOMINANT)
        == ActivationStrategy.LAYERED
    )
    assert (
        activation_strategy_for_shelf_underperform(ShelfClickMode.SHELF_DOMINANT_OR_EQUAL)
        == ActivationStrategy.PIECEWISE
    )
    assert (
        activation_strategy_for_shelf_underperform(ShelfClickMode.UNKNOWN)
        == ActivationStrategy.PIECEWISE
    )


@pytest.mark.unit
def test_shelf_underperform_organic_dominant_uses_layered_general_pool() -> None:
    """organic > shelf → послойная MIN, без shelf-only."""
    prof = _sample_profile()
    pending = KeywordV3Context(
        keyword=_calc_kw(
            ks_id=1,
            text="shelf",
            mode=KeywordStrategyMode.OFF,
            rating=1.0,
            conv=0.03,
            hard_status=1,
            status=KeywordStatus.BAD,
            reason=KeywordStatusReason.WHITE_LIST,
        ),
        position_profile=prof,
    )
    high_conv = KeywordV3Context(
        keyword=_calc_kw(
            ks_id=2,
            text="other",
            mode=KeywordStrategyMode.OFF,
            rating=1.0,
            conv=0.9,
            hard_status=2,
        ),
        position_profile=prof,
    )
    actions = select_v3_actions(
        state=SalesStates.UNDERPERFORM,
        contexts=[pending, high_conv],
        shelf_promotion_active=True,
        shelf_click_mode=ShelfClickMode.ORGANIC_DOMINANT,
    )
    assert len(actions) == 1
    assert actions[0].action == V3ActionType.UP
    assert actions[0].keyword_setting_id == 2
    assert actions[0].reason == "up_cost_first_pooled"


@pytest.mark.unit
def test_shelf_underperform_shelf_dominant_uses_aggr_target_cap() -> None:
    """shelf >= organic: pooled-рейтинг, но target фильтруется aggressiveness."""
    prof = _sample_profile()
    pending = KeywordV3Context(
        keyword=_calc_kw(
            ks_id=1,
            text="shelf",
            mode=KeywordStrategyMode.OFF,
            rating=1.0,
            conv=0.03,
            hard_status=1,
            status=KeywordStatus.BAD,
            reason=KeywordStatusReason.WHITE_LIST,
        ),
        position_profile=prof,
    )
    high_conv = KeywordV3Context(
        keyword=_calc_kw(
            ks_id=2,
            text="other",
            mode=KeywordStrategyMode.OFF,
            rating=1.0,
            conv=0.9,
            hard_status=2,
        ),
        position_profile=prof,
    )
    actions = select_v3_actions(
        state=SalesStates.UNDERPERFORM,
        contexts=[high_conv, pending],
        shelf_promotion_active=True,
        shelf_click_mode=ShelfClickMode.SHELF_DOMINANT_OR_EQUAL,
        rollout_aggressiveness=3,
    )
    assert len(actions) == 1
    assert actions[0].action == V3ActionType.UP
    assert actions[0].keyword_setting_id == 2
    assert actions[0].reason == "up_cost_first_pooled"


@pytest.mark.unit
def test_shelf_underperform_aggr1_blocks_targets_above_min() -> None:
    prof = _sample_profile()
    off_kw = KeywordV3Context(
        keyword=_calc_kw(
            ks_id=1,
            text="off",
            mode=KeywordStrategyMode.OFF,
            rating=1.0,
            conv=0.08,
            hard_status=2,
        ),
        position_profile=prof,
    )
    min_kw = KeywordV3Context(
        keyword=_calc_kw(
            ks_id=2,
            text="min",
            mode=KeywordStrategyMode.MIN_CPA,
            rating=1.0,
            conv=0.2,
            hard_status=2,
        ),
        position_profile=prof,
    )
    actions = select_v3_actions(
        state=SalesStates.UNDERPERFORM,
        contexts=[off_kw, min_kw],
        shelf_promotion_active=True,
        shelf_click_mode=ShelfClickMode.SHELF_DOMINANT_OR_EQUAL,
        rollout_aggressiveness=1,
    )
    assert len(actions) == 1
    assert actions[0].action == V3ActionType.UP
    assert actions[0].keyword_setting_id == 1
    assert actions[0].target_strategy_mode == KeywordStrategyMode.MIN_CPA


@pytest.mark.unit
def test_shelf_underperform_piecewise_non_shelf_when_shelf_exhausted() -> None:
    """shelf pending пуст → поштучная non-shelf, не MAX fallback."""
    prof = _sample_profile()
    non_shelf_low = KeywordV3Context(
        keyword=_calc_kw(
            ks_id=1,
            text="low",
            mode=KeywordStrategyMode.OFF,
            rating=1.0,
            conv=0.02,
            hard_status=2,
            status=KeywordStatus.GOOD,
        ),
        position_profile=prof,
    )
    non_shelf_high = KeywordV3Context(
        keyword=_calc_kw(
            ks_id=2,
            text="high",
            mode=KeywordStrategyMode.OFF,
            rating=1.0,
            conv=0.08,
            hard_status=2,
            status=KeywordStatus.GOOD,
        ),
        position_profile=prof,
    )
    actions = select_v3_actions(
        state=SalesStates.UNDERPERFORM,
        contexts=[non_shelf_low, non_shelf_high],
        shelf_promotion_active=True,
        shelf_click_mode=ShelfClickMode.SHELF_DOMINANT_OR_EQUAL,
        rollout_aggressiveness=3,
    )
    assert len(actions) == 1
    assert actions[0].action == V3ActionType.UP
    assert actions[0].keyword_setting_id == 2
    assert actions[0].reason == "up_cost_first_pooled"


@pytest.mark.unit
def test_shelf_underperform_unknown_click_mode_matches_shelf_dominant() -> None:
    """DTO None → поштучная как shelf >= organic."""
    prof = _sample_profile()
    pending = KeywordV3Context(
        keyword=_calc_kw(
            ks_id=1,
            text="shelf",
            mode=KeywordStrategyMode.OFF,
            rating=1.0,
            conv=0.03,
            hard_status=1,
            status=KeywordStatus.BAD,
            reason=KeywordStatusReason.WHITE_LIST,
        ),
        position_profile=prof,
    )
    other = KeywordV3Context(
        keyword=_calc_kw(
            ks_id=2,
            text="other",
            mode=KeywordStrategyMode.OFF,
            rating=1.0,
            conv=0.9,
            hard_status=2,
        ),
        position_profile=prof,
    )
    actions = select_v3_actions(
        state=SalesStates.UNDERPERFORM,
        contexts=[other, pending],
        shelf_promotion_active=True,
    )
    assert len(actions) == 1
    assert actions[0].keyword_setting_id == 2
    assert actions[0].reason == "up_cost_first_pooled"


@pytest.mark.unit
def test_shelf_underperform_piecewise_tie_break_by_keyword_setting_id() -> None:
    prof = _sample_profile()
    kw_a = KeywordV3Context(
        keyword=_calc_kw(
            ks_id=2,
            text="b",
            mode=KeywordStrategyMode.OFF,
            rating=1.0,
            conv=0.05,
            hard_status=2,
            status=KeywordStatus.GOOD,
        ),
        position_profile=prof,
    )
    kw_b = KeywordV3Context(
        keyword=_calc_kw(
            ks_id=1,
            text="a",
            mode=KeywordStrategyMode.OFF,
            rating=1.0,
            conv=0.05,
            hard_status=2,
            status=KeywordStatus.GOOD,
        ),
        position_profile=prof,
    )
    actions = select_v3_actions(
        state=SalesStates.UNDERPERFORM,
        contexts=[kw_a, kw_b],
        shelf_promotion_active=True,
        shelf_click_mode=ShelfClickMode.SHELF_DOMINANT_OR_EQUAL,
    )
    assert len(actions) == 1
    assert actions[0].keyword_setting_id == 1
    assert actions[0].reason == "up_cost_first_pooled"


@pytest.mark.unit
def test_calculated_keyword_position_profile_json_roundtrip() -> None:
    kw = _calc_kw(ks_id=1, text="x", mode=KeywordStrategyMode.MIN_CPA, rating=1.0)
    kw = kw.model_copy(update={"position_profile": _sample_profile()})
    raw = kw.model_dump_json()
    restored = CalculatedKeyword.model_validate(json.loads(raw))
    assert restored.position_profile is not None
    assert restored.position_profile[0].position == 1
    assert restored.strategy_mode == KeywordStrategyMode.MIN_CPA
