"""Unit: PayForOrderNoChEnableExecutor and its interaction with NORMAL preamble."""

from __future__ import annotations

from dataclasses import replace

import pytest

from app.modules.common_slaves.wildberries.models.enums import KeywordStrategyMode
from app.modules.shop_runner.service_manager.services.auto_updater_v3.keyword_v3_decision_data import (
    KeywordV3DecisionTier,
)
from app.modules.shop_runner.service_manager.services.auto_updater_v3.keyword_v3_eligibility import (
    KeywordDataTier,
    KeywordV3Eligibility,
)
from app.modules.shop_runner.service_manager.services.auto_updater_v3.keyword_dto import (
    KeywordDTO,
    UpdateContextManager,
)
from app.modules.shop_runner.service_manager.services.auto_updater_v3.keyword_dto.dto import (
    AdvState,
    KeywordsPreparedList,
    UpdateContext,
)
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
from app.modules.shop_runner.service_manager.services.auto_updater_v3.selector import (
    KeywordV3Context,
)
from app.modules.shop_runner.service_manager.services.auto_updater_v3.update_pipeline.executors import (
    PayForOrderGapEnableExecutor,
    PayForOrderNoChEnableExecutor,
    build_normal_preamble_executors,
)
from tests.unit.test_auto_updater_v3 import _calc_kw


def _pfo_elig() -> KeywordV3Eligibility:
    return KeywordV3Eligibility(
        data_tier=KeywordDataTier.KEYWORD_PFO,
        allowed_modes=frozenset({KeywordStrategyMode.MIN_CPA}),
        max_allowed_mode=KeywordStrategyMode.MIN_CPA,
        participates_in_ladder=True,
        target_place_fallback_zero=True,
        imputed=False,
        fallback_kind="none",
        decision_tier=KeywordV3DecisionTier.NO_CH_MATRIX,
    )


def _no_data_elig() -> KeywordV3Eligibility:
    return KeywordV3Eligibility(
        data_tier=KeywordDataTier.KEYWORD_NO_DATA,
        allowed_modes=frozenset(),
        max_allowed_mode=KeywordStrategyMode.OFF,
        participates_in_ladder=False,
        target_place_fallback_zero=True,
        imputed=False,
        fallback_kind=None,
        decision_tier=KeywordV3DecisionTier.NO_CONV,
    )


def _ladder_states(ks_id: int) -> tuple[KeywordV3LadderState, ...]:
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


def _gap_states(ks_id: int) -> tuple[KeywordV3LadderState, ...]:
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
            stage=V3LadderStageKind.GAP,
            strategy_mode=KeywordStrategyMode.OFF,
            target_position=0,
            cpo=None,
        ),
    )


def _dto(
    *,
    ks_id: int = 1,
    hard_status: int = 2,
    pay_for_order: float | None = 50.0,
    position_profile: list[object] | None = None,
    states: tuple[KeywordV3LadderState, ...] | None = None,
) -> KeywordDTO:
    kw = _calc_kw(
        ks_id=ks_id,
        text=f"kw{ks_id}",
        mode=KeywordStrategyMode.OFF,
        rating=1.0,
        hard_status=hard_status,
    )
    kw = kw.model_copy(update={"pay_for_order": pay_for_order})
    ctx = KeywordV3Context(keyword=kw, position_profile=position_profile)
    return KeywordDTO.from_context(ctx, ladder_states=states or _ladder_states(ks_id))


def _adv_state(
    *,
    resolve: float = 100.0,
    eligibility: dict[int, KeywordV3Eligibility] | None = None,
    fact_pay_for_order: float | None = None,
    max_pay_for_order: float = 95.0,
    guard_condition: bool = False,
) -> AdvState:
    return replace(
        AdvState.empty(),
        resolve=resolve,
        resolve_valid=True,
        fact_pay_for_order=fact_pay_for_order,
        max_pay_for_order=max_pay_for_order,
        guard_condition=guard_condition,
        eligibility_by_ks_id=eligibility or {1: _pfo_elig()},
    )


def _context(keywords: list[KeywordDTO], adv_state: AdvState) -> UpdateContext:
    return UpdateContextManager().from_prepared(
        KeywordsPreparedList(keywords=keywords),
        adv_state=adv_state,
    )


def _raw_context(keywords: list[KeywordDTO], adv_state: AdvState) -> UpdateContext:
    return UpdateContext(prepared=KeywordsPreparedList(keywords=keywords), adv_state=adv_state)


@pytest.mark.unit
def test_normal_pfo_no_ch_off_to_min_creates_explicit_action() -> None:
    dto = _dto()
    ctx = _context([dto], _adv_state())
    PayForOrderNoChEnableExecutor().execute(ctx)
    assert dto.current_mode == KeywordStrategyMode.MIN_CPA
    assert dto.target_place == 0
    assert len(dto.next_state) == 1
    assert dto.next_state[0].executor_name == "PayForOrderNoChEnableExecutor"


@pytest.mark.unit
def test_keyword_pay_for_order_gt_resolve_skips() -> None:
    dto = _dto()
    pfo = dto.calculated_keyword.pay_for_order
    assert pfo is not None
    ctx = _context([dto], _adv_state(resolve=float(pfo) - 1.0))
    executor = PayForOrderNoChEnableExecutor()
    executor.execute(ctx)
    assert executor.skip_reason == "no_candidates"
    assert dto.next_state == []


@pytest.mark.unit
def test_hard_status_not_allowed_skips() -> None:
    dto = _dto(hard_status=4)
    ctx = _context([dto], _adv_state())
    executor = PayForOrderNoChEnableExecutor()
    executor.execute(ctx)
    assert executor.skip_reason == "no_candidates"
    assert dto.next_state == []


@pytest.mark.unit
def test_position_profile_exists_skips() -> None:
    dto = _dto(position_profile=[object()])
    ctx = _context([dto], _adv_state())
    executor = PayForOrderNoChEnableExecutor()
    executor.execute(ctx)
    assert executor.skip_reason == "no_candidates"
    assert dto.next_state == []


@pytest.mark.unit
def test_keyword_no_data_not_taken_by_new_executor() -> None:
    dto = _dto(pay_for_order=None, states=_gap_states(1))
    ctx = _context([dto], _adv_state(eligibility={1: _no_data_elig()}))
    executor = PayForOrderNoChEnableExecutor()
    executor.execute(ctx)
    assert executor.skip_reason == "no_candidates"
    assert dto.next_state == []


@pytest.mark.unit
def test_campaign_fact_over_max_blocks_expensive_key_enable() -> None:
    cheap = _dto(ks_id=1, pay_for_order=80.0)
    expensive = _dto(ks_id=2, pay_for_order=125.0)
    adv = _adv_state(
        resolve=150.0,
        fact_pay_for_order=120.0,
        max_pay_for_order=95.0,
        guard_condition=True,
        eligibility={1: _pfo_elig(), 2: _pfo_elig()},
    )
    ctx = _context([cheap, expensive], adv)
    PayForOrderNoChEnableExecutor().execute(ctx)
    assert cheap.current_mode == KeywordStrategyMode.MIN_CPA
    assert expensive.current_mode == KeywordStrategyMode.OFF


@pytest.mark.unit
def test_overspend_enables_cheap_key_below_fact() -> None:
    cheap = _dto(ks_id=1, pay_for_order=600.0)
    expensive = _dto(ks_id=2, pay_for_order=850.0)
    adv = _adv_state(
        resolve=900.0,
        fact_pay_for_order=800.0,
        max_pay_for_order=500.0,
        guard_condition=True,
        eligibility={1: _pfo_elig(), 2: _pfo_elig()},
    )
    ctx = _context([cheap, expensive], adv)
    PayForOrderNoChEnableExecutor().execute(ctx)
    assert cheap.current_mode == KeywordStrategyMode.MIN_CPA
    assert expensive.current_mode == KeywordStrategyMode.OFF


@pytest.mark.unit
def test_one_key_per_tick_deterministic_order() -> None:
    dto1 = _dto(ks_id=2, pay_for_order=40.0)
    dto2 = _dto(ks_id=1, pay_for_order=50.0)
    adv = _adv_state(eligibility={1: _pfo_elig(), 2: _pfo_elig()})
    ctx = _context([dto1, dto2], adv)
    PayForOrderNoChEnableExecutor().execute(ctx)
    assert dto2.current_mode == KeywordStrategyMode.MIN_CPA
    assert dto1.current_mode == KeywordStrategyMode.OFF


@pytest.mark.unit
def test_new_executor_in_preamble_before_rebalance() -> None:
    phases = [e.phase_name for e in build_normal_preamble_executors()]
    assert "pay_for_order_no_ch_enable" in phases
    assert phases.index("pay_for_order_no_ch_enable") < phases.index("cost_reallocation")
    assert phases.index("pay_for_order_gap_enable") > phases.index("cost_reallocation")
