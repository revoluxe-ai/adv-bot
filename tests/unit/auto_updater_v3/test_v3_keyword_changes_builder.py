"""Unit: post-hoc audit из KeywordDTO (v3_keyword_changes_report.builder)."""

from __future__ import annotations

from datetime import UTC, datetime

import pytest

from app.modules.common_slaves.wildberries.models.enums import KeywordStrategyMode
from app.modules.shop_runner.service_manager.services.auto_updater_v3.keyword_dto.dto.keyword_mode import (
    KeywordMode,
)
from app.modules.shop_runner.service_manager.services.auto_updater_v3.keyword_dto.dto.keyword_v3_ladder_state import (
    KeywordV3LadderState,
)
from app.modules.shop_runner.service_manager.services.auto_updater_v3.keyword_dto.dto.ladder_state_kind import (
    V3LadderStageKind,
)
from app.modules.shop_runner.service_manager.services.auto_updater_v3.keyword_dto.dto.next_state import (
    NextState,
)
from app.modules.shop_runner.service_manager.services.auto_updater_v3.keyword_dto.dto.next_target_place import (
    NextTargetPlace,
)
from app.modules.shop_runner.service_manager.services.auto_updater_v3.selector import (
    KeywordV3Context,
)
from app.modules.shop_runner.service_manager.services.auto_updater_v3.v3_keyword_changes_report.builder import (
    build_keyword_changes_snapshot,
)
from tests.unit.test_auto_updater_v3 import _calc_kw


def _dto(
    ks_id: int,
    *,
    mode: KeywordStrategyMode = KeywordStrategyMode.MIN_CPA,
    text: str | None = None,
) -> "KeywordDTO":
    from app.modules.shop_runner.service_manager.services.auto_updater_v3.keyword_dto import (
        KeywordDTO,
    )

    kw = _calc_kw(
        ks_id=ks_id,
        text=text or f"kw{ks_id}",
        mode=mode,
        rating=1.0,
    )
    ctx = KeywordV3Context(keyword=kw, position_profile=None)
    states = (
        KeywordV3LadderState(
            keyword_setting_id=ks_id,
            stage=V3LadderStageKind.OFF,
            strategy_mode=KeywordStrategyMode.OFF,
            target_position=0,
            cpo=None,
        ),
        KeywordV3LadderState(
            keyword_setting_id=ks_id,
            stage=V3LadderStageKind.MIN_CPA,
            strategy_mode=KeywordStrategyMode.MIN_CPA,
            target_position=0,
            cpo=100.0,
        ),
        KeywordV3LadderState(
            keyword_setting_id=ks_id,
            stage=V3LadderStageKind.OPTIMUM,
            strategy_mode=KeywordStrategyMode.OPTIMUM,
            target_position=10,
            cpo=200.0,
        ),
    )
    return KeywordDTO.from_context(ctx, ladder_states=states)


@pytest.mark.unit
def test_build_snapshot_aggregates_by_executor() -> None:
    dto1 = _dto(1, mode=KeywordStrategyMode.MIN_CPA)
    dto1.current_mode = NextState(
        new_mode=KeywordMode.OPTIMUM,
        executor_name="ResolveCalibrationExecutor",
    )
    dto2 = _dto(2, mode=KeywordStrategyMode.OPTIMUM)
    dto2.current_mode = NextState(
        new_mode=KeywordMode.MIN_CPA,
        executor_name="ShelfCleanupExecutor",
    )
    unchanged = _dto(3)

    snap = build_keyword_changes_snapshot(
        [dto1, dto2, unchanged],
        adv_id=42,
        tick_at=datetime(2026, 6, 3, 12, 0, tzinfo=UTC),
    )

    assert snap.adv_id == 42
    assert snap.changed_keywords == 2
    assert snap.net_up == 1
    assert snap.net_down == 1
    assert snap.net_force_off == 0

    by_phase = {p.phase_id: p for p in snap.by_phase}
    assert by_phase["resolve_calibration"].up == 1
    assert by_phase["shelf_cleanup"].down == 1
    assert len(snap.keyword_entries) == 2


@pytest.mark.unit
def test_multi_step_keyword_two_executors() -> None:
    dto = _dto(10, mode=KeywordStrategyMode.OFF)
    dto.current_mode = NextState(
        new_mode=KeywordMode.MIN_CPA,
        executor_name="PayForOrderGapEnableExecutor",
    )
    dto.current_mode = NextState(
        new_mode=KeywordMode.OPTIMUM,
        executor_name="ResolveCalibrationExecutor",
    )

    snap = build_keyword_changes_snapshot([dto], adv_id=1)
    by_phase = {p.phase_id: p for p in snap.by_phase}
    assert by_phase["pay_for_order_gap_enable"].up == 1
    assert by_phase["resolve_calibration"].up == 1
    assert snap.net_up == 1
    entry = snap.keyword_entries[0]
    assert "OFF→MIN_CPA→OPTIMUM" in entry.mode_chain
    assert len(entry.steps) == 2


@pytest.mark.unit
def test_ignored_prepare_executor_not_in_report() -> None:
    dto = _dto(5)
    dto.current_mode = NextState(
        new_mode=KeywordMode.OPTIMUM,
        executor_name="PrepareExecutor",
    )
    dto.current_mode = NextState(
        new_mode=KeywordMode.MAX_CONVERSION,
        executor_name="ResolveCalibrationExecutor",
    )

    snap = build_keyword_changes_snapshot([dto], adv_id=1)
    assert snap.changed_keywords == 1
    by_phase = {p.phase_id: p for p in snap.by_phase}
    assert "PrepareExecutor" not in {p.executor_name for p in snap.by_phase}
    assert by_phase["resolve_calibration"].up == 1
    assert len(snap.keyword_entries[0].steps) == 1


@pytest.mark.unit
def test_target_place_history_in_entry() -> None:
    dto = _dto(7)
    dto.current_target_place = NextTargetPlace(
        new_target_place=15,
        executor_name="RaiseStateToTargetCpoExecutor",
    )

    snap = build_keyword_changes_snapshot([dto], adv_id=1)
    assert snap.changed_keywords == 1
    assert snap.net_up == 0
    assert snap.keyword_entries[0].target_place_steps == ["15 (R↑)"]
