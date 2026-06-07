"""Unit: ResolveCalibrationExecutor, StatesListGenerator (calibration) и runner."""

from __future__ import annotations

from dataclasses import replace

import pytest

from app.modules.common_slaves.wildberries.models.enums import KeywordStrategyMode
from app.modules.shop_runner.service_manager.services.auto_updater_v3.activation_strategy import (
    ShelfClickMode,
)
from app.modules.shop_runner.service_manager.services.auto_updater_v3.calibration_step_resolver import (
    CalibrationDirect,
)
from app.modules.shop_runner.service_manager.services.auto_updater_v3.keyword_v3_eligibility import (
    KeywordDataTier,
    KeywordV3DecisionTier,
    KeywordV3Eligibility,
)
from app.modules.shop_runner.service_manager.services.auto_updater_v3.keyword_v3_ladder_view import (
    LadderInputs,
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
from app.modules.shop_runner.service_manager.services.auto_updater_v3.rollout_aggressiveness import (
    V3RolloutAggressiveness,
)
from app.modules.shop_runner.service_manager.services.auto_updater_v3.selector import (
    KeywordV3Context,
)
from app.modules.shop_runner.service_manager.services.auto_updater_v3.transition_ranking import (
    SelectionPolicy,
)
from app.modules.shop_runner.service_manager.services.auto_updater_v3.update_pipeline.executors import (
    build_normal_preamble_executors,
)
from app.modules.shop_runner.service_manager.services.auto_updater_v3.update_pipeline.executors.resolve_calibration import (
    ResolveCalibrationExecutor,
)
from app.modules.shop_runner.service_manager.services.auto_updater_v3.update_pipeline.executors.states_list_generator import (
    StatesListGenerator,
)
from tests.unit.test_auto_updater_v3 import _calc_kw, _conv_for_pay_for_order


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
    hard_status: int = 2,
    target_place: int | None = None,
    views: int = 100,
) -> KeywordDTO:
    kw = _calc_kw(
        ks_id=ks_id,
        text=f"kw{ks_id}",
        mode=mode,
        rating=1.0,
        hard_status=hard_status,
        views=views,
    )
    states = ladder if ladder is not None else _ladder_states(ks_id)
    if target_place is None:
        for state in states:
            if state.strategy_mode == mode and state.cpo is not None:
                target_place = int(state.target_position)
                break
    if target_place is not None:
        kw.keyword_setting.target_place = target_place
    ctx = KeywordV3Context(keyword=kw, position_profile=None)
    return KeywordDTO.from_context(ctx, ladder_states=states)


def _cal_adv_state(**overrides: object) -> AdvState:
    base = replace(
        AdvState.empty(),
        resolve=500.0,
        resolve_valid=True,
        max_pay_for_order=600.0,
        fact_pay_for_order=400.0,
        plan_fact_equal=False,
        views_equal=False,
        calibration_direct=CalibrationDirect.TIGHTEN,
        max_effective_steps=2,
        policy=SelectionPolicy.from_aggressiveness(
            click_mode=ShelfClickMode.ORGANIC_DOMINANT,
            aggressiveness=V3RolloutAggressiveness.MAX,
        ),
        shelf_click_mode=ShelfClickMode.ORGANIC_DOMINANT,
        aggressiveness=V3RolloutAggressiveness.MAX,
    )
    return replace(base, **overrides)


def _ctx(*keywords: KeywordDTO, adv_state: AdvState | None = None):
    return UpdateContextManager().from_prepared(
        KeywordsPreparedList(keywords=list(keywords)),
        adv_state=adv_state or _cal_adv_state(),
    )


@pytest.mark.unit
@pytest.mark.parametrize(
    ("adv_overrides", "expected_skip"),
    [
        ({"resolve_valid": False}, "resolve_invalid"),
        ({"fact_pay_for_order": 700.0}, "fact_gt_max"),
        (
            {"plan_fact_equal": True, "views_equal": True},
            "plan_fact_unchanged_and_views_unchanged",
        ),
        ({"plan_fact_equal": True}, "plan_fact_unchanged"),
        ({"views_equal": True}, "views_unchanged"),
        ({"calibration_direct": None}, "no_direct"),
    ],
)
def test_calibration_skip_gates(
    adv_overrides: dict[str, object],
    expected_skip: str,
) -> None:
    ctx = _ctx(_dto(), adv_state=_cal_adv_state(**adv_overrides))
    executor = ResolveCalibrationExecutor()
    executor.execute(ctx)
    assert executor.skip_reason == expected_skip
    assert ctx.keywords[0].next_state == []
    assert ctx.adv_state.max_effective_steps == 0
    assert ctx.adv_state.calibration_phase_extra["effective_steps"] == 0


@pytest.mark.unit
def test_calibration_down_max_donor_above_resolve() -> None:
    expensive = _dto(
        ks_id=1,
        mode=KeywordStrategyMode.MAX_CONVERSION,
        ladder=_ladder_states(1, min_cpo=250.0, opt_cpo=400.0, max_cpo=600.0),
        target_place=30,
    )
    ctx = _ctx(expensive, adv_state=_cal_adv_state(resolve=500.0))
    ResolveCalibrationExecutor().execute(ctx)
    assert ctx.keywords[0].current_mode == KeywordStrategyMode.OPTIMUM
    assert len(ctx.keywords[0].next_state) == 1


@pytest.mark.unit
def test_calibration_down_no_op_when_cpo_at_or_below_resolve() -> None:
    cheap = _dto(
        ks_id=1,
        mode=KeywordStrategyMode.MIN_CPA,
        ladder=_ladder_states(1, min_cpo=200.0, opt_cpo=400.0, max_cpo=600.0),
        target_place=10,
    )
    ctx = _ctx(cheap, adv_state=_cal_adv_state(resolve=500.0))
    ResolveCalibrationExecutor().execute(ctx)
    assert ctx.keywords[0].next_state == []


@pytest.mark.unit
def test_calibration_down_no_ch_min_pfo_to_off() -> None:
    kw = _calc_kw(
        ks_id=21,
        text="no_ch_cal",
        mode=KeywordStrategyMode.MIN_CPA,
        rating=1.0,
        conv=_conv_for_pay_for_order(435.0),
        hard_status=2,
    )
    kw = kw.model_copy(
        update={
            "keyword_setting": kw.keyword_setting.model_copy(
                update={"target_place": 10}
            )
        }
    )
    dto = KeywordDTO.from_context(
        KeywordV3Context(keyword=kw, position_profile=None),
        ladder_states=_ladder_states(21, min_cpo=435.0, opt_cpo=500.0, max_cpo=600.0),
    )
    elig = KeywordV3Eligibility(
        data_tier=KeywordDataTier.KEYWORD_NO_CH_PROFILE_WITH_OWN_CONV,
        allowed_modes=frozenset({KeywordStrategyMode.MIN_CPA}),
        max_allowed_mode=KeywordStrategyMode.MIN_CPA,
        participates_in_ladder=True,
        target_place_fallback_zero=True,
        imputed=False,
        fallback_kind="none",
        decision_tier=KeywordV3DecisionTier.FULL,
    )
    adv = _cal_adv_state(
        resolve=300.0,
        eligibility_by_ks_id={21: elig},
    )
    ctx = _ctx(dto, adv_state=adv)
    ResolveCalibrationExecutor().execute(ctx)
    assert ctx.keywords[0].current_mode == KeywordStrategyMode.OFF
    assert len(ctx.keywords[0].next_state) == 1


@pytest.mark.unit
def test_calibration_up_min_from_list2() -> None:
    dto = _dto(
        ks_id=1,
        mode=KeywordStrategyMode.MIN_CPA,
        ladder=_ladder_states(1, min_cpo=300.0, opt_cpo=400.0, max_cpo=600.0),
        target_place=10,
    )
    adv = _cal_adv_state(
        calibration_direct=CalibrationDirect.LOOSEN,
        max_effective_steps=1,
    )
    ctx = _ctx(dto, adv_state=adv)
    ResolveCalibrationExecutor().execute(ctx)
    assert ctx.keywords[0].current_mode == KeywordStrategyMode.OPTIMUM
    assert len(ctx.keywords[0].next_state) == 1


@pytest.mark.unit
def test_calibration_budget_limits_steps() -> None:
    dto = _dto(
        ks_id=1,
        mode=KeywordStrategyMode.MIN_CPA,
        ladder=_ladder_states(1, min_cpo=300.0, opt_cpo=400.0, max_cpo=600.0),
        target_place=10,
    )
    adv = _cal_adv_state(
        calibration_direct=CalibrationDirect.LOOSEN,
        max_effective_steps=2,
    )
    ctx = _ctx(dto, adv_state=adv)
    ResolveCalibrationExecutor().execute(ctx)
    assert ctx.keywords[0].current_mode == KeywordStrategyMode.MAX_CONVERSION
    assert len(ctx.keywords[0].next_state) == 2


@pytest.mark.unit
def test_calibration_up_budget_is_ladder_steps_not_iterations() -> None:
    """Бюджет 2 = два ladder UP; alias MIN→OPT на том же place не считается шагом."""
    dto = _dto(
        ks_id=1,
        mode=KeywordStrategyMode.OFF,
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
                target_position=10,
                cpo=400.0,
            ),
            KeywordV3LadderState(
                keyword_setting_id=1,
                stage=V3LadderStageKind.MAX_CONVERSION,
                strategy_mode=KeywordStrategyMode.MAX_CONVERSION,
                target_position=20,
                cpo=500.0,
            ),
        ),
        target_place=0,
        views=100,
    )
    adv = _cal_adv_state(
        calibration_direct=CalibrationDirect.LOOSEN,
        max_effective_steps=2,
    )
    ctx = _ctx(dto, adv_state=adv)
    ResolveCalibrationExecutor().execute(ctx)
    assert ctx.keywords[0].current_mode == KeywordStrategyMode.MAX_CONVERSION
    assert ctx.keywords[0].current_target_place == 20
    assert len(ctx.keywords[0].next_state) == 3
    assert ctx.adv_state.calibration_phase_extra.get("ladder_steps_done") == 2


@pytest.mark.unit
def test_generator_calibration_includes_off_no_data_in_list2() -> None:
    off_no_data = _dto(
        ks_id=1,
        mode=KeywordStrategyMode.OFF,
        target_place=0,
        views=0,
        ladder=_ladder_states(1),
    )
    off_no_data.calculated_keyword = off_no_data.calculated_keyword.model_copy(
        update={"views": 0, "conv_views_to_orders": 0.0}
    )
    from app.modules.shop_runner.service_manager.services.auto_updater_v3.keyword_v3_eligibility import (
        build_eligibility_map,
    )

    ladder = LadderInputs.from_contexts([off_no_data.context])
    elig = build_eligibility_map(
        ladder.all_contexts,
        campaign_orders_per_cart_7d=ladder.campaign_orders_per_cart_7d,
    )
    adv = _cal_adv_state(
        calibration_direct=CalibrationDirect.LOOSEN,
        eligibility_by_ks_id=elig,
        ladder_inputs=ladder,
    )
    std_gen = StatesListGenerator(adv, for_calibration=False)
    cal_gen = StatesListGenerator(adv, for_calibration=True)
    _c1, pot_std = std_gen.get_current_states([off_no_data])
    _c2, pot_cal = cal_gen.get_current_states([off_no_data])
    assert len(pot_cal) >= 1
    assert any(
        item[1].strategy_mode == KeywordStrategyMode.MIN_CPA for item in pot_cal
    )


@pytest.mark.unit
def test_calibration_executor_in_preamble() -> None:
    phases = [e.phase_name for e in build_normal_preamble_executors()]
    assert "resolve_calibration" in phases
