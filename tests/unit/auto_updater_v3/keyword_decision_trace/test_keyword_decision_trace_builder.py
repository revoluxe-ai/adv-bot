"""Unit: build_keyword_decision_trace_snapshot decisive fields."""

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
from tests.unit.test_auto_updater_v3 import _calc_kw


def _dto(ks_id: int) -> "KeywordDTO":
    from app.modules.shop_runner.service_manager.services.auto_updater_v3.keyword_dto import (
        KeywordDTO,
    )

    kw = _calc_kw(
        ks_id=ks_id,
        text="test kw",
        mode=KeywordStrategyMode.OFF,
        rating=1.0,
        hard_status=1,
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
    )
    return KeywordDTO.from_context(ctx, ladder_states=states)


@pytest.mark.unit
def test_builder_decisive_executor_and_timing() -> None:
    tick_start = datetime(2026, 6, 3, 11, 0, tzinfo=UTC)
    tick_end = datetime(2026, 6, 3, 11, 1, tzinfo=UTC)
    collector = KeywordDecisionTraceCollector()
    collector.start_tick(tick_started_at=tick_start)
    dto = _dto(42)
    collector.register_operable_keywords([dto], nmids=[519358830])
    dto.current_mode = NextState(
        new_mode=KeywordMode.MIN_CPA,
        executor_name="RaiseStateToTargetCpoExecutor",
    )
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

    contexts = [dto.context]
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
    ctx = build_update_context(contexts, adv_state=adv_state)
    dto = ctx.keywords[0]

    class RaiseStateToTargetCpoExecutor:
        phase_name = "raise_state_to_target_cpo"
        skip_reason = None

        def execute(self, context: UpdateContext) -> None:
            return

    dto.current_mode = NextState(
        new_mode=KeywordMode.MIN_CPA,
        executor_name="RaiseStateToTargetCpoExecutor",
    )
    collector.record_executor_phase(
        context=ctx,
        executor=RaiseStateToTargetCpoExecutor(),
        order=7,
        steps_before={42: 0},
        tp_steps_before={42: 0},
        skip_reason=None,
    )
    snap = build_keyword_decision_trace_snapshot(
        collector,
        adv_id=519358830,
        tick_finished_at=tick_end,
        nmids=[519358830],
    )
    assert snap.tick_started_at == tick_start
    assert snap.tick_finished_at == tick_end
    entry = snap.entries[0]
    assert entry.decisive_executor is not None
    assert entry.net_changed is True
    assert entry.steps[0].status == TraceStepStatus.APPLY
