"""Unit: trim по ``plan.max_pay_for_order`` (state_cost, не keyword.pay_for_order)."""

from __future__ import annotations

import pytest

from app.modules.common_slaves.wildberries.models.enums import KeywordStrategyMode
from app.modules.shop_runner.service_manager.services.auto_updater_v3.activation_strategy import (
    ShelfClickMode,
)
from app.modules.shop_runner.service_manager.services.auto_updater_v3.dto import (
    V3ActionType,
)
from app.modules.shop_runner.service_manager.services.auto_updater_v3.rollout_aggressiveness import (
    V3RolloutAggressiveness,
)
from app.modules.shop_runner.service_manager.services.auto_updater_v3.rollout_planner import (
    build_worst_costs,
    compute_resolve_cost_threshold,
    is_resolve_valid,
    plan_campaign_trim_by_max_state_cost,
    plan_mass_cheap_promotion,
)
from app.modules.shop_runner.service_manager.services.auto_updater_v3.transition_ranking import (
    SelectionPolicy,
)
from app.modules.shop_runner.service_manager.services.auto_updater_v3.selector import (
    KeywordV3Context,
    build_prepared_from_contexts,
)
from tests.unit.test_auto_updater_v3 import (
    _calc_kw,
    _conv_for_pay_for_order,
    _sample_profile,
)


@pytest.mark.unit
def test_trim_lowers_mode_when_state_cost_above_max() -> None:
    prof = _sample_profile()
    kw = _calc_kw(
        ks_id=10,
        text="expensive",
        mode=KeywordStrategyMode.OPTIMUM,
        rating=1.0,
        conv=_conv_for_pay_for_order(200.0),
    )
    kw = kw.model_copy(
        update={
            "keyword_setting": kw.keyword_setting.model_copy(
                update={"hard_status": 2}
            )
        }
    )
    prepared = build_prepared_from_contexts(
        [KeywordV3Context(keyword=kw, position_profile=prof)]
    )
    actions = plan_campaign_trim_by_max_state_cost(
        prepared,
        max_pay_for_order=30.0,
        shelf_click_mode=ShelfClickMode.ORGANIC_DOMINANT,
        aggressiveness=V3RolloutAggressiveness.MAX,
    )
    assert len(actions) >= 1
    assert all(a.reason == "trim_max_state_cost" for a in actions)
    assert actions[0].action in (V3ActionType.DOWN, V3ActionType.FORCE_OFF)


@pytest.mark.unit
def test_m1_promotes_off_to_highest_passing_mode() -> None:
    from app.modules.shop_runner.service_manager.old_modules.setting_auto_updater.data_classes import (
        FactData,
        PlanData,
    )
    from app.modules.common_slaves.wildberries.models.fact_methods_enum import (
        FactMethods,
    )
    prof = _sample_profile()
    off_kw = _calc_kw(
        ks_id=17783584,
        text="крем от морщин вокруг глаз",
        mode=KeywordStrategyMode.OFF,
        rating=1.0,
        conv=_conv_for_pay_for_order(205.0),
    )
    off_kw = off_kw.model_copy(
        update={
            "keyword_setting": off_kw.keyword_setting.model_copy(
                update={"hard_status": 1}
            )
        }
    )
    plan = PlanData(orders=10, target_pay_for_order=80, max_pay_for_order=300)
    fact = FactData(
        predict_orders=5.0,
        original_orders=5.0,
        pay_for_order=350.0,
        fact_method=FactMethods.DIRECT_SALES,
    )
    prepared = build_prepared_from_contexts(
        [KeywordV3Context(keyword=off_kw, position_profile=prof)]
    )
    resolve = compute_resolve_cost_threshold(plan, fact)
    assert is_resolve_valid(plan, resolve)
    policy = SelectionPolicy.from_aggressiveness(
        click_mode=ShelfClickMode.ORGANIC_DOMINANT,
        aggressiveness=V3RolloutAggressiveness.MAX,
    )
    actions = plan_mass_cheap_promotion(
        prepared,
        resolve=resolve,
        policy=policy,
        worst_costs=build_worst_costs(prepared),
    )
    assert len(actions) == 1
    assert actions[0].action == V3ActionType.UP
    assert actions[0].reason == "m1_mass_cheap_promotion"
    assert actions[0].target_strategy_mode is not None
