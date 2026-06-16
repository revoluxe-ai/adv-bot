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
from app.modules.shop_runner.service_manager.services.auto_updater_v3.update_pipeline.executors.clamp_state_to_aggression import (
    ClampStateToAggressionExecutor,
)
from app.modules.shop_runner.service_manager.services.auto_updater_v3.update_pipeline.executors.ladder_state_pick import (
    has_operable_cpo,
    pick_max_ladder_state_at_or_below_cpo,
    pick_max_valid_ladder_state_at_or_below_cpo,
)
from app.modules.shop_runner.service_manager.services.auto_updater_v3.update_pipeline.executors.raise_state_to_target_cpo import (
    RaiseStateToTargetCpoExecutor,
)
from app.modules.shop_runner.service_manager.services.auto_updater_v3.update_pipeline.next_state.manager import (
    NextStateManager,
)
from app.modules.shop_runner.service_manager.services.auto_updater_v3.campaign_pfo_gates import (
    is_campaign_in_raise_stabilization_zone,
    raise_state_resolve_stabilization_floor,
    should_skip_keyword_raise_to_target_cpo,
)

from tests.unit.test_auto_updater_v3 import _calc_kw, _conv_for_pay_for_order, _sample_profile


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
    target_pfo: float | None = None,
) -> KeywordDTO:
    conv = (
        _conv_for_pay_for_order(target_pfo)
        if target_pfo is not None
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
    ctx = KeywordV3Context(keyword=kw, position_profile=_sample_profile())
    states = ladder if ladder is not None else _ladder_states(ks_id)
    return KeywordDTO.from_context(ctx, ladder_states=states)


def _adv_state(
    *,
    resolve: float = 500.0,
    max_pay_for_order: float = 550.0,
    fact_pay_for_order: float | None = None,
    resolve_valid: bool = True,
    guard_condition: bool = False,
) -> AdvState:
    return replace(
        AdvState.empty(),
        resolve=resolve,
        max_pay_for_order=max_pay_for_order,
        fact_pay_for_order=fact_pay_for_order,
        resolve_valid=resolve_valid,
        guard_condition=guard_condition,
    )


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
def test_pick_max_ladder_state_at_or_below_cpo_includes_equal_ceiling() -> None:
    dto = _dto()
    winner = pick_max_ladder_state_at_or_below_cpo(dto, 400.0)
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
def test_pick_max_ladder_state_at_or_below_cpo_respects_aggression_cap() -> None:
    dto = _dto()
    winner = pick_max_valid_ladder_state_at_or_below_cpo(
        dto,
        500.0,
        max_target_mode=KeywordStrategyMode.MIN_CPA,
    )
    assert winner is not None
    assert winner.strategy_mode == KeywordStrategyMode.MIN_CPA


@pytest.mark.unit
def test_pick_max_valid_ladder_state_excludes_invalid_operable_state() -> None:
    dto = _dto(
        ladder=(
            KeywordV3LadderState(
                keyword_setting_id=1,
                stage=V3LadderStageKind.OFF,
                strategy_mode=KeywordStrategyMode.OFF,
                target_position=0,
                cpo=None,
            ),
            KeywordV3LadderState(
                keyword_setting_id=1,
                stage=V3LadderStageKind.MIN_CPA,
                strategy_mode=KeywordStrategyMode.MIN_CPA,
                target_position=10,
                cpo=300.0,
            ),
            KeywordV3LadderState(
                keyword_setting_id=1,
                stage=V3LadderStageKind.OPTIMUM,
                strategy_mode=KeywordStrategyMode.OPTIMUM,
                target_position=20,
                cpo=400.0,
                is_valid=False,
            ),
            KeywordV3LadderState(
                keyword_setting_id=1,
                stage=V3LadderStageKind.MAX_CONVERSION,
                strategy_mode=KeywordStrategyMode.MAX_CONVERSION,
                target_position=30,
                cpo=800.0,
            ),
        )
    )
    winner = pick_max_valid_ladder_state_at_or_below_cpo(
        dto,
        500.0,
        strict_ceiling=True,
        max_target_mode=KeywordStrategyMode.MAX_CONVERSION,
    )
    assert winner is not None
    assert winner.strategy_mode == KeywordStrategyMode.MIN_CPA
    assert winner.is_valid is True


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
def test_raise_state_executor_respects_policy_cap() -> None:
    dto = _dto(mode=KeywordStrategyMode.MIN_CPA)
    adv_state = replace(
        AdvState.empty(),
        resolve=700.0,
        policy=replace(
            AdvState.empty().policy,
            max_target_mode=KeywordStrategyMode.OPTIMUM,
        ),
    )
    ctx = UpdateContextManager().from_prepared(
        KeywordsPreparedList(keywords=[dto]),
        adv_state=adv_state,
    )
    RaiseStateToTargetCpoExecutor().execute(ctx)
    assert dto.current_mode == KeywordStrategyMode.OPTIMUM
    assert dto.target_place == 20


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
def test_is_campaign_in_raise_stabilization_zone_uses_resolve() -> None:
    resolve = 400.0
    floor = raise_state_resolve_stabilization_floor(resolve)
    adv_at = _adv_state(resolve=resolve, fact_pay_for_order=floor)
    assert is_campaign_in_raise_stabilization_zone(adv_at) is True
    adv_below = _adv_state(resolve=resolve, fact_pay_for_order=floor - 1.0)
    assert is_campaign_in_raise_stabilization_zone(adv_below) is False


@pytest.mark.unit
def test_should_skip_keyword_false_when_pfo_le_resolve_even_in_stabilization() -> None:
    resolve = 400.0
    fact = raise_state_resolve_stabilization_floor(resolve)
    adv = _adv_state(resolve=resolve, fact_pay_for_order=fact)
    cheap = _dto(target_pfo=10.73)
    assert should_skip_keyword_raise_to_target_cpo(cheap, adv) is False


@pytest.mark.unit
def test_should_skip_keyword_true_when_expensive_and_stabilization() -> None:
    resolve = 400.0
    fact = raise_state_resolve_stabilization_floor(resolve)
    adv = _adv_state(resolve=resolve, fact_pay_for_order=fact)
    expensive = _dto(target_pfo=500.0)
    assert should_skip_keyword_raise_to_target_cpo(expensive, adv) is True


@pytest.mark.unit
def test_cheap_kw_never_skipped_regardless_of_campaign_fact() -> None:
    """Регрессия: fact выше 0.9×max и 0.9×resolve, но дешёвый ключ поднимается."""
    dto = _dto(ks_id=1, mode=KeywordStrategyMode.MIN_CPA, target_pfo=10.73)
    adv_state = _adv_state(
        resolve=500.0,
        max_pay_for_order=550.0,
        fact_pay_for_order=704.0,
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
def test_raise_state_skips_expensive_kw_when_campaign_in_stabilization() -> None:
    resolve = 400.0
    fact = raise_state_resolve_stabilization_floor(resolve)
    dto = _dto(ks_id=1, mode=KeywordStrategyMode.MIN_CPA, target_pfo=500.0)
    adv_state = _adv_state(
        resolve=resolve,
        max_pay_for_order=550.0,
        fact_pay_for_order=fact,
    )
    ctx = UpdateContextManager().from_prepared(
        KeywordsPreparedList(keywords=[dto]),
        adv_state=adv_state,
    )
    executor = RaiseStateToTargetCpoExecutor()
    executor.execute(ctx)
    assert executor.skip_reason is None
    assert dto.current_mode == KeywordStrategyMode.MIN_CPA
    assert dto.next_state == []


@pytest.mark.unit
def test_raise_state_raises_expensive_kw_when_fact_below_stabilization() -> None:
    resolve = 400.0
    fact = raise_state_resolve_stabilization_floor(resolve) - 1.0
    dto = _dto(ks_id=1, mode=KeywordStrategyMode.MIN_CPA, target_pfo=500.0)
    adv_state = _adv_state(
        resolve=500.0,
        max_pay_for_order=550.0,
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
def test_raise_state_runs_when_fact_below_90pct_resolve() -> None:
    """При fact < 90 % resolve фаза R↑ поднимает ключ до OPTIMUM."""
    resolve = 500.0
    fact = raise_state_resolve_stabilization_floor(resolve) - 1.0
    dto = _dto(ks_id=1, mode=KeywordStrategyMode.MIN_CPA)
    adv_state = _adv_state(
        resolve=resolve,
        max_pay_for_order=550.0,
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
def test_raise_state_caps_at_fact_ceiling_on_overspend() -> None:
    """Overspend: подъём только до ступени с cpo < fact (800), не до resolve."""
    cheap = _dto(
        ks_id=1,
        mode=KeywordStrategyMode.MIN_CPA,
        ladder=_ladder_states(1, min_cpo=300.0, opt_cpo=600.0, max_cpo=850.0),
    )
    expensive = _dto(
        ks_id=2,
        mode=KeywordStrategyMode.MIN_CPA,
        ladder=_ladder_states(2, min_cpo=300.0, opt_cpo=850.0, max_cpo=1000.0),
    )
    adv_state = _adv_state(
        resolve=900.0,
        max_pay_for_order=500.0,
        fact_pay_for_order=800.0,
        guard_condition=True,
    )
    ctx = UpdateContextManager().from_prepared(
        KeywordsPreparedList(keywords=[cheap, expensive]),
        adv_state=adv_state,
    )
    RaiseStateToTargetCpoExecutor().execute(ctx)
    assert cheap.current_mode == KeywordStrategyMode.OPTIMUM
    assert expensive.current_mode == KeywordStrategyMode.MIN_CPA
    assert expensive.next_state == []


@pytest.mark.unit
@pytest.mark.parametrize(
    ("mode", "cap", "expected_mode", "expected_place"),
    [
        (
            KeywordStrategyMode.MAX_CONVERSION,
            KeywordStrategyMode.MIN_CPA,
            KeywordStrategyMode.MIN_CPA,
            10,
        ),
        (
            KeywordStrategyMode.OPTIMUM,
            KeywordStrategyMode.MIN_CPA,
            KeywordStrategyMode.MIN_CPA,
            10,
        ),
        (
            KeywordStrategyMode.MAX_CONVERSION,
            KeywordStrategyMode.OPTIMUM,
            KeywordStrategyMode.OPTIMUM,
            20,
        ),
    ],
)
def test_clamp_state_to_aggression_executor_downgrades_above_cap(
    mode: KeywordStrategyMode,
    cap: KeywordStrategyMode,
    expected_mode: KeywordStrategyMode,
    expected_place: int,
) -> None:
    dto = _dto(mode=mode)
    adv_state = replace(
        AdvState.empty(),
        resolve=500.0,
        policy=replace(AdvState.empty().policy, max_target_mode=cap),
    )
    ctx = UpdateContextManager().from_prepared(
        KeywordsPreparedList(keywords=[dto]),
        adv_state=adv_state,
    )
    ClampStateToAggressionExecutor().execute(ctx)
    assert dto.current_mode == expected_mode
    assert dto.target_place == expected_place
    assert dto.next_state[-1].executor_name == "ClampStateToAggressionExecutor"


@pytest.mark.unit
def test_clamp_state_to_aggression_executor_noop_when_already_within_cap() -> None:
    dto = _dto(mode=KeywordStrategyMode.MIN_CPA)
    adv_state = replace(
        AdvState.empty(),
        resolve=500.0,
        policy=replace(
            AdvState.empty().policy,
            max_target_mode=KeywordStrategyMode.OPTIMUM,
        ),
    )
    ctx = UpdateContextManager().from_prepared(
        KeywordsPreparedList(keywords=[dto]),
        adv_state=adv_state,
    )
    ClampStateToAggressionExecutor().execute(ctx)
    assert dto.next_state == []
    assert dto.current_mode == KeywordStrategyMode.MIN_CPA


@pytest.mark.unit
def test_clamp_state_to_aggression_executor_skips_when_cap_state_missing() -> None:
    dto = _dto(
        mode=KeywordStrategyMode.MAX_CONVERSION,
        ladder=_ladder_states(1, min_cpo=None, opt_cpo=400.0, max_cpo=600.0),
    )
    adv_state = replace(
        AdvState.empty(),
        resolve=500.0,
        policy=replace(
            AdvState.empty().policy,
            max_target_mode=KeywordStrategyMode.MIN_CPA,
        ),
    )
    ctx = UpdateContextManager().from_prepared(
        KeywordsPreparedList(keywords=[dto]),
        adv_state=adv_state,
    )
    executor = ClampStateToAggressionExecutor()
    executor.execute(ctx)
    assert executor.skip_reason == "missing_cap_ladder_state"
    assert dto.current_mode == KeywordStrategyMode.MAX_CONVERSION
    assert dto.next_state == []


@pytest.mark.unit
def test_raise_state_executor_in_preamble() -> None:
    executors = build_normal_preamble_executors()
    assert executors[0].phase_name == "validate_state_by_hard_status"
    phases = [executor.phase_name for executor in executors]
    assert phases.index("raise_state_to_target_cpo") == (
        phases.index("skip_up_same_target_place") + 1
    )
