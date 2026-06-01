"""Unit: state-level rec_gate (к→з vs rec_orders_per_view)."""

from __future__ import annotations

from datetime import UTC, datetime
from unittest.mock import patch

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
from app.modules.shop_runner.service_manager.services.auto_updater_v3.state_rec_gate import (
    REC_GATE_MARK_FAIL,
    REC_GATE_MARK_PASS,
    REC_GATE_MARK_UNKNOWN,
    RecGateStatus,
    rec_gate_allows_up,
    rec_gate_triggers_cleanup,
    resolve_rec_gate_mark,
    resolve_rec_gate_status_for_target_state,
    state_rec_gate_status_for_mode,
)
from app.modules.shop_runner.service_manager.services.auto_updater_v3.transition_ranking import (
    SelectionPolicy,
    build_prepared_from_contexts,
    collect_transition_candidates,
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
def test_gate_inactive_when_rec_none() -> None:
    mc = _mc(conv_cart=0.01)
    status = resolve_rec_gate_status_for_target_state(
        mc,
        target_mode=KeywordStrategyMode.MIN_CPA,
        policy=_policy_shelf(),
        rec_orders_per_view=None,
        rk_orders_per_cart=RK,
    )
    assert status == RecGateStatus.INACTIVE
    assert rec_gate_allows_up(status)
    assert not rec_gate_triggers_cleanup(status)
    assert (
        resolve_rec_gate_mark(
            mc,
            policy=_policy_shelf(),
            rec_orders_per_view=None,
            rk_orders_per_cart=RK,
        )
        == REC_GATE_MARK_FAIL
    )


@pytest.mark.unit
def test_gate_unknown_when_rk_missing_allows_up_mark_n() -> None:
    mc = _mc(conv_cart=0.02, opv=None)
    mc = mc.model_copy(update={"predicted_orders_per_view": None})
    pol = _policy_shelf()
    status = resolve_rec_gate_status_for_target_state(
        mc,
        target_mode=KeywordStrategyMode.MIN_CPA,
        policy=pol,
        rec_orders_per_view=REC,
        rk_orders_per_cart=None,
    )
    assert status == RecGateStatus.UNKNOWN
    assert rec_gate_allows_up(status)
    assert not rec_gate_triggers_cleanup(status)
    assert (
        resolve_rec_gate_mark(
            mc,
            policy=pol,
            rec_orders_per_view=REC,
            rk_orders_per_cart=None,
        )
        == REC_GATE_MARK_UNKNOWN
    )


@pytest.mark.unit
def test_gate_unknown_when_state_opv_missing_allows_up_no_cleanup() -> None:
    mc = ModeCandidate(
        mode=AggressionTargetMode.OPTIMUM,
        predicted_conversion=None,
        predicted_orders_per_view=None,
        is_valid=False,
    )
    pol = _policy_shelf()
    status = resolve_rec_gate_status_for_target_state(
        mc,
        target_mode=KeywordStrategyMode.OPTIMUM,
        policy=pol,
        rec_orders_per_view=REC,
        rk_orders_per_cart=RK,
    )
    assert status == RecGateStatus.UNKNOWN
    assert rec_gate_allows_up(status)
    assert not rec_gate_triggers_cleanup(status)


@pytest.mark.unit
def test_gate_pass_and_fail_strictly_greater_than_baseline() -> None:
    above = _mc(conv_cart=0.03, opv=REC + 0.001)
    below = _mc(conv_cart=0.01, opv=REC - 0.001)
    pol = _policy_shelf()
    pass_status = resolve_rec_gate_status_for_target_state(
        above,
        target_mode=KeywordStrategyMode.MIN_CPA,
        policy=pol,
        rec_orders_per_view=REC,
        rk_orders_per_cart=RK,
    )
    fail_status = resolve_rec_gate_status_for_target_state(
        below,
        target_mode=KeywordStrategyMode.MIN_CPA,
        policy=pol,
        rec_orders_per_view=REC,
        rk_orders_per_cart=RK,
    )
    assert pass_status == RecGateStatus.PASS
    assert rec_gate_allows_up(pass_status)
    assert not rec_gate_triggers_cleanup(pass_status)
    assert fail_status == RecGateStatus.FAIL
    assert not rec_gate_allows_up(fail_status)
    assert rec_gate_triggers_cleanup(fail_status)
    assert (
        resolve_rec_gate_mark(
            above,
            policy=pol,
            rec_orders_per_view=REC,
            rk_orders_per_cart=RK,
        )
        == REC_GATE_MARK_PASS
    )
    assert (
        resolve_rec_gate_mark(
            below,
            policy=pol,
            rec_orders_per_view=REC,
            rk_orders_per_cart=RK,
        )
        == REC_GATE_MARK_FAIL
    )


@pytest.mark.unit
def test_up_allowed_on_unknown_rk_via_collect_transition_candidates() -> None:
    prof = [
        PositionProfilePoint(
            position=49, bid=510.0, predicted_conversion=0.02, pay_for_cart=1.0, timestamp=TS
        ),
    ]
    kw = _calc_kw(
        ks_id=10,
        text="kw",
        mode=KeywordStrategyMode.OFF,
        rating=1.0,
        hard_status=2,
    )
    ctx = KeywordV3Context(keyword=kw, position_profile=prof)
    prepared = build_prepared_from_contexts([ctx])
    ladder = LadderInputs.from_contexts(
        [ctx],
        rk_orders_per_cart=None,
        rec_orders_per_view=REC,
    )
    candidates = collect_transition_candidates(
        prepared,
        policy=_policy_shelf(),
        ladder_inputs=ladder,
    )
    assert any(c.to_mode == KeywordStrategyMode.MIN_CPA for c in candidates)


@pytest.mark.unit
def test_cleanup_skipped_on_unknown_current_state() -> None:
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
    ladder = LadderInputs.from_contexts(
        [ctx],
        rk_orders_per_cart=None,
        rec_orders_per_view=REC,
    )
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
def test_cleanup_down_on_fail_current_pass_min() -> None:
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

    def _status(
        _cats: dict,
        to_mode: KeywordStrategyMode,
        _policy: SelectionPolicy,
        **kwargs: object,
    ) -> RecGateStatus:
        _ = (_cats, _policy, kwargs)
        if to_mode == KeywordStrategyMode.MIN_CPA:
            return RecGateStatus.PASS
        if to_mode == KeywordStrategyMode.OPTIMUM:
            return RecGateStatus.FAIL
        return RecGateStatus.PASS

    with patch(
        "app.modules.shop_runner.service_manager.services.auto_updater_v3.state_rec_gate.state_rec_gate_status_for_mode",
        side_effect=_status,
    ):
        actions = plan_shelf_rec_false_cleanup_down(
            prepared,
            click_mode=ShelfClickMode.SHELF_DOMINANT_OR_EQUAL,
            ladder_inputs=ladder,
            policy=_policy_shelf(),
        )
    assert len(actions) == 1
    assert actions[0].action == V3ActionType.FORCE_OFF
    assert actions[0].reason == "shelf_rec_false_cleanup"


@pytest.mark.unit
def test_mass_cleanup_impossible_when_all_unknown() -> None:
    prof = [
        PositionProfilePoint(
            position=1, bid=100.0, predicted_conversion=0.04, pay_for_cart=1.0, timestamp=TS
        ),
    ]
    prepared = [
        (
            KeywordV3Context(
                keyword=_calc_kw(
                    ks_id=i,
                    text=f"kw{i}",
                    mode=KeywordStrategyMode.OPTIMUM,
                    rating=1.0,
                    hard_status=2,
                ),
                position_profile=prof,
            ),
            KeywordStrategyMode.OPTIMUM,
        )
        for i in (1, 2, 3)
    ]
    ladder = LadderInputs.from_contexts(
        [c for c, _ in prepared],
        rk_orders_per_cart=None,
        rec_orders_per_view=REC,
    )
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
def test_expansion_off_to_min_when_m_state_passes() -> None:
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
    assert actions[0].target_strategy_mode in (
        KeywordStrategyMode.OPTIMUM,
        KeywordStrategyMode.MAX_CONVERSION,
    )


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
def test_state_status_for_mode_from_candidates_dict() -> None:
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
    status = state_rec_gate_status_for_mode(
        cats,
        KeywordStrategyMode.MIN_CPA,
        _policy_shelf(),
        rec_orders_per_view=0.004,
        rk_orders_per_cart=RK,
    )
    assert status == RecGateStatus.PASS
    assert rec_gate_allows_up(status)


def _same_place_catalog() -> dict[AggressionTargetMode, ModeCandidate]:
    from tests.unit.auto_updater_v3.test_effective_ladder_steps import _fake_catalog_places

    return _fake_catalog_places(min_place=1, opt_place=1, max_place=1)


def _patch_same_place_catalog(monkeypatch: pytest.MonkeyPatch, cat: dict) -> None:
    monkeypatch.setattr(
        "app.modules.shop_runner.service_manager.services.auto_updater_v3.rollout_planner._mode_catalog_for_ctx",
        lambda _ctx, _prepared, _ladder=None: cat,
    )


@pytest.mark.unit
def test_expansion_off_picks_highest_passing_in_same_place_alias_group(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """OFF, M/O/C same place: MIN FAIL, OPT+MAX PASS → UP на MAX."""
    cat = _same_place_catalog()
    _patch_same_place_catalog(monkeypatch, cat)

    def _status(
        _cats: dict,
        to_mode: KeywordStrategyMode,
        _policy: SelectionPolicy,
        **kwargs: object,
    ) -> RecGateStatus:
        _ = (_cats, _policy, kwargs)
        if to_mode == KeywordStrategyMode.MIN_CPA:
            return RecGateStatus.FAIL
        if to_mode in (
            KeywordStrategyMode.OPTIMUM,
            KeywordStrategyMode.MAX_CONVERSION,
        ):
            return RecGateStatus.PASS
        return RecGateStatus.FAIL

    monkeypatch.setattr(
        "app.modules.shop_runner.service_manager.services.auto_updater_v3.rollout_planner.state_rec_gate_status_for_mode",
        _status,
    )

    def _fixed_cost(
        *,
        to_mode: KeywordStrategyMode,
        **kwargs: object,
    ) -> tuple[float, bool]:
        _ = (kwargs, to_mode)
        return 100.0, False

    monkeypatch.setattr(
        "app.modules.shop_runner.service_manager.services.auto_updater_v3.rollout_planner.resolve_effective_state_cost_for_mode",
        _fixed_cost,
    )

    kw = _calc_kw(
        ks_id=301,
        text="off_same_place",
        mode=KeywordStrategyMode.OFF,
        rating=1.0,
        hard_status=2,
    )
    ctx = KeywordV3Context(keyword=kw, position_profile=[])
    prepared = build_prepared_from_contexts([ctx])
    ladder = LadderInputs.from_contexts([ctx], rk_orders_per_cart=RK, rec_orders_per_view=REC)
    actions = plan_profitable_expansion(
        prepared,
        resolve=500.0,
        policy=_policy_shelf(),
        ladder_inputs=ladder,
    )
    assert len(actions) == 1
    assert actions[0].action == V3ActionType.UP
    assert actions[0].target_strategy_mode == KeywordStrategyMode.MAX_CONVERSION


@pytest.mark.unit
def test_expansion_off_no_up_when_entire_alias_group_fails(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """OFF, same place: все modes FAIL → UP не создаётся."""
    cat = _same_place_catalog()
    _patch_same_place_catalog(monkeypatch, cat)

    def _all_fail(
        _cats: dict,
        _to_mode: KeywordStrategyMode,
        _policy: SelectionPolicy,
        **kwargs: object,
    ) -> RecGateStatus:
        _ = (_cats, _to_mode, _policy, kwargs)
        return RecGateStatus.FAIL

    monkeypatch.setattr(
        "app.modules.shop_runner.service_manager.services.auto_updater_v3.rollout_planner.state_rec_gate_status_for_mode",
        _all_fail,
    )

    kw = _calc_kw(
        ks_id=302,
        text="off_all_fail",
        mode=KeywordStrategyMode.OFF,
        rating=1.0,
        hard_status=2,
    )
    ctx = KeywordV3Context(keyword=kw, position_profile=[])
    prepared = build_prepared_from_contexts([ctx])
    ladder = LadderInputs.from_contexts([ctx], rk_orders_per_cart=RK, rec_orders_per_view=REC)
    actions = plan_profitable_expansion(
        prepared,
        resolve=500.0,
        policy=_policy_shelf(),
        ladder_inputs=ladder,
    )
    assert actions == []
