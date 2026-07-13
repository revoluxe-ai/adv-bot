"""Unit: BLOCK только при FORCE_OFF."""

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
from app.modules.shop_runner.service_manager.services.auto_updater_v3.keyword_decision_trace.collector import (
    KeywordDecisionTraceCollector,
)
from app.modules.shop_runner.service_manager.services.auto_updater_v3.keyword_decision_trace.models import (
    TraceStepStatus,
)
from app.modules.shop_runner.service_manager.services.auto_updater_v3.selector import (
    KeywordV3Context,
)
from tests.unit.auto_updater_v3.keyword_decision_trace.test_keyword_decision_trace_collector import (
    _minimal_context,
)
from tests.unit.test_auto_updater_v3 import _calc_kw


def _dto(ks_id: int) -> "KeywordDTO":
    from app.modules.shop_runner.service_manager.services.auto_updater_v3.keyword_dto import (
        KeywordDTO,
    )

    kw = _calc_kw(
        ks_id=ks_id,
        text=f"kw{ks_id}",
        mode=KeywordStrategyMode.MIN_CPA,
        rating=1.0,
        hard_status=2,
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
def test_collector_block_force_off_only() -> None:
    tick = datetime(2026, 6, 3, 12, 0, tzinfo=UTC)
    collector = KeywordDecisionTraceCollector()
    collector.start_tick(tick_started_at=tick)
    dto = _dto(20)
    collector.register_operable_keywords([dto])
    ctx = _minimal_context([dto])
    dto = ctx.keywords[0]
    dto.current_mode = NextState(
        new_mode=KeywordMode.OFF,
        executor_name="ShelfCleanupExecutor",
    )

    class ShelfCleanupExecutor:
        phase_name = "shelf_cleanup"
        skip_reason = None

        def execute(self, context) -> None:
            return

    collector.record_executor_phase(
        context=ctx,
        executor=ShelfCleanupExecutor(),
        order=10,
        steps_before={20: 0},
        tp_steps_before={20: 0},
        skip_reason=None,
    )
    step = collector.iter_accumulators()[0].steps[0]
    assert step.status == TraceStepStatus.BLOCK
    assert "FORCE_OFF" in step.decision_ru
