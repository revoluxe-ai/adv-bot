"""Unit: KeywordDecisionTraceCollector."""

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
from app.modules.shop_runner.service_manager.services.auto_updater_v3.keyword_dto.dto.update_context import (
    UpdateContext,
)
from app.modules.shop_runner.service_manager.services.auto_updater_v3.keyword_decision_trace.builder import (
    build_keyword_decision_trace_snapshot,
)
from app.modules.shop_runner.service_manager.services.auto_updater_v3.keyword_decision_trace.collector import (
    KeywordDecisionTraceCollector,
)
from app.modules.shop_runner.service_manager.services.auto_updater_v3.keyword_decision_trace.models import (
    TraceStepStatus,
)
from app.modules.shop_runner.service_manager.services.auto_updater_v3.selector import (
    KeywordV3Context,
)
from app.modules.shop_runner.service_manager.services.auto_updater_v3.update_pipeline.executors.hard_status_validate import (
    HardStatusValidateExecutor,
)
from app.modules.shop_runner.service_manager.services.auto_updater_v3.update_pipeline.executors.raise_state_to_target_cpo import (
    RaiseStateToTargetCpoExecutor,
)
from tests.unit.test_auto_updater_v3 import _calc_kw


def _dto(ks_id: int, *, mode: KeywordStrategyMode = KeywordStrategyMode.OFF) -> "KeywordDTO":
    from app.modules.shop_runner.service_manager.services.auto_updater_v3.keyword_dto import (
        KeywordDTO,
    )

    kw = _calc_kw(ks_id=ks_id, text=f"kw{ks_id}", mode=mode, rating=1.0, hard_status=1)
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


def _minimal_context(keywords: list) -> UpdateContext:
    from app.modules.shop_runner.service_manager.services.auto_updater_v3.activation_strategy import (
        ShelfClickMode,
    )
    from app.modules.shop_runner.service_manager.services.auto_updater_v3.calibration_step_resolver import (
        CalibrationDirect,
    )
    from app.modules.shop_runner.service_manager.services.auto_updater_v3.keyword_dto import (
        AdvState,
        build_update_context,
    )
    from app.modules.shop_runner.service_manager.services.auto_updater_v3.keyword_v3_ladder_view import (
        LadderInputs,
    )
    from app.modules.shop_runner.service_manager.services.auto_updater_v3.rollout_aggressiveness import (
        V3RolloutAggressiveness,
    )
    from app.modules.shop_runner.service_manager.services.auto_updater_v3.transition_ranking import (
        SelectionPolicy,
    )

    contexts = [dto.context for dto in keywords]
    ladder = LadderInputs.from_contexts(contexts)
    adv_state = AdvState(
        eligibility_by_ks_id={},
        ladder_inputs=ladder,
        resolve=100.0,
        policy=SelectionPolicy.from_aggressiveness(
            click_mode=ShelfClickMode.ORGANIC_DOMINANT,
            aggressiveness=V3RolloutAggressiveness.MID,
        ),
        shelf_click_mode=ShelfClickMode.ORGANIC_DOMINANT,
        aggressiveness=V3RolloutAggressiveness.MID,
        max_pay_for_order=200.0,
        fact_pay_for_order=50.0,
        plan_fact_equal=False,
        views_equal=False,
        resolve_valid=True,
        shelf_active=False,
        guard_condition=False,
        calibration_direct=CalibrationDirect.LOOSEN,
        max_effective_steps=1,
        configured_keyword_calibration_max_step=1,
        calibration_phase_extra={"calibration_direct": "loosen"},
    )
    return build_update_context(contexts, adv_state=adv_state)


@pytest.mark.unit
def test_collector_all_operable_have_entry() -> None:
    tick = datetime(2026, 6, 3, 12, 0, tzinfo=UTC)
    collector = KeywordDecisionTraceCollector()
    collector.start_tick(tick_started_at=tick)
    keywords = [_dto(1), _dto(2)]
    collector.register_operable_keywords(keywords)
    executor = HardStatusValidateExecutor()
    ctx = _minimal_context(keywords)
    steps_before = {1: 0, 2: 0}
    executor.execute(ctx)
    collector.record_executor_phase(
        context=ctx,
        executor=executor,
        order=1,
        steps_before=steps_before,
        tp_steps_before={1: 0, 2: 0},
        skip_reason=executor.skip_reason,
    )
    snap = build_keyword_decision_trace_snapshot(
        collector,
        adv_id=99,
        tick_finished_at=tick,
        nmids=[519358830],
    )
    assert snap.operable_keywords == 2
    assert len(snap.entries) == 2
    assert all(e.processing_started for e in snap.entries)


@pytest.mark.unit
def test_collector_unchanged_off_has_skip_steps() -> None:
    tick = datetime(2026, 6, 3, 12, 0, tzinfo=UTC)
    collector = KeywordDecisionTraceCollector()
    collector.start_tick(tick_started_at=tick)
    off = _dto(10, mode=KeywordStrategyMode.OFF)
    collector.register_operable_keywords([off])
    executor = HardStatusValidateExecutor()
    ctx = _minimal_context([off])
    executor.execute(ctx)
    collector.record_executor_phase(
        context=ctx,
        executor=executor,
        order=1,
        steps_before={10: 0},
        tp_steps_before={10: 0},
        skip_reason=executor.skip_reason,
    )
    snap = build_keyword_decision_trace_snapshot(
        collector,
        adv_id=1,
        tick_finished_at=tick,
    )
    entry = snap.entries[0]
    assert entry.net_changed is False
    assert "Без изменений" in entry.final_decision_ru
    assert entry.steps[0].status == TraceStepStatus.SKIP


@pytest.mark.unit
def test_collector_apply_raise_not_block() -> None:
    tick = datetime(2026, 6, 3, 12, 0, tzinfo=UTC)
    collector = KeywordDecisionTraceCollector()
    collector.start_tick(tick_started_at=tick)
    dto = _dto(11, mode=KeywordStrategyMode.OFF)
    collector.register_operable_keywords([dto])
    ctx = _minimal_context([dto])
    dto = ctx.keywords[0]
    dto.current_mode = NextState(
        new_mode=KeywordMode.MIN_CPA,
        executor_name="RaiseStateToTargetCpoExecutor",
    )
    collector.record_executor_phase(
        context=ctx,
        executor=RaiseStateToTargetCpoExecutor(),
        order=7,
        steps_before={11: 0},
        tp_steps_before={11: 0},
        skip_reason=None,
    )
    snap = build_keyword_decision_trace_snapshot(
        collector,
        adv_id=1,
        tick_finished_at=tick,
    )
    entry = snap.entries[0]
    apply_steps = [s for s in entry.steps if s.status == TraceStepStatus.APPLY]
    assert apply_steps
    assert not any(s.status == TraceStepStatus.BLOCK for s in entry.steps)


@pytest.mark.unit
def test_collector_phase_pass_on_skip_reason() -> None:
    tick = datetime(2026, 6, 3, 12, 0, tzinfo=UTC)
    collector = KeywordDecisionTraceCollector()
    collector.start_tick(tick_started_at=tick)
    dto = _dto(12)
    collector.register_operable_keywords([dto])
    ctx = _minimal_context([dto])

    class _SkippedExecutor:
        phase_name = "resolve_calibration"
        skip_reason = "calibration_disabled"

        def execute(self, context: UpdateContext) -> None:
            return

    executor = _SkippedExecutor()
    collector.record_executor_phase(
        context=ctx,
        executor=executor,
        order=15,
        steps_before={12: 0},
        tp_steps_before={12: 0},
        skip_reason=executor.skip_reason,
    )
    snap = build_keyword_decision_trace_snapshot(
        collector,
        adv_id=1,
        tick_finished_at=tick,
    )
    step = snap.entries[0].steps[0]
    assert step.status == TraceStepStatus.PASS
    assert step.reason_ru == "calibration_disabled"
