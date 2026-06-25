"""Unit: merge audit в V3TickReportSnapshot."""

from __future__ import annotations

from datetime import UTC, datetime

import pytest

from app.modules.shop_runner.service_manager.services.auto_updater_v3.v3_keyword_changes_report.merge import (
    merge_keyword_changes_into_tick_snapshot,
)
from app.modules.shop_runner.service_manager.services.auto_updater_v3.v3_keyword_changes_report.models import (
    V3ExecutorPhaseBreakdown,
    V3KeywordChangesSnapshot,
)
from app.modules.shop_runner.service_manager.services.auto_updater_v3.v3_tick_report import (
    V3PhaseStats,
    V3TickReportSnapshot,
)


@pytest.mark.unit
def test_merge_replaces_counters_preserves_skip_reason() -> None:
    base = V3TickReportSnapshot(
        tick_at=datetime(2026, 6, 3, tzinfo=UTC),
        adv_id=1,
        campaign_mode="NORMAL",
        aggression_score_before=100,
        aggression_score_after=105,
        aggression_delta=5,
        net_up=10,
        net_down=2,
        net_force_off=1,
        phases=[
            V3PhaseStats(
                phase_id="max_cpa_guard",
                title_ru="G",
                executed=False,
                skip_reason="fact_le_max",
            ),
            V3PhaseStats(
                phase_id="resolve_calibration",
                title_ru="calibration",
                up=99,
                down=0,
                planned=99,
            ),
        ],
    )
    audit = V3KeywordChangesSnapshot(
        tick_at=datetime(2026, 6, 3, tzinfo=UTC),
        adv_id=1,
        net_up=20,
        net_down=18,
        net_force_off=16,
        aggression_score_after=156,
        by_phase=[
            V3ExecutorPhaseBreakdown(
                phase_id="resolve_calibration",
                executor_name="ResolveCalibrationExecutor",
                up=20,
                planned=20,
                keywords_touched=20,
            ),
            V3ExecutorPhaseBreakdown(
                phase_id="cost_reallocation",
                executor_name="RebalanceExecutor",
                down=2,
                force_off=16,
                planned=18,
                keywords_touched=18,
                ended_off=16,
                ended_on=0,
            ),
        ],
    )

    merged = merge_keyword_changes_into_tick_snapshot(base, audit)
    guard = next(p for p in merged.phases if p.phase_id == "max_cpa_guard")
    assert guard.skip_reason == "fact_le_max"
    assert guard.up == 0

    cal = next(p for p in merged.phases if p.phase_id == "resolve_calibration")
    assert cal.up == 20
    assert cal.planned == 20
    assert cal.outcome_note is None

    realloc = next(p for p in merged.phases if p.phase_id == "cost_reallocation")
    assert realloc.down == 2
    assert realloc.force_off == 16
    assert realloc.ended_off == 16
    assert realloc.ended_on == 0

    assert merged.net_up == 20
    assert merged.net_down == 18
    assert merged.net_force_off == 16
    assert merged.net_on == 0
    assert merged.aggression_score_after == 156
    assert merged.aggression_delta == 56


@pytest.mark.unit
def test_merge_appends_phase_missing_in_collector() -> None:
    base = V3TickReportSnapshot(
        tick_at=datetime(2026, 6, 3, tzinfo=UTC),
        adv_id=1,
        campaign_mode="NORMAL",
        phases=[],
    )
    audit = V3KeywordChangesSnapshot(
        tick_at=datetime(2026, 6, 3, tzinfo=UTC),
        adv_id=1,
        by_phase=[
            V3ExecutorPhaseBreakdown(
                phase_id="skip_up_same_target_place",
                executor_name="SkipUpTargetPlaceExecutor",
                down=1,
                planned=1,
            ),
        ],
    )
    merged = merge_keyword_changes_into_tick_snapshot(base, audit)
    assert len(merged.phases) == 1
    assert merged.phases[0].phase_id == "skip_up_same_target_place"
    assert merged.phases[0].down == 1


@pytest.mark.unit
def test_merge_keeps_distinct_clamp_phase_ids() -> None:
    base = V3TickReportSnapshot(
        tick_at=datetime(2026, 6, 3, tzinfo=UTC),
        adv_id=1,
        campaign_mode="NORMAL",
        phases=[
            V3PhaseStats(
                phase_id="clamp_states_to_resolve_when_no_effective_steps",
                title_ru="1b · clamp · resolve when configured steps=0",
                planned=1,
                down=1,
            ),
            V3PhaseStats(
                phase_id="final_clamp_states_to_resolve",
                title_ru="1c · clamp · final resolve safety when configured steps=0",
                planned=1,
                down=1,
            ),
        ],
    )
    audit = V3KeywordChangesSnapshot(
        tick_at=datetime(2026, 6, 3, tzinfo=UTC),
        adv_id=1,
        by_phase=[
            V3ExecutorPhaseBreakdown(
                phase_id="clamp_states_to_resolve_when_no_effective_steps",
                executor_name="ClampStatesToResolveWhenNoEffectiveStepsExecutor",
                down=1,
                planned=1,
                keywords_touched=1,
            ),
            V3ExecutorPhaseBreakdown(
                phase_id="final_clamp_states_to_resolve",
                executor_name="ClampStatesToResolveWhenNoEffectiveStepsExecutor",
                down=1,
                planned=1,
                keywords_touched=1,
            ),
        ],
    )

    merged = merge_keyword_changes_into_tick_snapshot(base, audit)
    assert {p.phase_id for p in merged.phases} == {
        "clamp_states_to_resolve_when_no_effective_steps",
        "final_clamp_states_to_resolve",
    }
    assert sum(p.down for p in merged.phases) == 2
