"""Unit: raise_state_to_target_cpo executor, NSM и ladder_state_pick."""

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
from app.modules.shop_runner.service_manager.services.auto_updater_v3.selector import (
    KeywordV3Context,
)
from app.modules.shop_runner.service_manager.services.auto_updater_v3.update_pipeline.executors import (
    build_normal_preamble_executors,
)
from app.modules.shop_runner.service_manager.services.auto_updater_v3.update_pipeline.executors.ladder_state_pick import (
    has_operable_cpo,
    pick_max_ladder_state_at_or_below_cpo,
)
from app.modules.shop_runner.service_manager.services.auto_updater_v3.update_pipeline.executors.raise_state_to_target_cpo import (
    RaiseStateToTargetCpoExecutor,
)
from app.modules.shop_runner.service_manager.services.auto_updater_v3.update_pipeline.next_state.manager import (
    NextStateManager,
)
from app.modules.shop_runner.service_manager.services.auto_updater_v3.campaign_pfo_gates import (
    pfo_off_plan_headroom_floor, raise_state_plan_max_floor, should_skip_raise_state_to_target_cpo,

)

from tests.unit.test_auto_updater_v3 import _calc_kw, _sample_profile


def _ladder_states(
    ks_id: int,
    *,
    min_cpo: float | None = 300.0,
    opt_cpo: float | None = 400.0,
    max_cpo: float | None = 600.0,
) -> tuple[KeywordV3LadderState, ...]:
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
            cpo=min_cpo,
        ),
        KeywordV3LadderState(
            keyword_setting_id=ks_id,
            stage=V3LadderStageKind.OPTIMUM,
            strategy_mode=KeywordStrategyMode.OPTIMUM,
            target_position=20,
            cpo=opt_cpo,
        ),
        KeywordV3LadderState(
            keyword_setting_id=ks_id,
            stage=V3LadderStageKind.MAX_CONVERSION,
            strategy_mode=KeywordStrategyMode.MAX_CONVERSION,
            target_position=30,
            cpo=max_cpo,
        ),
    )


def _dto(
    *,
    ks_id: int = 1,
    mode: KeywordStrategyMode = KeywordStrategyMode.MIN_CPA,
    ladder: tuple[KeywordV3LadderState, ...] | None = None,
) -> KeywordDTO:
    kw = _calc_kw(
        ks_id=ks_id,
        text=f"kw{ks_id}",
        mode=mode,
        rating=1.0,
        hard_status=2,
    )
    ctx = KeywordV3Context(keyword=kw, position_profile=_sample_profile())
    states = ladder if ladder is not None else _ladder_states(ks_id)
    return KeywordDTO.from_context(ctx, ladder_states=states)


@pytest.mark.unit
def test_has_operable_cpo_excludes_off_and_none_cpo() -> None:
    dto = _dto()
    assert has_operable_cpo(dto) is True
    dto_empty = _dto(ladder=_ladder_states(1, min_cpo=None, opt_cpo=None, max_cpo=None))
    assert has_operable_cpo(dto_empty) is False


@pytest.mark.unit
def test_pick_max_ladder_state_at_or_below_cpo_picks_highest_passing() -> None:
    dto = _dto()
    winner = pick_max_ladder_state_at_or_below_cpo(dto, 500.0)
    assert winner is not None
    assert winner.strategy_mode == KeywordStrategyMode.OPTIMUM
    assert winner.cpo == 400.0


@pytest.mark.unit
def test_pick_max_ladder_state_at_or_below_cpo_returns_none_when_all_above() -> None:
    dto = _dto()
    assert pick_max_ladder_state_at_or_below_cpo(dto, 250.0) is None


@pytest.mark.unit
def test_pick_max_ladder_state_at_or_below_cpo_returns_none_when_no_operable_cpo() -> None:
    dto = _dto(ladder=_ladder_states(1, min_cpo=None, opt_cpo=None, max_cpo=None))
    assert has_operable_cpo(dto) is False
    assert pick_max_ladder_state_at_or_below_cpo(dto, 500.0) is None


@pytest.mark.unit
def test_apply_ladder_state_sets_mode_and_target_place() -> None:
    dto = _dto()
    state = next(
        s for s in dto.ladder_states if s.stage == V3LadderStageKind.OPTIMUM
    )
    dto.apply_ladder_state(state, executor_name="TestExecutor")
    assert dto.current_mode == KeywordStrategyMode.OPTIMUM
    assert dto.next_state[-1].executor_name == "TestExecutor"
    assert dto.target_place == 20
    assert dto.calculated_keyword.keyword_setting.strategy_mode == (
        KeywordStrategyMode.OPTIMUM
    )


@pytest.mark.unit
def test_nsm_raise_state_to_target_cpo_applies_winner() -> None:
    nsm = NextStateManager(RaiseStateToTargetCpoExecutor)
    dto = _dto(mode=KeywordStrategyMode.MIN_CPA)
    winner = pick_max_ladder_state_at_or_below_cpo(dto, 500.0)
    assert winner is not None
    nsm.raise_state_to_target_cpo(dto, winner)
    assert dto.current_mode == KeywordStrategyMode.OPTIMUM
    assert dto.target_place == 20


@pytest.mark.unit
def test_nsm_raise_state_to_target_cpo_noop_when_no_candidate() -> None:
    nsm = NextStateManager(RaiseStateToTargetCpoExecutor)
    dto = _dto(mode=KeywordStrategyMode.MIN_CPA)
    nsm.raise_state_to_target_cpo(dto, None)
    assert dto.next_state == []
    assert dto.current_mode == KeywordStrategyMode.MIN_CPA


@pytest.mark.unit
def test_raise_state_executor_mutates_matching_keywords_only() -> None:
    dto_ok = _dto(ks_id=1, mode=KeywordStrategyMode.MIN_CPA)
    dto_skip = _dto(
        ks_id=2,
        mode=KeywordStrategyMode.MIN_CPA,
        ladder=_ladder_states(2, min_cpo=800.0, opt_cpo=900.0, max_cpo=1000.0),
    )
    adv_state = replace(AdvState.empty(), resolve=500.0)
    ctx = UpdateContextManager().from_prepared(
        KeywordsPreparedList(keywords=[dto_ok, dto_skip]),
        adv_state=adv_state,
    )
    RaiseStateToTargetCpoExecutor().execute(ctx)
    assert ctx.keywords[0].current_mode == KeywordStrategyMode.OPTIMUM
    assert ctx.keywords[1].next_state == []


@pytest.mark.unit
def test_raise_state_executor_skips_down_when_already_above_resolve_cap() -> None:
    """Ключ выше max ступени под resolve — фаза R↑ не опускает (только UP)."""
    dto_high = _dto(
        ks_id=1,
        mode=KeywordStrategyMode.MAX_CONVERSION,
        ladder=_ladder_states(1, min_cpo=300.0, opt_cpo=400.0, max_cpo=600.0),
    )
    dto_low = _dto(ks_id=2, mode=KeywordStrategyMode.MIN_CPA)
    adv_state = replace(AdvState.empty(), resolve=550.0)
    ctx = UpdateContextManager().from_prepared(
        KeywordsPreparedList(keywords=[dto_high, dto_low]),
        adv_state=adv_state,
    )
    RaiseStateToTargetCpoExecutor().execute(ctx)
    assert ctx.keywords[0].current_mode == KeywordStrategyMode.MAX_CONVERSION
    assert ctx.keywords[0].next_state == []
    assert ctx.keywords[1].current_mode == KeywordStrategyMode.OPTIMUM
    assert len(ctx.keywords[1].next_state) == 1


@pytest.mark.unit
def test_should_skip_raise_state_when_fact_ge_90pct_plan_max() -> None:
    max_cpo = 550.0
    fact_at_floor = raise_state_plan_max_floor(max_cpo)
    adv_at = replace(
        AdvState.empty(),
        max_pay_for_order=max_cpo,
        fact_pay_for_order=fact_at_floor,
    )
    assert should_skip_raise_state_to_target_cpo(adv_at) is True
    adv_below = replace(
        AdvState.empty(),
        max_pay_for_order=max_cpo,
        fact_pay_for_order=fact_at_floor - 1.0,
    )
    assert should_skip_raise_state_to_target_cpo(adv_below) is False


@pytest.mark.unit
def test_raise_state_skips_phase_when_fact_ge_90pct_plan_max() -> None:
    """При fact ≥ 90 % plan.max фаза R↑ не выполняется (стабилизация кампании)."""
    max_cpo = 550.0
    fact = pfo_off_plan_headroom_floor(max_cpo)
    dto = _dto(ks_id=1, mode=KeywordStrategyMode.MIN_CPA)
    adv_state = replace(
        AdvState.empty(),
        resolve=500.0,
        max_pay_for_order=max_cpo,
        fact_pay_for_order=fact,
    )
    ctx = UpdateContextManager().from_prepared(
        KeywordsPreparedList(keywords=[dto]),
        adv_state=adv_state,
    )
    executor = RaiseStateToTargetCpoExecutor()
    executor.execute(ctx)
    assert executor.skip_reason == "fact_cpo_ge_90pct_plan_max"
    assert dto.current_mode == KeywordStrategyMode.MIN_CPA
    assert dto.next_state == []


@pytest.mark.unit
def test_raise_state_runs_when_fact_below_90pct_plan_max() -> None:
    """При fact < 90 % plan.max фаза R↑ выполняется и поднимает ключ до OPTIMUM."""
    max_cpo = 550.0
    fact = raise_state_plan_max_floor(max_cpo) - 1.0
    dto = _dto(ks_id=1, mode=KeywordStrategyMode.MIN_CPA)
    adv_state = replace(
        AdvState.empty(),
        resolve=500.0,
        max_pay_for_order=max_cpo,
        fact_pay_for_order=fact,
    )
    ctx = UpdateContextManager().from_prepared(
        KeywordsPreparedList(keywords=[dto]),
        adv_state=adv_state,
    )
    executor = RaiseStateToTargetCpoExecutor()
    executor.execute(ctx)
    assert executor.skip_reason is None
    assert dto.current_mode == KeywordStrategyMode.OPTIMUM
    assert len(dto.next_state) == 1


@pytest.mark.unit
def test_raise_state_executor_in_preamble() -> None:
    executors = build_normal_preamble_executors()
    assert executors[0].phase_name == "validate_state_by_hard_status"
    assert executors[5].phase_name == "skip_up_same_target_place"
    assert executors[6].phase_name == "raise_state_to_target_cpo"
