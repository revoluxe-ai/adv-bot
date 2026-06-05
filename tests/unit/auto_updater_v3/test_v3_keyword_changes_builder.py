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
from app.modules.shop_runner.service_manager.services.auto_updater_v3.v3_keyword_changes_report.keyword_entry import (
    find_keyword_change_entry,
    last_decisive_step,
)
from app.modules.shop_runner.service_manager.services.auto_updater_v3.v3_keyword_changes_report.models import (
    V3KeywordChangeEntry,
    V3KeywordStepRecord,
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
    assert by_phase["pay_for_order_gap_enable"].ended_on == 1
    assert by_phase["resolve_calibration"].up == 1
    assert by_phase["resolve_calibration"].ended_on == 0
    assert snap.net_up == 1
    assert snap.net_on == 1
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


@pytest.mark.unit
def test_shelf_force_off_counts_ended_off() -> None:
    dto = _dto(1, mode=KeywordStrategyMode.OPTIMUM)
    dto.current_mode = NextState(
        new_mode=KeywordMode.OFF,
        executor_name="ShelfCleanupExecutor",
    )

    snap = build_keyword_changes_snapshot([dto], adv_id=1)
    shelf = next(p for p in snap.by_phase if p.phase_id == "shelf_cleanup")
    assert shelf.up == 0
    assert shelf.down == 0
    assert shelf.force_off == 1
    assert shelf.ended_off == 1
    assert shelf.ended_on == 0
    assert snap.net_force_off == 1
    assert snap.net_on == 0


@pytest.mark.unit
def test_last_decisive_step_picks_last_non_noop() -> None:
    entry = V3KeywordChangeEntry(
        keyword_setting_id=1,
        keyword_text="kw",
        stored_mode="OFF",
        current_mode="OPTIMUM",
        steps=[
            V3KeywordStepRecord(
                executor_name="PayForOrderGapEnableExecutor",
                from_mode="OFF",
                to_mode="MIN_CPA",
                action="UP",
            ),
            V3KeywordStepRecord(
                executor_name="ResolveCalibrationExecutor",
                from_mode="MIN_CPA",
                to_mode="OPTIMUM",
                action="UP",
            ),
        ],
    )
    decisive = last_decisive_step(entry)
    assert isinstance(decisive, V3KeywordStepRecord)
    assert decisive.executor_name == "ResolveCalibrationExecutor"


@pytest.mark.unit
def test_last_decisive_step_skips_trailing_noop() -> None:
    entry = V3KeywordChangeEntry(
        keyword_setting_id=1,
        keyword_text="kw",
        stored_mode="MIN_CPA",
        current_mode="MIN_CPA",
        steps=[
            V3KeywordStepRecord(
                executor_name="ShelfCleanupExecutor",
                from_mode="MIN_CPA",
                to_mode="OPTIMUM",
                action="UP",
            ),
            V3KeywordStepRecord(
                executor_name="SkipUpTargetPlaceExecutor",
                from_mode="OPTIMUM",
                to_mode="OPTIMUM",
                action="NOOP",
            ),
        ],
    )
    decisive = last_decisive_step(entry)
    assert isinstance(decisive, V3KeywordStepRecord)
    assert decisive.executor_name == "ShelfCleanupExecutor"


@pytest.mark.unit
def test_last_decisive_step_target_place_when_all_noop() -> None:
    entry = V3KeywordChangeEntry(
        keyword_setting_id=7,
        keyword_text="kw",
        stored_mode="MIN_CPA",
        current_mode="MIN_CPA",
        steps=[
            V3KeywordStepRecord(
                executor_name="SkipUpTargetPlaceExecutor",
                from_mode="MIN_CPA",
                to_mode="MIN_CPA",
                action="NOOP",
            ),
        ],
        target_place_steps=["15 (R↑)", "20 (R↑)"],
    )
    assert last_decisive_step(entry) == "20 (R↑)"


@pytest.mark.unit
def test_find_keyword_change_entry_by_id() -> None:
    dto = _dto(5)
    dto.current_mode = NextState(
        new_mode=KeywordMode.OPTIMUM,
        executor_name="ResolveCalibrationExecutor",
    )
    snap = build_keyword_changes_snapshot([dto], adv_id=1)
    found = find_keyword_change_entry(snap, 5)
    assert found is not None
    assert found.keyword_setting_id == 5
    assert find_keyword_change_entry(snap, 999) is None
    assert find_keyword_change_entry(None, 5) is None
