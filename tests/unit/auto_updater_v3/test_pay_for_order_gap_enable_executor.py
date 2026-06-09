"""Unit: PayForOrderGapEnableExecutor, NSM enable_gap_to_min_cpa."""

from __future__ import annotations

from dataclasses import replace

import pytest

from app.modules.common_slaves.wildberries.models.enums import KeywordStrategyMode
from app.modules.shop_runner.service_manager.services.auto_updater_v3.campaign_pfo_gates import (
    gap_enable_plan_headroom_floor,
)
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
    PayForOrderGapEnableExecutor,
    build_normal_preamble_executors,
)
from app.modules.shop_runner.service_manager.services.auto_updater_v3.update_pipeline.executors.pay_for_order_gap_enable import (
    PayForOrderGapEnableExecutor as GapExecutorClass,
)
from app.modules.shop_runner.service_manager.services.auto_updater_v3.update_pipeline.next_state.manager import (
    NextStateManager,
)
from app.modules.wb_adv_updater.calculated_keywords_manager.dto.calculated_keyword import (
    CalculatedKeyword,
)
from app.modules.wb_adv_updater.calculated_keywords_manager.dto.inner_dto.keyword_state import (
    KeywordState,
)
from app.modules.wb_adv_updater.calculated_keywords_manager.dto.states import (
    KeywordStatus,
    KeywordStatusReason,
)
from app.modules.wb_adv_updater.calculated_keywords_manager.keyword_setting_dto import (
    KeywordSettingDTO,
)
from app.modules.wb_adv_updater.calculated_keywords_manager.keyword_stat import (
    make_zero_keyword_stat,
)
from tests.unit.test_auto_updater_v3 import _calc_kw


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


def _gap_ladder_states(ks_id: int) -> tuple[KeywordV3LadderState, ...]:
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
    )


def _gap_dto(*, ks_id: int = 1) -> KeywordDTO:
    stat = make_zero_keyword_stat(f"gap{ks_id}")
    kw = CalculatedKeyword(
        adv_id=1,
        keyword_setting=KeywordSettingDTO(
            text=f"gap{ks_id}",
            relevant=True,
            hard_status=2,
            id=ks_id,
            strategy_mode=KeywordStrategyMode.OFF,
        ),
        cluster_stat=stat,
        state=KeywordState(
            status=KeywordStatus.GOOD,
            reason=KeywordStatusReason.WHITE_LIST,
            best_keyword_status=False,
        ),
        rating=1.0,
        target_pay_for_order=None,
    )
    ctx = KeywordV3Context(keyword=kw, position_profile=None)
    return KeywordDTO.from_context(ctx, ladder_states=_gap_ladder_states(ks_id))


def _adv_state(
    *,
    fact: float = 50.0,
    resolve: float = 100.0,
    max_cpo: float = 120.0,
    eligibility: dict[int, KeywordV3Eligibility] | None = None,
) -> AdvState:
    elig = eligibility if eligibility is not None else {1: _no_data_elig()}
    return replace(
        AdvState.empty(),
        resolve=resolve,
        max_pay_for_order=max_cpo,
        fact_pay_for_order=fact,
        resolve_valid=True,
        guard_condition=fact <= max_cpo,
        eligibility_by_ks_id=elig,
    )


def _context(
    keywords: list[KeywordDTO],
    adv_state: AdvState,
):
    return UpdateContextManager().from_prepared(
        KeywordsPreparedList(keywords=keywords),
        adv_state=adv_state,
    )


@pytest.mark.unit
def test_skip_when_fact_ge_plan_headroom_ratio() -> None:
    max_cpo = 120.0
    resolve = 50.0
    fact = gap_enable_plan_headroom_floor(max_cpo)
    ctx = _context(
        [_gap_dto()],
        _adv_state(fact=fact, resolve=resolve, max_cpo=max_cpo),
    )
    executor = PayForOrderGapEnableExecutor()
    executor.execute(ctx)
    assert executor.skip_reason == "fact_ge_plan_headroom_ratio"
    assert ctx.keywords[0].next_state == []


@pytest.mark.unit
def test_skip_when_fact_gt_max() -> None:
    ctx = _context(
        [_gap_dto()],
        _adv_state(fact=121.0, max_cpo=120.0),
    )
    executor = PayForOrderGapEnableExecutor()
    executor.execute(ctx)
    assert executor.skip_reason == "fact_gt_max_cpo"
    assert ctx.keywords[0].next_state == []


@pytest.mark.unit
def test_enable_one_gap_keyword_to_min_cpa() -> None:
    dto = _gap_dto()
    ctx = _context([dto], _adv_state())
    PayForOrderGapEnableExecutor().execute(ctx)
    assert dto.current_mode == KeywordStrategyMode.MIN_CPA
    assert dto.target_place == 0
    assert len(dto.next_state) == 1
    assert dto.next_state[0].executor_name == "PayForOrderGapEnableExecutor"


@pytest.mark.unit
def test_picks_lowest_keyword_setting_id() -> None:
    dto1 = _gap_dto(ks_id=2)
    dto2 = _gap_dto(ks_id=1)
    adv = _adv_state(
        eligibility={1: _no_data_elig(), 2: _no_data_elig()},
    )
    ctx = _context([dto1, dto2], adv)
    PayForOrderGapEnableExecutor().execute(ctx)
    assert dto2.current_mode == KeywordStrategyMode.MIN_CPA
    assert dto1.current_mode == KeywordStrategyMode.OFF


@pytest.mark.unit
def test_non_gap_off_unchanged() -> None:
    kw = _calc_kw(
        ks_id=3,
        text="full",
        mode=KeywordStrategyMode.OFF,
        rating=1.0,
        hard_status=2,
    )
    ctx_obj = KeywordV3Context(keyword=kw, position_profile=None)
    dto = KeywordDTO.from_context(ctx_obj, ladder_states=_full_ladder_states(3))
    ctx = _context([dto], _adv_state(eligibility={3: _no_data_elig()}))
    PayForOrderGapEnableExecutor().execute(ctx)
    assert dto.next_state == []
    assert dto.current_mode == KeywordStrategyMode.OFF


@pytest.mark.unit
def test_no_data_singleton_is_not_gap_candidate() -> None:
    kw = _calc_kw(
        ks_id=4,
        text="nd",
        mode=KeywordStrategyMode.OFF,
        rating=1.0,
        hard_status=2,
    )
    kw = kw.model_copy(update={"pay_for_order": 111.0})
    ctx_obj = KeywordV3Context(keyword=kw, position_profile=None)
    dto = KeywordDTO.from_context(
        ctx_obj,
        ladder_states=(
            KeywordV3LadderState(
                keyword_setting_id=4,
                stage=V3LadderStageKind.OFF,
                strategy_mode=KeywordStrategyMode.OFF,
                target_position=0,
                cpo=111.0,
                synthetic_no_data=True,
            ),
        ),
    )
    ctx = _context([dto], _adv_state(eligibility={4: _no_data_elig()}))
    PayForOrderGapEnableExecutor().execute(ctx)
    assert dto.next_state == []
    assert dto.current_mode == KeywordStrategyMode.OFF


@pytest.mark.unit
def test_nsm_enable_gap_to_min_cpa() -> None:
    dto = _gap_dto()
    nsm = NextStateManager(GapExecutorClass)
    nsm.enable_gap_to_min_cpa(dto)
    assert dto.current_mode == KeywordStrategyMode.MIN_CPA
    assert dto.target_place == 0


@pytest.mark.unit
def test_gap_enable_in_preamble() -> None:
    executors = build_normal_preamble_executors()
    phases = [ex.phase_name for ex in executors]
    assert "pay_for_order_gap_enable" in phases
