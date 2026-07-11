# pyright: reportPrivateUsage=false
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
from app.modules.shop_runner.service_manager.services.auto_updater_v3.activation_strategy import (
    ShelfClickMode,
)
from app.modules.shop_runner.service_manager.services.auto_updater_v3.rollout_aggressiveness import (
    V3RolloutAggressiveness,
)
from app.modules.shop_runner.service_manager.services.auto_updater_v3.transition_ranking import (
    SelectionPolicy,
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
from tests.unit.test_auto_updater_v3 import (  # pyright: ignore[reportPrivateUsage]
    _calc_kw,
    _conv_for_pay_for_order,
    _sample_profile,
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


def _adv_state(*, fact: float, max_cpo: float = 550.0, guard_condition: bool = False) -> AdvState:
    use_raise_max = float(fact) > float(max_cpo)
    return replace(
        AdvState.empty(),
        resolve=500.0,
        max_pay_for_order=max_cpo,
        fact_pay_for_order=fact,
        resolve_valid=True,
        guard_condition=guard_condition,
        v3_substitute_fact_cpo_for_max=use_raise_max,
    )


def _adv_state_custom(
    *,
    resolve: float,
    fact: float | None,
    max_cpo: float = 550.0,
    guard_condition: bool = False,
    use_raise_max: bool | None = None,
) -> AdvState:
    """Build a mutable AdvState for characterization tests with explicit resolve."""
    if use_raise_max is None:
        use_raise_max = fact is not None and float(fact) > float(max_cpo)
    return replace(
        AdvState.empty(),
        resolve=resolve,
        max_pay_for_order=max_cpo,
        fact_pay_for_order=fact,
        resolve_valid=True,
        guard_condition=guard_condition,
        v3_substitute_fact_cpo_for_max=use_raise_max,
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
    adv_at = _adv_state(fact=floor + 0.01, max_cpo=max_cpo)
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
def test_exact_threshold_is_currently_noop_for_eligible_keyword() -> None:
    max_cpo = 550.0
    fact = pfo_off_plan_headroom_floor(max_cpo)
    dto = _dto(pfo_target=600.0)
    ctx = _context([dto], _adv_state(fact=fact, max_cpo=max_cpo))

    PayForOrderOverMaxOffOnDeepOverspendExecutor().execute(ctx)

    assert dto.current_mode == KeywordStrategyMode.MIN_CPA
    assert dto.next_state == []


@pytest.mark.unit
def test_fact_just_above_threshold_keeps_already_off_keyword_unchanged() -> None:
    max_cpo = 550.0
    fact = pfo_off_plan_headroom_floor(max_cpo) + 0.01
    dto = _dto(mode=KeywordStrategyMode.OFF, pfo_target=600.0)
    ctx = _context([dto], _adv_state(fact=fact, max_cpo=max_cpo))

    PayForOrderOverMaxOffOnDeepOverspendExecutor().execute(ctx)

    assert dto.current_mode == KeywordStrategyMode.OFF
    assert dto.next_state == []


@pytest.mark.unit
def test_fact_above_threshold_noop_when_keyword_has_no_off_candidate() -> None:
    max_cpo = 550.0
    fact = pfo_off_plan_headroom_floor(max_cpo) + 0.01
    ks_id = 177
    dto = KeywordDTO.from_context(
        KeywordV3Context(
            keyword=_calc_kw(
                ks_id=ks_id,
                text="kw177",
                mode=KeywordStrategyMode.MIN_CPA,
                rating=1.0,
                hard_status=2,
                conv=_conv_for_pay_for_order(600.0),
            ),
            position_profile=_sample_profile(),
        ),
        ladder_states=(
            KeywordV3LadderState(
                keyword_setting_id=ks_id,
                stage=V3LadderStageKind.MIN_CPA,
                strategy_mode=KeywordStrategyMode.MIN_CPA,
                target_position=10,
                cpo=600.0,
            ),
        ),
    )
    ctx = _context([dto], _adv_state(fact=fact, max_cpo=max_cpo))

    PayForOrderOverMaxOffOnDeepOverspendExecutor().execute(ctx)

    assert dto.current_mode == KeywordStrategyMode.MIN_CPA
    assert dto.next_state == []


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
    fact = pfo_off_plan_headroom_floor(max_cpo) + 0.01
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
def test_overspend_off_only_expensive_above_fact() -> None:
    """При overspend OFF только ключи с PFO > fact (800), не plan.max (500)."""
    cheap = _dto(ks_id=1, pfo_target=600.0)
    expensive = _dto(ks_id=2, pfo_target=850.0)
    ctx = _context(
        [cheap, expensive],
        _adv_state(fact=800.0, max_cpo=500.0, guard_condition=True),
    )
    PayForOrderOverMaxOffOnDeepOverspendExecutor().execute(ctx)
    assert cheap.current_mode == KeywordStrategyMode.MIN_CPA
    assert expensive.current_mode == KeywordStrategyMode.OFF


@pytest.mark.unit
def test_overspend_uses_fact_ceiling_and_offs_only_when_above_fact() -> None:
    max_cpo = 500.0
    fact = 800.0
    cheap = _dto(ks_id=1, pfo_target=600.0)
    expensive = _dto(ks_id=2, pfo_target=850.0)
    ctx = _context(
        [cheap, expensive],
        _adv_state(fact=fact, max_cpo=max_cpo, guard_condition=True),
    )

    PayForOrderOverMaxOffOnDeepOverspendExecutor().execute(ctx)

    assert cheap.current_mode == KeywordStrategyMode.MIN_CPA
    assert cheap.next_state == []
    assert expensive.current_mode == KeywordStrategyMode.OFF
    assert len(expensive.next_state) == 1


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
    adv = _adv_state(fact=700.0, max_cpo=max_cpo, guard_condition=False)
    adv = replace(adv, resolve=800.0)
    adv = replace(
        adv,
        policy=SelectionPolicy.from_aggressiveness(
            click_mode=ShelfClickMode.ORGANIC_DOMINANT,
            aggressiveness=V3RolloutAggressiveness.MAX,
        ),
    )
    ctx = _context([dto], adv)
    RaiseStateToTargetCpoExecutor().execute(ctx)
    assert dto.current_mode == KeywordStrategyMode.MAX_CONVERSION
    PayForOrderOverMaxOffOnDeepOverspendExecutor().execute(ctx)
    assert dto.current_mode == KeywordStrategyMode.MAX_CONVERSION
    assert len(dto.next_state) == 1


@pytest.mark.unit
def test_resolve_change_does_not_affect_executor_result() -> None:
    max_cpo = 550.0
    fact = pfo_off_plan_headroom_floor(max_cpo) + 0.01
    dto_low_resolve = _dto(pfo_target=600.0)
    dto_high_resolve = _dto(ks_id=2, pfo_target=600.0)
    ctx_low = _context(
        [dto_low_resolve],
        _adv_state_custom(resolve=100.0, fact=fact, max_cpo=max_cpo),
    )
    ctx_high = _context(
        [dto_high_resolve],
        _adv_state_custom(resolve=9999.0, fact=fact, max_cpo=max_cpo),
    )

    executor_low = PayForOrderOverMaxOffOnDeepOverspendExecutor()
    executor_high = PayForOrderOverMaxOffOnDeepOverspendExecutor()
    executor_low.execute(ctx_low)
    executor_high.execute(ctx_high)

    assert dto_low_resolve.current_mode == KeywordStrategyMode.OFF
    assert dto_high_resolve.current_mode == KeywordStrategyMode.OFF
    assert dto_low_resolve.current_target_place == 0
    assert dto_high_resolve.current_target_place == 0
    assert len(dto_low_resolve.next_state) == 1
    assert len(dto_high_resolve.next_state) == 1


@pytest.mark.unit
def test_empty_keyword_list_is_noop() -> None:
    ctx = _context([], _adv_state(fact=800.0, max_cpo=500.0, guard_condition=True))

    PayForOrderOverMaxOffOnDeepOverspendExecutor().execute(ctx)

    assert ctx.keywords == []


@pytest.mark.unit
def test_none_fact_pay_for_order_skips_without_actions() -> None:
    adv = _adv_state_custom(resolve=500.0, fact=None, max_cpo=550.0)
    ctx = _context([_dto()], adv)

    executor = PayForOrderOverMaxOffOnDeepOverspendExecutor()
    executor.execute(ctx)

    assert executor.skip_reason == "no_fact_pay_for_order"
    assert ctx.keywords[0].next_state == []


@pytest.mark.unit
def test_non_positive_max_pay_for_order_uses_existing_gate_behavior() -> None:
    adv = _adv_state_custom(resolve=500.0, fact=610.0, max_cpo=0.0, use_raise_max=False)
    ctx = _context([_dto()], adv)

    PayForOrderOverMaxOffOnDeepOverspendExecutor().execute(ctx)

    assert ctx.keywords[0].current_mode == KeywordStrategyMode.MIN_CPA
    assert ctx.keywords[0].next_state == []


@pytest.mark.unit
def test_pfo_off_in_preamble_order() -> None:
    phases = [ex.phase_name for ex in build_normal_preamble_executors()]
    idx_enable = phases.index("pay_for_order_gap_enable")
    idx_off = phases.index("pay_for_order_over_max_off_on_deep_overspend")
    idx_cal = phases.index("resolve_calibration")
    assert idx_off == idx_enable + 1
    assert idx_cal == idx_off + 1
