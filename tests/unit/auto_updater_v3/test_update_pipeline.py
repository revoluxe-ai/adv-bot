"""Unit: UpdatePipeline и executors."""

from __future__ import annotations

import pytest

from app.modules.common_slaves.wildberries.models.enums import KeywordStrategyMode
from app.modules.common_slaves.wildberries.models.fact_methods_enum import FactMethods
from app.modules.shop_runner.service_manager.old_modules.setting_auto_updater.data_classes import (
    FactData,
    PlanData,
)
from app.modules.shop_runner.service_manager.services.auto_updater_v3.activation_strategy import (
    ShelfClickMode,
)
from app.modules.shop_runner.service_manager.services.auto_updater_v3.calibration_step_resolver import (
    CalibrationDirect,
)
from app.modules.shop_runner.service_manager.services.auto_updater_v3.keyword_dto import (
    UpdateContext,
    UpdateContextInput,
    UpdateContextManager,
    build_update_context,
)
from app.modules.shop_runner.service_manager.services.auto_updater_v3.rollout_aggressiveness import (
    V3RolloutAggressiveness,
)
from app.modules.shop_runner.service_manager.services.auto_updater_v3.selector import (
    KeywordV3Context,
)
from app.modules.shop_runner.service_manager.services.auto_updater_v3.update_pipeline import (
    UpdatePipeline,
    build_normal_preamble_executors,
)
from app.modules.shop_runner.service_manager.services.auto_updater_v3.update_pipeline.executors.not_full_validate import (
    NotFullValidateExecutor,
)
from tests.unit.test_auto_updater_v3 import _calc_kw


def _ctx(ks_id: int, *, mode: KeywordStrategyMode = KeywordStrategyMode.MAX_CONVERSION) -> KeywordV3Context:
    kw = _calc_kw(
        ks_id=ks_id,
        text=f"kw{ks_id}",
        mode=mode,
        rating=1.0,
        hard_status=2,
    )
    return KeywordV3Context(keyword=kw, position_profile=None)


def _legacy_context(**adv_overrides: object) -> UpdateContext:
    from app.modules.shop_runner.service_manager.services.auto_updater_v3.keyword_v3_ladder_view import (
        LadderInputs,
    )
    from app.modules.shop_runner.service_manager.services.auto_updater_v3.keyword_dto import (
        AdvState,
    )
    from app.modules.shop_runner.service_manager.services.auto_updater_v3.transition_ranking import (
        SelectionPolicy,
    )

    contexts = [_ctx(1)]
    ladder = LadderInputs.from_contexts(contexts)
    base = dict(
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
        calibration_phase_extra={"calibration_direct": "loosen"},
    )
    base.update(adv_overrides)
    adv_state = AdvState(**base)  # type: ignore[arg-type]
    return build_update_context(contexts, adv_state=adv_state)


@pytest.mark.unit
def test_update_pipeline_mutates_context_in_place() -> None:
    ctx = _legacy_context()
    executor = NotFullValidateExecutor()
    pipeline = UpdatePipeline([executor])
    result_ctx = pipeline.update(ctx)
    assert result_ctx is ctx


@pytest.mark.unit
def test_context_manager_build_from_plan_fact() -> None:
    kw = _calc_kw(ks_id=1, text="kw1", mode=KeywordStrategyMode.MIN_CPA, rating=1.0)
    tick_input = UpdateContextInput(
        keywords=[kw],
        plan=PlanData(orders=1, target_pay_for_order=100, max_pay_for_order=200),
        fact=FactData(
            predict_orders=1.0,
            original_orders=1.0,
            pay_for_order=50.0,
            fact_method=FactMethods.DIRECT_SALES,
        ),
        raw_profiles={},
    )
    ctx = UpdateContextManager().build(tick_input)
    assert isinstance(ctx, UpdateContext)
    assert ctx.adv_state.fact_pay_for_order == 50.0


@pytest.mark.unit
def test_executor_sets_skip_reason() -> None:
    from app.modules.shop_runner.service_manager.services.auto_updater_v3.update_pipeline.executors.pay_for_order_gap_enable import (
        PayForOrderGapEnableExecutor,
    )

    ctx = _legacy_context(resolve=0.0, resolve_valid=False)
    executor = PayForOrderGapEnableExecutor()
    executor.execute(ctx)
    assert executor.skip_reason == "resolve_invalid"


@pytest.mark.unit
def test_build_normal_preamble_executors_order() -> None:
    names = [ex.phase_name for ex in build_normal_preamble_executors()]
    assert names == [
        "validate_state_by_hard_status",
        "validate_not_full_state",
        "not_full_target_place_migrate",
        "not_full_target_place_overspend_reset",
        "not_full_target_place_plan_fact",
        "skip_up_same_target_place",
        "raise_state_to_target_cpo",
        "reset_over_max_cpo_on_overspend",
        "shelf_cleanup",
        "cost_reallocation",
        "pay_for_order_gap_enable",
        "pay_for_order_over_max_off_on_deep_overspend",
        "resolve_calibration",
    ]
