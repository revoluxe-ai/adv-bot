"""Unit: PayForOrderOverMaxOffOnDeepOverspendExecutor и campaign_pfo_gates."""

from __future__ import annotations

from dataclasses import replace

import pytest

from app.modules.common_slaves.wildberries.models.enums import KeywordStrategyMode
from app.modules.shop_runner.service_manager.services.auto_updater_v3.campaign_pfo_gates import (
    is_campaign_at_plan_headroom_plus_one,
    is_deep_overspend,
    keyword_pay_for_order_over_plan_max,
    pfo_off_plan_headroom_floor,
    plan_max_stabilization_floor,
)
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
from app.modules.shop_runner.service_manager.services.auto_updater_v3.selector import (
    KeywordV3Context,
)
from app.modules.shop_runner.service_manager.services.auto_updater_v3.update_pipeline.executors import (
    build_normal_preamble_executors,
)
from app.modules.shop_runner.service_manager.services.auto_updater_v3.update_pipeline.executors.pay_for_order_over_max_off_on_deep_overspend import (
    PayForOrderOverMaxOffOnDeepOverspendExecutor,
)
from app.modules.shop_runner.service_manager.services.auto_updater_v3.update_pipeline.executors.raise_state_to_target_cpo import (
    RaiseStateToTargetCpoExecutor,
)
from tests.unit.test_auto_updater_v3 import _calc_kw, _conv_for_pay_for_order, _sample_profile


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


def _dto(
    *,
    ks_id: int = 1,
    mode: KeywordStrategyMode = KeywordStrategyMode.MIN_CPA,
    pfo_target: float | None = 600.0,
) -> KeywordDTO:
    conv = (
        _conv_for_pay_for_order(pfo_target)
        if pfo_target is not None
        else 0.05
    )
    kw = _calc_kw(
        ks_id=ks_id,
        text=f"kw{ks_id}",
        mode=mode,
        rating=1.0,
        hard_status=2,
        conv=conv,
    )
    ctx = KeywordV3Context(keyword=kw, position_profile=None)
    return KeywordDTO.from_context(ctx, ladder_states=_ladder_states(ks_id))


def _adv_state(*, fact: float, max_cpo: float = 550.0) -> AdvState:
    return replace(
        AdvState.empty(),
        resolve=500.0,
        max_pay_for_order=max_cpo,
        fact_pay_for_order=fact,
        resolve_valid=True,
    )


def _context(keywords: list[KeywordDTO], adv: AdvState):
    return UpdateContextManager().from_prepared(
        KeywordsPreparedList(keywords=keywords),
        adv_state=adv,
    )


@pytest.mark.unit
def test_is_campaign_at_plan_headroom_plus_one_boundary() -> None:
    max_cpo = 100.0
    floor = plan_max_stabilization_floor(max_cpo)
    adv_below = _adv_state(fact=floor - 0.01, max_cpo=max_cpo)
    adv_at = _adv_state(fact=floor, max_cpo=max_cpo)
    assert is_campaign_at_plan_headroom_plus_one(adv_below) is False
    assert is_deep_overspend(adv_at) is True


@pytest.mark.unit
def test_skip_when_fact_lt_plan_headroom_ratio() -> None:
    max_cpo = 100.0
    fact = plan_max_stabilization_floor(max_cpo) - 0.01
    ctx = _context([_dto()], _adv_state(fact=fact, max_cpo=max_cpo))
    executor = PayForOrderOverMaxOffOnDeepOverspendExecutor()
    executor.execute(ctx)
    assert executor.skip_reason == "fact_lt_plan_headroom_ratio"
    assert ctx.keywords[0].next_state == []


@pytest.mark.unit
def test_off_active_keyword_when_at_plan_headroom_and_pfo_gt_max() -> None:
    """OFF только если нет ступени с ``cpo <= max`` (все operable выше потолка)."""
    max_cpo = 550.0
    ks_id = 1
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
            target_position=10,
            cpo=600.0,
        ),
    )
    dto = _dto(pfo_target=600.0)
    dto = KeywordDTO.from_context(
        KeywordV3Context(keyword=dto.calculated_keyword, position_profile=_sample_profile()),
        ladder_states=states,
    )
    fact = pfo_off_plan_headroom_floor(max_cpo)
    ctx = _context([dto], _adv_state(fact=fact, max_cpo=max_cpo))
    PayForOrderOverMaxOffOnDeepOverspendExecutor().execute(ctx)
    assert dto.current_mode == KeywordStrategyMode.OFF
    assert len(dto.next_state) == 1


@pytest.mark.unit
def test_no_off_when_pfo_at_or_below_max() -> None:
    max_cpo = 550.0
    dto = _dto(pfo_target=500.0)
    ctx = _context([dto], _adv_state(fact=610.0, max_cpo=max_cpo))
    PayForOrderOverMaxOffOnDeepOverspendExecutor().execute(ctx)
    assert dto.current_mode == KeywordStrategyMode.MIN_CPA
    assert dto.next_state == []


@pytest.mark.unit
def test_keyword_pfo_over_plan_max_gate() -> None:
    max_cpo = 550.0
    high = _dto(pfo_target=600.0)
    low = _dto(ks_id=2, pfo_target=400.0)
    assert keyword_pay_for_order_over_plan_max(high, max_pay=max_cpo) is True
    assert keyword_pay_for_order_over_plan_max(low, max_pay=max_cpo) is False


@pytest.mark.unit
def test_pfo_off_skips_when_current_ladder_cpo_at_or_below_max_after_raise() -> None:
    """R↑ поднял на MAX с cpo<=max — pfo_off не гасит, даже если aggregate PFO > max."""
    max_cpo = 550.0
    ks_id = 17783643
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
            stage=V3LadderStageKind.MAX_CONVERSION,
            strategy_mode=KeywordStrategyMode.MAX_CONVERSION,
            target_position=1,
            cpo=10.689,
        ),
    )
    dto = _dto(ks_id=ks_id, mode=KeywordStrategyMode.OFF, pfo_target=600.0)
    dto = KeywordDTO.from_context(
        KeywordV3Context(
            keyword=dto.calculated_keyword,
            position_profile=_sample_profile(),
        ),
        ladder_states=states,
    )
    adv = _adv_state(fact=700.0, max_cpo=max_cpo)
    ctx = _context([dto], adv)
    RaiseStateToTargetCpoExecutor().execute(ctx)
    # При fact > 90% от max — R↑ пропускает ключи с PFO > max, остаёмся в OFF
    assert dto.current_mode == KeywordStrategyMode.OFF
    PayForOrderOverMaxOffOnDeepOverspendExecutor().execute(ctx)
    # Фаза pfo_off ничего не делает для уже OFF ключа
    assert dto.current_mode == KeywordStrategyMode.OFF
    assert len(dto.next_state) == 0


@pytest.mark.unit
def test_pfo_off_in_preamble_order() -> None:
    phases = [ex.phase_name for ex in build_normal_preamble_executors()]
    idx_enable = phases.index("pay_for_order_gap_enable")
    idx_off = phases.index("pay_for_order_over_max_off_on_deep_overspend")
    idx_cal = phases.index("resolve_calibration")
    assert idx_off == idx_enable + 1
    assert idx_cal == idx_off + 1
