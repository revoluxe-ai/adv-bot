"""Unit: black-box characterization of NORMAL preamble manager output."""

from __future__ import annotations

from dataclasses import replace

import pytest

from app.modules.common_slaves.wildberries.models.enums import KeywordStrategyMode
from app.modules.shop_runner.service_manager.services.auto_updater_v3.keyword_dto import (
    KeywordDTO,
    UpdateContextManager,
)
from app.modules.shop_runner.service_manager.services.auto_updater_v3.keyword_dto.dto import (
    AdvState,
    KeywordsPreparedList,
)
from app.modules.shop_runner.service_manager.services.auto_updater_v3.keyword_dto.dto.keyword_v3_ladder_state import (
    KeywordV3LadderState,
)
from app.modules.shop_runner.service_manager.services.auto_updater_v3.keyword_dto.dto.ladder_state_kind import (
    V3LadderStageKind,
)
from app.modules.shop_runner.service_manager.services.auto_updater_v3.keyword_dto.dto.keyword_mode import (
    KeywordMode,
)
from app.modules.shop_runner.service_manager.services.auto_updater_v3.keyword_v3_eligibility import (
    KeywordDataTier,
    KeywordV3Eligibility,
)
from app.modules.shop_runner.service_manager.services.auto_updater_v3.keyword_v3_decision_data import (
    KeywordV3DecisionTier,
)
from app.modules.shop_runner.service_manager.services.auto_updater_v3.selector import (
    KeywordV3Context,
)
from app.modules.shop_runner.service_manager.services.auto_updater_v3.keyword_dto.dto.update_context import (
    UpdateContext,
)
from app.modules.shop_runner.service_manager.services.auto_updater_v3.keyword_dto.dto.update_context_runtime import (
    UpdateContextRuntime,
)
from app.modules.shop_runner.service_manager.services.auto_updater_v3.update_pipeline.manager import (
    UpdatePipelineManager,
)
from app.modules.shop_runner.service_manager.services.auto_updater_v3.v3_tick_report import (
    V3TickReportCollector,
)
from app.modules.wb_adv_updater.calculated_keywords_manager.dto.states import (
    KeywordStatus,
    KeywordStatusReason,
)
from tests.unit.auto_updater_v3.test_pay_for_order_no_ch_enable_executor import (
    _pfo_elig,
)
from tests.unit.auto_updater_v3.test_update_pipeline_manager_run_preamble import (
    _with_runtime,
)
from tests.unit.test_auto_updater_v3 import _calc_kw, _conv_for_pay_for_order, _sample_profile


def _full_ladder_states(ks_id: int) -> tuple[KeywordV3LadderState, ...]:
    return (
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
            target_position=10,
            cpo=300.0,
        ),
        KeywordV3LadderState(
            keyword_setting_id=ks_id,
            stage=V3LadderStageKind.OPTIMUM,
            strategy_mode=KeywordStrategyMode.OPTIMUM,
            target_position=20,
            cpo=400.0,
        ),
    )


def _pfo_ladder_states(ks_id: int) -> tuple[KeywordV3LadderState, ...]:
    return (
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
            cpo=150.0,
        ),
    )


def _full_dto(
    *,
    ks_id: int = 1,
    mode: KeywordStrategyMode = KeywordStrategyMode.MIN_CPA,
    target_place: int | None = None,
) -> KeywordDTO:
    kw = _calc_kw(
        ks_id=ks_id,
        text=f"kw{ks_id}",
        mode=mode,
        rating=1.0,
        hard_status=2,
        views=0,
        conv=0.05,
        status=KeywordStatus.BAD,
        reason=KeywordStatusReason.WHITE_LIST,
        cpm_set_bid=510,
    )
    dto = KeywordDTO.from_context(
        KeywordV3Context(keyword=kw, position_profile=_sample_profile()),
        ladder_states=_full_ladder_states(ks_id),
    )
    if target_place is not None:
        kw.keyword_setting.target_place = target_place
    return dto


def _pfo_dto(
    *,
    ks_id: int = 1,
    mode: KeywordStrategyMode = KeywordStrategyMode.OFF,
    pay_for_order: float | None = 50.0,
) -> KeywordDTO:
    kw = _calc_kw(
        ks_id=ks_id,
        text=f"kw{ks_id}",
        mode=mode,
        rating=1.0,
        hard_status=2,
    )
    kw = kw.model_copy(update={"pay_for_order": pay_for_order})
    return KeywordDTO.from_context(
        type("C", (), {"keyword": kw, "position_profile": None})(),
        ladder_states=_pfo_ladder_states(ks_id),
    )


def _full_adv_state(
    *,
    resolve: float = 100.0,
    fact_pay_for_order: float | None = 50.0,
    max_pay_for_order: float = 120.0,
) -> AdvState:
    return replace(
        AdvState.empty(),
        resolve=resolve,
        resolve_valid=True,
        fact_pay_for_order=fact_pay_for_order,
        max_pay_for_order=max_pay_for_order,
        guard_condition=False,
        calibration_direct=None,
        max_effective_steps=0,
        shelf_active=False,
    )


def _pfo_adv_state(
    *,
    resolve_valid: bool,
    fact_pay_for_order: float | None,
    resolve: float = 100.0,
    max_pay_for_order: float = 95.0,
) -> AdvState:
    return replace(
        AdvState.empty(),
        resolve=resolve,
        resolve_valid=resolve_valid,
        fact_pay_for_order=fact_pay_for_order,
        max_pay_for_order=max_pay_for_order,
        guard_condition=False,
        calibration_direct=None,
        max_effective_steps=0,
        shelf_active=False,
        eligibility_by_ks_id={1: _pfo_elig()},
    )


def _context(keywords: list[KeywordDTO], adv_state: AdvState) -> UpdateContext:
    return _with_runtime(
        UpdateContextManager().from_prepared(
            KeywordsPreparedList(keywords=keywords),
            adv_state=adv_state,
        )
    )


@pytest.mark.unit
def test_run_preamble_full_keyword_already_at_target_remains_unchanged() -> None:
    dto = _full_dto(mode=KeywordStrategyMode.OPTIMUM, target_place=20)
    ctx = _context([dto], _full_adv_state())

    result = UpdatePipelineManager().run_preamble(ctx)

    assert dto.current_mode == KeywordStrategyMode.OPTIMUM
    assert dto.current_target_place == 20
    assert dto.next_state == []
    assert dto.history_target_place == []
    assert result.pfo_off_count == 0
    assert result.enable_count == 0
    assert result.resolve_clamp_count == 0
    assert result.calibration_executed is False


@pytest.mark.unit
def test_run_preamble_pfo_keyword_skipped_when_bootstrap_gates_block() -> None:
    dto = _pfo_dto(mode=KeywordStrategyMode.OFF, pay_for_order=50.0)
    ctx = _context([dto], _pfo_adv_state(resolve_valid=False, fact_pay_for_order=None))

    result = UpdatePipelineManager().run_preamble(ctx)

    assert dto.current_mode == KeywordStrategyMode.OFF
    assert dto.current_target_place == 0
    assert dto.next_state == []
    assert dto.history_target_place == []
    assert result.pfo_off_count == 0
    assert result.enable_count == 0
    assert result.resolve_clamp_count == 0
    assert result.calibration_executed is False


@pytest.mark.unit
def test_run_preamble_pfo_keyword_enters_min_cpa_when_bootstrap_allows_it() -> None:
    dto = _pfo_dto(mode=KeywordStrategyMode.OFF, pay_for_order=50.0)
    ctx = _context([dto], _pfo_adv_state(resolve_valid=True, fact_pay_for_order=50.0))

    result = UpdatePipelineManager().run_preamble(ctx)

    assert dto.current_mode == KeywordStrategyMode.MIN_CPA
    assert dto.current_target_place == 0
    assert len(dto.next_state) == 1
    assert dto.next_state[0].executor_name == "PayForOrderNoChEnableExecutor"
    assert dto.next_state[0].new_mode == KeywordMode.MIN_CPA
    assert dto.next_state[0].phase_id == "pay_for_order_no_ch_enable"
    assert dto.history_target_place == []
    assert result.pfo_off_count == 0
    assert result.enable_count == 1
    assert result.resolve_clamp_count == 0
    assert result.calibration_executed is False
