"""Unit: NO_DATA audit из AppliedV3Action."""

from __future__ import annotations

from datetime import UTC, datetime

import pytest

from app.modules.common_slaves.wildberries.models.enums import KeywordStrategyMode
from app.modules.shop_runner.service_manager.services.auto_updater_v3.applier import (
    AppliedV3Action,
)
from app.modules.shop_runner.service_manager.services.auto_updater_v3.dto import (
    V3ActionType,
)
from app.modules.shop_runner.service_manager.services.auto_updater_v3.v3_keyword_changes_report.no_data_builder import (
    build_from_applied_actions,
)


@pytest.mark.unit
def test_no_data_bootstrap_from_applied() -> None:
    applied = [
        AppliedV3Action(
            action=V3ActionType.UP,
            keyword_setting_id=1,
            keyword_text="alpha",
            from_mode=KeywordStrategyMode.OFF,
            to_mode=KeywordStrategyMode.MIN_CPA,
            reason="data_bootstrap_safe",
        ),
        AppliedV3Action(
            action=V3ActionType.UP,
            keyword_setting_id=2,
            keyword_text="beta",
            from_mode=KeywordStrategyMode.OFF,
            to_mode=KeywordStrategyMode.MIN_CPA,
            reason="data_bootstrap_safe",
        ),
    ]
    snap = build_from_applied_actions(
        applied,
        adv_id=99,
        tick_at=datetime(2026, 6, 3, tzinfo=UTC),
        keywords_aggression_modes=[
            KeywordStrategyMode.MIN_CPA,
            KeywordStrategyMode.MIN_CPA,
        ],
    )
    assert snap.source == "applied_actions"
    assert snap.net_up == 2
    assert snap.changed_keywords == 2
    assert len(snap.by_phase) == 1
    phase = snap.by_phase[0]
    assert phase.phase_id == "no_data_bootstrap"
    assert phase.up == 2
    assert phase.keywords_touched == 2
    assert snap.aggression_score_after == 2
