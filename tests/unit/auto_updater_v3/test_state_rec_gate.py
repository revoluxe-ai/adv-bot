"""Unit: state-level rec_gate (к→з vs rec_orders_per_view)."""

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
    ModeCandidate,
    V3ActionType,
)
from app.modules.shop_runner.service_manager.services.auto_updater_v3.keyword_v3_ladder_view import (
    LadderInputs,
)
from app.modules.shop_runner.service_manager.services.auto_updater_v3.rollout_planner import (
    plan_profitable_expansion,
)
from app.modules.shop_runner.service_manager.services.auto_updater_v3.selector import (
    KeywordV3Context,
)
from unittest.mock import patch

from app.modules.shop_runner.service_manager.services.auto_updater_v3.state_rec_gate import (
    REC_GATE_MARK_PASS,
    REC_GATE_MARK_UNKNOWN_BASELINE,
    passes_rec_gate_for_target_state,
    resolve_rec_gate_mark,
    state_passes_rec_gate_for_mode,
)
from app.modules.shop_runner.service_manager.services.auto_updater_v3.transition_ranking import (
    SelectionPolicy,
    build_prepared_from_contexts,
    plan_shelf_rec_false_cleanup_down,
)
from app.modules.wb_adv_updater.calculated_keywords_manager.dto.position_profile_point import (
    PositionProfilePoint,
)
from tests.unit.test_auto_updater_v3 import _calc_kw

TS = datetime(2024, 1, 1, tzinfo=UTC)
RK = 0.26
REC = 0.005


def _policy_shelf() -> SelectionPolicy:
    return SelectionPolicy.from_aggressiveness(
        click_mode=ShelfClickMode.SHELF_DOMINANT_OR_EQUAL,
        aggressiveness=3,
    )


def _mc(*, conv_cart: float, opv: float | None = None) -> ModeCandidate:
    opv_val = opv if opv is not None else conv_cart * RK
    return ModeCandidate(
        mode=AggressionTargetMode.MIN_CPA,
        predicted_conversion=conv_cart,
        predicted_orders_per_view=opv_val,
        is_valid=True,
    )


@pytest.mark.unit
def test_gate_pass_when_rec_none() -> None:
    mc = _mc(conv_cart=0.01)
    assert passes_rec_gate_for_target_state(
        mc,
        target_mode=KeywordStrategyMode.MIN_CPA,
        policy=_policy_shelf(),
        rec_orders_per_view=None,
        rk_orders_per_cart=RK,
    )
    assert (
        resolve_rec_gate_mark(
            mc,
            policy=_policy_shelf(),
            rec_orders_per_view=None,
            rk_orders_per_cart=RK,
        )
        == REC_GATE_MARK_UNKNOWN_BASELINE
    )


@pytest.mark.unit
def test_gate_fail_when_rk_missing_but_baseline_known() -> None:
    mc = _mc(conv_cart=0.02, opv=None)
    mc = mc.model_copy(update={"predicted_orders_per_view": None})
    assert not passes_rec_gate_for_target_state(
        mc,
        target_mode=KeywordStrategyMode.MIN_CPA,
        policy=_policy_shelf(),
        rec_orders_per_view=REC,
        rk_orders_per_cart=None,
    )


@pytest.mark.unit
def test_gate_strictly_greater_than_baseline() -> None:
    above = _mc(conv_cart=0.03, opv=REC + 0.001)
    below = _mc(conv_cart=0.01, opv=REC - 0.001)
    pol = _policy_shelf()
    assert passes_rec_gate_for_target_state(
        above,
        target_mode=KeywordStrategyMode.MIN_CPA,
        policy=pol,
        rec_orders_per_view=REC,
        rk_orders_per_cart=RK,
    )
    assert not passes_rec_gate_for_target_state(
        below,
        target_mode=KeywordStrategyMode.MIN_CPA,
        policy=pol,
        rec_orders_per_view=REC,
        rk_orders_per_cart=RK,
    )
    assert (
        resolve_rec_gate_mark(
            above,
            policy=pol,
            rec_orders_per_view=REC,
            rk_orders_per_cart=RK,
        )
        == REC_GATE_MARK_PASS
    )


@pytest.mark.unit
def test_expansion_off_to_min_when_above_rec_false_but_m_state_passes() -> None:
    prof = [
        PositionProfilePoint(
            position=49, bid=510.0, predicted_conversion=0.02, pay_for_cart=1.0, timestamp=TS
        ),
        PositionProfilePoint(
            position=1, bid=5340.0, predicted_conversion=0.13, pay_for_cart=1.0, timestamp=TS
        ),
    ]
    kw = _calc_kw(
        ks_id=200,
        text="крем для комбинированной кожи лица",
        mode=KeywordStrategyMode.OFF,
        rating=5.0,
        conv=0.001,
        hard_status=2,
        above_rec=False,
    )
    ctx = KeywordV3Context(keyword=kw, position_profile=prof)
    prepared = build_prepared_from_contexts([ctx])
    ladder = LadderInputs.from_contexts(
        [ctx],
        rk_orders_per_cart=RK,
        rec_orders_per_view=0.004,
    )
    actions = plan_profitable_expansion(
        prepared,
        resolve=120.0,
        policy=_policy_shelf(),
        ladder_inputs=ladder,
    )
    assert len(actions) == 1
    assert actions[0].action == V3ActionType.UP
    assert actions[0].target_strategy_mode == KeywordStrategyMode.MIN_CPA


@pytest.mark.unit
def test_expansion_blocks_min_when_m_state_below_baseline() -> None:
    prof = [
        PositionProfilePoint(
            position=49, bid=510.0, predicted_conversion=0.01, pay_for_cart=1.0, timestamp=TS
        ),
    ]
    kw = _calc_kw(
        ks_id=201,
        text="kw",
        mode=KeywordStrategyMode.OFF,
        rating=1.0,
        above_rec=True,
        hard_status=2,
    )
    ctx = KeywordV3Context(keyword=kw, position_profile=prof)
    prepared = build_prepared_from_contexts([ctx])
    ladder = LadderInputs.from_contexts([ctx], rk_orders_per_cart=RK, rec_orders_per_view=0.01)
    actions = plan_profitable_expansion(
        prepared,
        resolve=400.0,
        policy=_policy_shelf(),
        ladder_inputs=ladder,
    )
    assert actions == []


@pytest.mark.unit
def test_cleanup_no_action_when_rec_none() -> None:
    prof = [
        PositionProfilePoint(
            position=1, bid=100.0, predicted_conversion=0.04, pay_for_cart=1.0, timestamp=TS
        ),
    ]
    kw = _calc_kw(
        ks_id=1,
        text="kw",
        mode=KeywordStrategyMode.OPTIMUM,
        rating=1.0,
        above_rec=False,
        hard_status=2,
    )
    ctx = KeywordV3Context(keyword=kw, position_profile=prof)
    prepared = build_prepared_from_contexts([ctx])
    ladder = LadderInputs.from_contexts([ctx], rk_orders_per_cart=RK, rec_orders_per_view=None)
    assert (
        plan_shelf_rec_false_cleanup_down(
            prepared,
            click_mode=ShelfClickMode.SHELF_DOMINANT_OR_EQUAL,
            ladder_inputs=ladder,
            policy=_policy_shelf(),
        )
        == []
    )


@pytest.mark.unit
def test_cleanup_down_to_min_not_force_off_when_min_passes() -> None:
    """OPT не проходит gate, MIN проходит → DOWN до MIN (не FORCE_OFF на авто)."""
    prof = [
        PositionProfilePoint(
            position=1, bid=5340.0, predicted_conversion=0.13, pay_for_cart=1.0, timestamp=TS
        ),
        PositionProfilePoint(
            position=49, bid=510.0, predicted_conversion=0.02, pay_for_cart=1.0, timestamp=TS
        ),
    ]
    kw = _calc_kw(
        ks_id=2,
        text="kw",
        mode=KeywordStrategyMode.OPTIMUM,
        rating=1.0,
        above_rec=False,
        hard_status=1,
    )
    ctx = KeywordV3Context(keyword=kw, position_profile=prof)
    prepared = build_prepared_from_contexts([ctx])
    ladder = LadderInputs.from_contexts([ctx], rk_orders_per_cart=RK, rec_orders_per_view=0.004)

    def _gate(
        _cats: dict,
        to_mode: KeywordStrategyMode,
        _policy: SelectionPolicy,
        *,
        rec_orders_per_view: float | None,
        rk_orders_per_cart: float | None,
    ) -> bool:
        _ = (_cats, _policy, rec_orders_per_view, rk_orders_per_cart)
        if to_mode == KeywordStrategyMode.MIN_CPA:
            return True
        if to_mode == KeywordStrategyMode.OPTIMUM:
            return False
        return True

    with patch(
        "app.modules.shop_runner.service_manager.services.auto_updater_v3.state_rec_gate.state_passes_rec_gate_for_mode",
        side_effect=_gate,
    ):
        actions = plan_shelf_rec_false_cleanup_down(
            prepared,
            click_mode=ShelfClickMode.SHELF_DOMINANT_OR_EQUAL,
            ladder_inputs=ladder,
            policy=_policy_shelf(),
        )
    assert len(actions) == 1
    assert actions[0].action == V3ActionType.DOWN
    assert actions[0].target_strategy_mode == KeywordStrategyMode.MIN_CPA


@pytest.mark.unit
def test_state_passes_for_mode_from_candidates_dict() -> None:
    cats = build_mode_candidates(
        profile=[
            PositionProfilePoint(
                position=49,
                bid=510.0,
                predicted_conversion=0.02,
                pay_for_cart=1.0,
                timestamp=TS,
            ),
        ],
        keyword_text="kw",
        rk_orders_per_cart=RK,
    )
    assert state_passes_rec_gate_for_mode(
        cats,
        KeywordStrategyMode.MIN_CPA,
        _policy_shelf(),
        rec_orders_per_view=0.004,
        rk_orders_per_cart=RK,
    )
