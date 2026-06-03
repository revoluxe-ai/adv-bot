"""Unit: V3 tick report model — aggression, breakdown, collector."""

from __future__ import annotations

from datetime import UTC, datetime

import pytest

from app.modules.common_slaves.wildberries.models.enums import KeywordStrategyMode
from app.modules.shop_runner.service_manager.services.auto_updater_v3.applier import (
    AppliedV3Action,
)
from app.modules.shop_runner.service_manager.services.auto_updater_v3.dto import (
    V3Action,
    V3ActionType,
)
from app.modules.shop_runner.service_manager.services.auto_updater_v3.v3_tick_report import (
    AppliedBreakdown,
    V3ActionBreakdown,
    V3TickReportCollector,
    campaign_aggression_score,
    count_hard_status_distribution,
    mode_aggression_points,
)
from tests.unit.test_auto_updater_v3 import _calc_kw


@pytest.mark.unit
def test_mode_aggression_points() -> None:
    assert mode_aggression_points(KeywordStrategyMode.OFF) == 0
    assert mode_aggression_points(KeywordStrategyMode.MIN_CPA) == 1
    assert mode_aggression_points(KeywordStrategyMode.OPTIMUM) == 2
    assert mode_aggression_points(KeywordStrategyMode.MAX_CONVERSION) == 3


@pytest.mark.unit
def test_campaign_aggression_score_sums_keywords() -> None:
    kws = [
        _calc_kw(ks_id=1, text="a", mode=KeywordStrategyMode.MIN_CPA, rating=1.0),
        _calc_kw(ks_id=2, text="b", mode=KeywordStrategyMode.OPTIMUM, rating=1.0),
        _calc_kw(ks_id=3, text="c", mode=KeywordStrategyMode.OFF, rating=1.0),
    ]
    assert campaign_aggression_score(kws) == 3


@pytest.mark.unit
def test_breakdown_v3_actions() -> None:
    actions = [
        V3Action(action=V3ActionType.UP, keyword_setting_id=1),
        V3Action(action=V3ActionType.DOWN, keyword_setting_id=2),
        V3Action(action=V3ActionType.REBALANCE_TRANSFER, keyword_setting_id=3),
    ]
    bd = V3ActionBreakdown.from_actions(actions)
    assert bd.planned == 3
    assert bd.up == 1
    assert bd.down == 1
    assert bd.rebalance == 1


@pytest.mark.unit
def test_collector_build_snapshot() -> None:
    kws = [
        _calc_kw(ks_id=1, text="a", mode=KeywordStrategyMode.MIN_CPA, rating=1.0),
    ]
    coll = V3TickReportCollector()
    coll.set_aggression_before(kws)
    coll.record_filter(total=10, operable=8)
    coll.record_phase(
        "validate_state_by_hard_status",
        [],
        extra={"hs1_touched": 2},
    )
    coll.record_phase(
        "cap_down",
        [V3Action(action=V3ActionType.DOWN, keyword_setting_id=1)],
    )
    snap = coll.build_snapshot(
        adv_id=99,
        adv_name="Test RK",
        campaign_mode="NORMAL",
        sales_state="STABLE",
        keywords=kws,
        applied=[
            AppliedV3Action(
                action=V3ActionType.DOWN,
                keyword_setting_id=1,
                keyword_text="a",
                from_mode=KeywordStrategyMode.OPTIMUM,
                to_mode=KeywordStrategyMode.MIN_CPA,
                reason="cap",
            )
        ],
        fact_cpa=85.0,
        resolve=92.0,
        tick_at=datetime(2026, 6, 3, 12, 0, 0, tzinfo=UTC),
    )
    assert snap.adv_id == 99
    assert len(snap.phases) == 3
    assert snap.net_down == 1
    assert snap.hard_status_counts


@pytest.mark.unit
def test_collector_record_phase_stores_outcome_note_on_zero_actions() -> None:
    coll = V3TickReportCollector()
    coll.record_phase(
        "resolve_calibration",
        [],
        outcome_note="нет ключей для UP: 10 operable",
        extra={"calibration_direct": "loosen", "effective_steps": 1},
    )
    snap = coll.build_snapshot(
        adv_id=1,
        adv_name="x",
        campaign_mode="NORMAL",
        sales_state=None,
        keywords=[],
        applied=[],
    )
    phase = snap.phases[0]
    assert phase.outcome_note == "нет ключей для UP: 10 operable"
    assert phase.up == 0


@pytest.mark.unit
def test_applied_breakdown() -> None:
    applied = [
        AppliedV3Action(
            action=V3ActionType.UP,
            keyword_setting_id=1,
            keyword_text="x",
            from_mode=KeywordStrategyMode.OFF,
            to_mode=KeywordStrategyMode.MIN_CPA,
            reason="x",
        ),
        AppliedV3Action(
            action=V3ActionType.FORCE_OFF,
            keyword_setting_id=2,
            keyword_text="y",
            from_mode=KeywordStrategyMode.MIN_CPA,
            to_mode=KeywordStrategyMode.OFF,
            reason="y",
        ),
    ]
    bd = AppliedBreakdown.from_applied(applied)
    assert bd.up == 1
    assert bd.force_off == 1


@pytest.mark.unit
def test_hard_status_distribution() -> None:
    kws = [
        _calc_kw(
            ks_id=1,
            text="a",
            mode=KeywordStrategyMode.MIN_CPA,
            rating=1.0,
            hard_status=1,
        ),
        _calc_kw(
            ks_id=2,
            text="b",
            mode=KeywordStrategyMode.MIN_CPA,
            rating=1.0,
            hard_status=2,
        ),
    ]
    dist = count_hard_status_distribution(kws)
    assert dist.get("Авто") == 1
    assert dist.get("Белый список") == 1
