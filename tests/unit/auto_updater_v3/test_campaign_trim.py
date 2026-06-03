"""Unit: trim по ``plan.max_pay_for_order`` (state_cost, не keyword.pay_for_order)."""

from __future__ import annotations

from datetime import UTC, datetime

import pytest

from app.modules.common_slaves.wildberries.models.enums import KeywordStrategyMode
from app.modules.shop_runner.service_manager.services.auto_updater_v3.dto import (
    AggressionTargetMode,
    ModeCandidate,
)
from app.modules.shop_runner.service_manager.services.auto_updater_v3.activation_strategy import (
    ShelfClickMode,
)
from app.modules.shop_runner.service_manager.services.auto_updater_v3.dto import (
    V3ActionType,
)
from app.modules.shop_runner.service_manager.services.auto_updater_v3.rollout_aggressiveness import (
    V3RolloutAggressiveness,
)
from app.modules.shop_runner.service_manager.services.auto_updater_v3.keyword_v3_ladder_view import (
    LadderInputs,
)
from app.modules.shop_runner.service_manager.services.auto_updater_v3.rollout_planner import (
    compute_resolve_cost_threshold,
    is_resolve_valid,
    plan_campaign_trim_by_max_state_cost,
    plan_mass_cheap_promotion,
    plan_resolve_calibration_trim,
)
from app.modules.shop_runner.service_manager.services.auto_updater_v3.transition_ranking import (
    SelectionPolicy,
    build_prepared_from_contexts,
)
from app.modules.shop_runner.service_manager.services.auto_updater_v3.selector import (
    KeywordV3Context,
)
from app.modules.wb_adv_updater.calculated_keywords_manager.dto.position_profile_point import (
    PositionProfilePoint,
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
def test_trim_no_ch_min_to_off_when_keyword_pay_for_order_above_max() -> None:
    """NO CH tier: trim по ``keyword.pay_for_order`` (как UI), не skip."""
    kw = _calc_kw(
        ks_id=20,
        text="no_ch_expensive",
        mode=KeywordStrategyMode.MIN_CPA,
        rating=1.0,
        conv=_conv_for_pay_for_order(435.0),
        hard_status=2,
    )
    assert kw.pay_for_order is not None
    assert kw.pay_for_order > 300.0
    prepared = build_prepared_from_contexts(
        [KeywordV3Context(keyword=kw, position_profile=None)]
    )
    actions = plan_campaign_trim_by_max_state_cost(
        prepared,
        max_pay_for_order=300.0,
        shelf_click_mode=ShelfClickMode.ORGANIC_DOMINANT,
        aggressiveness=V3RolloutAggressiveness.MAX,
    )
    assert len(actions) == 1
    assert actions[0].action == V3ActionType.FORCE_OFF
    assert actions[0].reason == "trim_max_state_cost"


@pytest.mark.unit
def test_resolve_calibration_trim_lowers_mode_when_state_cost_above_resolve() -> None:
    prof = _sample_profile()
    kw = _calc_kw(
        ks_id=11,
        text="expensive_cal",
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
    actions = plan_resolve_calibration_trim(
        prepared,
        resolve=30.0,
        shelf_click_mode=ShelfClickMode.ORGANIC_DOMINANT,
        aggressiveness=V3RolloutAggressiveness.MAX,
    )
    assert len(actions) >= 1
    assert all(a.reason == "resolve_calibration_trim" for a in actions)
    assert actions[0].action in (V3ActionType.DOWN, V3ActionType.FORCE_OFF)


@pytest.mark.unit
def test_resolve_calibration_trim_limited_one_step_vs_full(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """``max_effective_steps=1`` — один effective DOWN; ``99`` — до passing mode."""
    ts = datetime(2024, 1, 1, tzinfo=UTC)
    prof = [
        PositionProfilePoint(
            position=1,
            bid=10_000.0,
            predicted_conversion=0.1,
            pay_for_cart=1.0,
            timestamp=ts,
        ),
        PositionProfilePoint(
            position=5,
            bid=2_000.0,
            predicted_conversion=0.05,
            pay_for_cart=1.0,
            timestamp=ts,
        ),
        PositionProfilePoint(
            position=22,
            bid=500.0,
            predicted_conversion=0.02,
            pay_for_cart=1.0,
            timestamp=ts,
        ),
    ]

    def _mc(mode: AggressionTargetMode, place: int) -> ModeCandidate:
        return ModeCandidate(
            mode=mode,
            position=place,
            bid=float(place * 100),
            predicted_cpa=100.0,
            is_valid=True,
        )

    catalog = {
        AggressionTargetMode.MIN_CPA: _mc(AggressionTargetMode.MIN_CPA, 22),
        AggressionTargetMode.OPTIMUM: _mc(AggressionTargetMode.OPTIMUM, 5),
        AggressionTargetMode.MAX_CONVERSION: _mc(
            AggressionTargetMode.MAX_CONVERSION, 1
        ),
    }
    costs: dict[KeywordStrategyMode, tuple[float, bool]] = {
        KeywordStrategyMode.MAX_CONVERSION: (500.0, False),
        KeywordStrategyMode.OPTIMUM: (350.0, False),
        KeywordStrategyMode.MIN_CPA: (200.0, False),
    }

    monkeypatch.setattr(
        "app.modules.shop_runner.service_manager.services.auto_updater_v3.rollout_planner._mode_catalog_for_ctx",
        lambda _ctx, _prepared, _ladder=None: catalog,
    )

    def _fake_cost(
        *,
        ctx: KeywordV3Context,
        to_mode: KeywordStrategyMode,
        **_: object,
    ) -> tuple[float, bool]:
        _ = ctx
        return costs.get(to_mode, (float("inf"), False))

    monkeypatch.setattr(
        "app.modules.shop_runner.service_manager.services.auto_updater_v3.rollout_planner.resolve_effective_state_cost_for_mode",
        _fake_cost,
    )

    kw = _calc_kw(
        ks_id=13,
        text="expensive_limited",
        mode=KeywordStrategyMode.MAX_CONVERSION,
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
    resolve = 300.0
    one_step = plan_resolve_calibration_trim(
        prepared,
        resolve=resolve,
        shelf_click_mode=ShelfClickMode.ORGANIC_DOMINANT,
        aggressiveness=V3RolloutAggressiveness.MAX,
        max_effective_steps=1,
    )
    full = plan_resolve_calibration_trim(
        prepared,
        resolve=resolve,
        shelf_click_mode=ShelfClickMode.ORGANIC_DOMINANT,
        aggressiveness=V3RolloutAggressiveness.MAX,
        max_effective_steps=99,
    )
    assert one_step
    assert full
    one_target = one_step[0].target_strategy_mode
    full_target = full[0].target_strategy_mode
    assert one_target == KeywordStrategyMode.OPTIMUM
    assert full_target == KeywordStrategyMode.MIN_CPA
    from app.modules.shop_runner.service_manager.services.auto_updater_v3.ladder import (
        mode_level,
    )

    assert mode_level(full_target) < mode_level(one_target)


@pytest.mark.unit
def test_resolve_calibration_trim_no_ch_min_to_off_when_pfo_above_resolve() -> None:
    """NO CH tier: calibration trim по ``keyword.pay_for_order`` vs resolve."""
    kw = _calc_kw(
        ks_id=21,
        text="no_ch_cal",
        mode=KeywordStrategyMode.MIN_CPA,
        rating=1.0,
        conv=_conv_for_pay_for_order(435.0),
        hard_status=2,
    )
    assert kw.pay_for_order is not None
    assert kw.pay_for_order > 300.0
    prepared = build_prepared_from_contexts(
        [KeywordV3Context(keyword=kw, position_profile=None)]
    )
    actions = plan_resolve_calibration_trim(
        prepared,
        resolve=300.0,
        shelf_click_mode=ShelfClickMode.ORGANIC_DOMINANT,
        aggressiveness=V3RolloutAggressiveness.MAX,
    )
    assert len(actions) == 1
    assert actions[0].action == V3ActionType.FORCE_OFF
    assert actions[0].reason == "resolve_calibration_trim"


@pytest.mark.unit
def test_resolve_calibration_trim_skips_when_state_cost_at_or_below_resolve() -> None:
    prof = _sample_profile()
    kw = _calc_kw(
        ks_id=12,
        text="cheap_cal",
        mode=KeywordStrategyMode.MIN_CPA,
        rating=1.0,
        conv=_conv_for_pay_for_order(10.0),
        hard_status=2,
    )
    prepared = build_prepared_from_contexts(
        [KeywordV3Context(keyword=kw, position_profile=prof)]
    )
    actions = plan_resolve_calibration_trim(
        prepared,
        resolve=500.0,
        shelf_click_mode=ShelfClickMode.ORGANIC_DOMINANT,
        aggressiveness=V3RolloutAggressiveness.MAX,
    )
    assert actions == []


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
        ladder_inputs=LadderInputs.from_contexts(
            [ctx for ctx, _ in prepared]
        ),
    )
    assert len(actions) == 1
    assert actions[0].action == V3ActionType.UP
    assert actions[0].reason == "m1_mass_cheap_promotion"
    assert actions[0].target_strategy_mode is not None
