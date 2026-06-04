"""Unit: preamble CPA gates — COST_REALLOCATION vs MAX_CPA_GUARD, OVERSPEND selector."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.modules.shop_runner.service_manager.old_modules.setting_auto_updater_v2.adv_control_system.sales_state.sales_states import (
    SalesStates,
)
from app.modules.shop_runner.service_manager.old_modules.setting_auto_updater.data_classes import (
    FactData,
    PlanData,
)
from app.modules.shop_runner.service_manager.services.auto_updater_v3.calibration_step_resolver import (
    CalibrationDirect,
)
from app.modules.shop_runner.service_manager.services.auto_updater_v3.orchestrator import (
    process_adv_v3,
)
from app.modules.shop_runner.service_manager.services.auto_updater_v3.resolve_threshold import (
    compute_resolve_cost_threshold,
    is_resolve_valid,
)
from app.modules.common_slaves.wildberries.models.fact_methods_enum import (
    FactMethods,
)


@pytest.mark.unit
@pytest.mark.asyncio
async def test_process_adv_v3_runs_selector_when_plan_fact_equal_overspend() -> None:
    complex_adv = MagicMock()
    complex_adv.adv_id = 10
    complex_adv.adv_setting = MagicMock()
    complex_adv.shelf_promotion_active = False
    complex_adv.individual_keywords_target_place_mode = False
    complex_adv.v3_rollout_aggressiveness = 2
    complex_adv.keyword_calibration_max_step = 8
    complex_adv.get_keywords = AsyncMock(return_value=[])

    dto = MagicMock()
    dto.min_target_position = 5

    predictor = MagicMock()
    predictor.get_keyword_bid_profiles = AsyncMock(return_value={})

    wb_manager = MagicMock()
    wb_manager.get_wb_advs_dto = AsyncMock(return_value=[dto])

    plan_fact = MagicMock()
    plan_fact.check_equal_in_cache = AsyncMock(return_value=True)
    plan_fact.set_new_plan_fact = AsyncMock()
    views_cache = MagicMock()
    views_cache.get_cached_views = AsyncMock(return_value=100)
    views_cache.set_views = AsyncMock()

    select_mock = MagicMock(return_value=[])

    with (
        patch(
            "app.modules.shop_runner.service_manager.services.auto_updater_v3.data_update_manager.manager.load_v3_wb_context",
            new=AsyncMock(return_value=(dto, {})),
        ),
        patch(
            "app.modules.shop_runner.service_manager.services.auto_updater_v3.data_update_manager.manager.AdvSettingAutoUpdater.get_plan_data",
            return_value=MagicMock(max_pay_for_order=100.0, orders=10, target_pay_for_order=80.0),
        ),
        patch(
            "app.modules.shop_runner.service_manager.services.auto_updater_v3.data_update_manager.manager.AdvSettingAutoUpdater"
        ) as updater_cls,
        patch(
            "app.modules.shop_runner.service_manager.services.auto_updater_v3.data_update_manager.manager.ChangePlanFact",
            return_value=plan_fact,
        ),
        patch(
            "app.modules.shop_runner.service_manager.services.auto_updater_v3.data_update_manager.manager.ChangePlanFactViews",
            return_value=views_cache,
        ),
        patch(
            "app.modules.shop_runner.service_manager.services.auto_updater_v3.data_update_manager.manager.resolve_complex_adv_total_views",
            new=AsyncMock(return_value=100),
        ),
        patch(
            "app.modules.shop_runner.service_manager.services.auto_updater_v3.data_update_manager.manager.detect_campaign_state",
            return_value=SalesStates.OVERSPEND,
        ),
        patch(
            "app.modules.shop_runner.service_manager.services.auto_updater_v3.update_pipeline.executors.cost_reallocation.RebalanceExecutor.execute",
            return_value=None,
        ),
        patch(
            "app.modules.shop_runner.service_manager.services.auto_updater_v3.update_pipeline.executors.resolve_calibration.ResolveCalibrationExecutor.execute",
            return_value=None,
        ),
        patch(
            "app.modules.shop_runner.service_manager.services.auto_updater_v3.apply_manager.manager.select_v3_post_gate_actions",
            select_mock,
        ),
        patch(
            "app.modules.shop_runner.service_manager.services.auto_updater_v3.tick_ledger.V3TickKeywordLedger.flush_to_db",
            new=AsyncMock(return_value=False),
        ),
        patch(
            "app.modules.shop_runner.service_manager.services.auto_updater_v3.data_update_manager.manager.V3CalibrationStepState",
        ) as step_cls,
    ):
        step_cls.return_value.get_state = AsyncMock(return_value=None)
        step_cls.return_value.set_state = AsyncMock()
        updater_cls.return_value.get_fact_data = AsyncMock(
            return_value=MagicMock(pay_for_order=150.0, predict_orders=5)
        )
        await process_adv_v3(complex_adv, wb_shop_data_manager=wb_manager)

    select_mock.assert_called_once()
    plan_fact.set_new_plan_fact.assert_awaited_once()
    views_cache.set_views.assert_awaited_once_with(100)


@pytest.mark.unit
@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("plan_fact_equal", "cached_views", "current_views", "expect_calibration"),
    [
        (True, 100, 100, False),
        (False, 100, 100, False),
        (True, 100, 200, False),
        (False, 100, 200, True),
    ],
)
async def test_calibration_trim_and_gate_plan_fact_views(
    plan_fact_equal: bool,
    cached_views: int | None,
    current_views: int,
    expect_calibration: bool,
) -> None:
    """AND-gate: calibration только если plan/fact и views оба изменились."""
    plan = _plan_for_cpa_gates()
    fact = _fact_for_cpa_gates(pay_for_order=85.0)
    resolve = compute_resolve_cost_threshold(plan, fact)
    assert float(fact.pay_for_order) >= 0.9 * float(resolve)
    assert float(fact.pay_for_order) <= float(plan.max_pay_for_order)

    _, cal_up, cal_down, _, _, _ = await _run_preamble_with_fact_cpa(
        pay_for_order=85.0,
        plan_fact_equal=plan_fact_equal,
        cached_views=cached_views,
        current_views=current_views,
    )

    if expect_calibration:
        cal_down.assert_called_once()
        cal_up.assert_not_called()
    else:
        cal_up.assert_not_called()
        cal_down.assert_not_called()


@pytest.mark.unit
def test_resolve_zero_invalid_when_target_pay_is_zero() -> None:
    """target=0 и predict_orders >= plan.orders → resolve=0, is_resolve_valid False."""
    plan = PlanData(orders=10, target_pay_for_order=0.0, max_pay_for_order=100.0)
    fact = FactData(
        predict_orders=10.0,
        pay_for_order=150.0,
        original_orders=10,
        fact_method=FactMethods.DIRECT_SALES,
    )
    resolve = compute_resolve_cost_threshold(plan, fact)
    assert resolve == 0.0
    assert not is_resolve_valid(plan, resolve)
    assert float(fact.pay_for_order) > float(plan.max_pay_for_order)


def _plan_for_cpa_gates() -> PlanData:
    return PlanData(
        orders=10,
        target_pay_for_order=80.0,
        max_pay_for_order=100.0,
    )


def _fact_for_cpa_gates(*, pay_for_order: float) -> FactData:
    return FactData(
        predict_orders=10.0,
        pay_for_order=pay_for_order,
        original_orders=10,
        fact_method=FactMethods.DIRECT_SALES,
    )


async def _run_preamble_with_fact_cpa(
    *,
    pay_for_order: float,
    plan_fact_equal: bool = False,
    cached_views: int | None = 100,
    current_views: int = 200,
) -> tuple[MagicMock, MagicMock, MagicMock, MagicMock, MagicMock, MagicMock]:
    """NORMAL preamble: моки realloc/calibration/step cache, fact CPA = ``pay_for_order``."""
    plan = _plan_for_cpa_gates()
    fact = _fact_for_cpa_gates(pay_for_order=pay_for_order)
    resolve = compute_resolve_cost_threshold(plan, fact)
    assert is_resolve_valid(plan, resolve)

    complex_adv = MagicMock()
    complex_adv.adv_id = 30
    complex_adv.adv_setting = MagicMock()
    complex_adv.shelf_promotion_active = False
    complex_adv.individual_keywords_target_place_mode = False
    complex_adv.v3_rollout_aggressiveness = 2
    complex_adv.keyword_calibration_max_step = 8
    complex_adv.get_keywords = AsyncMock(return_value=[])

    dto = MagicMock()
    realloc = MagicMock(return_value=[])
    cal_up = MagicMock()
    cal_down = MagicMock()
    guard = MagicMock(return_value=[])  # legacy placeholder (max_cpa_guard removed)

    views_cache = MagicMock()
    views_cache.get_cached_views = AsyncMock(return_value=cached_views)
    views_cache.set_views = AsyncMock()
    step_cache = MagicMock()
    step_cache.get_state = AsyncMock(return_value=None)
    step_cache.set_state = AsyncMock()

    with (
        patch(
            "app.modules.shop_runner.service_manager.services.auto_updater_v3.data_update_manager.manager.load_v3_wb_context",
            new=AsyncMock(return_value=(dto, {})),
        ),
        patch(
            "app.modules.shop_runner.service_manager.services.auto_updater_v3.data_update_manager.manager.build_keyword_v3_contexts",
            return_value=[],
        ),
        patch(
            "app.modules.shop_runner.service_manager.services.auto_updater_v3.update_pipeline.executors.pay_for_order_gap_enable.PayForOrderGapEnableExecutor.execute",
            return_value=[],
        ),
        patch(
            "app.modules.shop_runner.service_manager.services.auto_updater_v3.update_pipeline.executors.pay_for_order_over_max_off_on_deep_overspend.PayForOrderOverMaxOffOnDeepOverspendExecutor.execute",
            return_value=[],
        ),
        patch(
            "app.modules.shop_runner.service_manager.services.auto_updater_v3.data_update_manager.manager.AdvSettingAutoUpdater"
        ) as updater_cls,
        patch(
            "app.modules.shop_runner.service_manager.services.auto_updater_v3.update_pipeline.executors.cost_reallocation.RebalanceExecutor.execute",
            realloc,
        ),
        patch(
            "app.modules.shop_runner.service_manager.services.auto_updater_v3.update_pipeline.executors.resolve_calibration.run_calibration_up",
            cal_up,
        ),
        patch(
            "app.modules.shop_runner.service_manager.services.auto_updater_v3.update_pipeline.executors.resolve_calibration.run_calibration_down",
            cal_down,
        ),
        patch(
            "app.modules.shop_runner.service_manager.services.auto_updater_v3.apply_manager.manager.select_v3_post_gate_actions",
            return_value=[],
        ),
        patch(
            "app.modules.shop_runner.service_manager.services.auto_updater_v3.data_update_manager.manager.ChangePlanFact"
        ) as pfc_cls,
        patch(
            "app.modules.shop_runner.service_manager.services.auto_updater_v3.data_update_manager.manager.ChangePlanFactViews",
            return_value=views_cache,
        ),
        patch(
            "app.modules.shop_runner.service_manager.services.auto_updater_v3.data_update_manager.manager.resolve_complex_adv_total_views",
            new=AsyncMock(return_value=current_views),
        ),
        patch(
            "app.modules.shop_runner.service_manager.services.auto_updater_v3.data_update_manager.manager.V3CalibrationStepState",
            return_value=step_cache,
        ),
        patch(
            "app.modules.shop_runner.service_manager.services.auto_updater_v3.tick_ledger.V3TickKeywordLedger.flush_to_db",
            new=AsyncMock(return_value=False),
        ),
    ):
        plan_fact = MagicMock()
        plan_fact.check_equal_in_cache = AsyncMock(return_value=plan_fact_equal)
        plan_fact.set_new_plan_fact = AsyncMock()
        pfc_cls.return_value = plan_fact
        updater_cls.get_plan_data.return_value = plan
        updater_cls.return_value.get_fact_data = AsyncMock(return_value=fact)
        await process_adv_v3(complex_adv, wb_shop_data_manager=MagicMock())

    return realloc, cal_up, cal_down, plan_fact, views_cache, step_cache


@pytest.mark.unit
@pytest.mark.asyncio
async def test_calibration_step_cache_not_updated_when_calibration_skipped() -> None:
    """Пропуск calibration (unchanged plan/fact и views) — Redis step state не пишется."""
    _, cal_up, cal_down, _, _, step_cache = await _run_preamble_with_fact_cpa(
        pay_for_order=50.0,
        plan_fact_equal=True,
        cached_views=100,
        current_views=100,
    )
    cal_up.assert_not_called()
    cal_down.assert_not_called()
    step_cache.set_state.assert_not_awaited()


@pytest.mark.unit
@pytest.mark.asyncio
async def test_calibration_trim_passes_max_effective_steps_from_resolver() -> None:
    """При calibration gate planner получает ``max_effective_steps`` из resolver."""
    plan = _plan_for_cpa_gates()
    fact = _fact_for_cpa_gates(pay_for_order=85.0)

    complex_adv = MagicMock()
    complex_adv.adv_id = 31
    complex_adv.adv_setting = MagicMock()
    complex_adv.shelf_promotion_active = False
    complex_adv.individual_keywords_target_place_mode = False
    complex_adv.v3_rollout_aggressiveness = 2
    complex_adv.keyword_calibration_max_step = 8
    complex_adv.get_keywords = AsyncMock(return_value=[])

    dto = MagicMock()
    cal_up = MagicMock()
    cal_down = MagicMock()

    with (
        patch(
            "app.modules.shop_runner.service_manager.services.auto_updater_v3.data_update_manager.manager.load_v3_wb_context",
            new=AsyncMock(return_value=(dto, {})),
        ),
        patch(
            "app.modules.shop_runner.service_manager.services.auto_updater_v3.data_update_manager.manager.build_keyword_v3_contexts",
            return_value=[],
        ),
        patch(
            "app.modules.shop_runner.service_manager.services.auto_updater_v3.update_pipeline.executors.pay_for_order_gap_enable.PayForOrderGapEnableExecutor.execute",
            return_value=[],
        ),
        patch(
            "app.modules.shop_runner.service_manager.services.auto_updater_v3.update_pipeline.executors.pay_for_order_over_max_off_on_deep_overspend.PayForOrderOverMaxOffOnDeepOverspendExecutor.execute",
            return_value=[],
        ),
        patch(
            "app.modules.shop_runner.service_manager.services.auto_updater_v3.data_update_manager.manager.AdvSettingAutoUpdater"
        ) as updater_cls,
        patch(
            "app.modules.shop_runner.service_manager.services.auto_updater_v3.update_pipeline.executors.cost_reallocation.RebalanceExecutor.execute",
            return_value=None,
        ),
        patch(
            "app.modules.shop_runner.service_manager.services.auto_updater_v3.update_pipeline.executors.resolve_calibration.run_calibration_up",
            cal_up,
        ),
        patch(
            "app.modules.shop_runner.service_manager.services.auto_updater_v3.update_pipeline.executors.resolve_calibration.run_calibration_down",
            cal_down,
        ),
        patch(
            "app.modules.shop_runner.service_manager.services.auto_updater_v3.apply_manager.manager.select_v3_post_gate_actions",
            return_value=[],
        ),
        patch(
            "app.modules.shop_runner.service_manager.services.auto_updater_v3.data_update_manager.manager.ChangePlanFact"
        ) as pfc_cls,
        patch(
            "app.modules.shop_runner.service_manager.services.auto_updater_v3.data_update_manager.manager.ChangePlanFactViews"
        ) as views_cls,
        patch(
            "app.modules.shop_runner.service_manager.services.auto_updater_v3.data_update_manager.manager.resolve_complex_adv_total_views",
            new=AsyncMock(return_value=200),
        ),
        patch(
            "app.modules.shop_runner.service_manager.services.auto_updater_v3.data_update_manager.manager.V3CalibrationStepState"
        ) as step_cls,
        patch(
            "app.modules.shop_runner.service_manager.services.auto_updater_v3.data_update_manager.manager.resolve_effective_calibration_steps",
            return_value=4,
        ) as resolve_steps,
        patch(
            "app.modules.shop_runner.service_manager.services.auto_updater_v3.tick_ledger.V3TickKeywordLedger.flush_to_db",
            new=AsyncMock(return_value=False),
        ),
    ):
        plan_fact = MagicMock()
        plan_fact.check_equal_in_cache = AsyncMock(return_value=False)
        plan_fact.set_new_plan_fact = AsyncMock()
        pfc_cls.return_value = plan_fact
        views_cls.return_value.get_cached_views = AsyncMock(return_value=100)
        views_cls.return_value.set_views = AsyncMock()
        step_cls.return_value.get_state = AsyncMock(return_value=None)
        step_cls.return_value.set_state = AsyncMock()
        updater_cls.get_plan_data.return_value = plan
        updater_cls.return_value.get_fact_data = AsyncMock(return_value=fact)
        await process_adv_v3(complex_adv, wb_shop_data_manager=MagicMock())

    resolve_steps.assert_called_once()
    cal_down.assert_called_once()
    assert cal_down.call_args.kwargs.get("max_steps") == 4
    step_mock = step_cls.return_value
    step_mock.set_state.assert_awaited_once()
    saved = step_mock.set_state.await_args[0][0]
    assert saved.effective_steps == 4


@pytest.mark.unit
@pytest.mark.asyncio
async def test_cost_reallocation_runs_when_resolve_valid() -> None:
    """При valid resolve realloc вызывается каждый NORMAL-тик."""
    plan = _plan_for_cpa_gates()
    fact = _fact_for_cpa_gates(pay_for_order=50.0)
    resolve = compute_resolve_cost_threshold(plan, fact)
    assert float(fact.pay_for_order) < 0.9 * float(resolve)

    realloc, cal_up, cal_down, _, _, step_cache = await _run_preamble_with_fact_cpa(
        pay_for_order=50.0
    )
    step_cache.set_state.assert_awaited_once()

    realloc.assert_called_once()
    cal_up.assert_called_once()
    cal_down.assert_not_called()


@pytest.mark.unit
@pytest.mark.asyncio
async def test_cost_reallocation_and_calibration_in_stabilization_zone() -> None:
    """``0.9 * resolve <= fact <= max`` — realloc + calibration (plan/views changed)."""
    plan = _plan_for_cpa_gates()
    fact = _fact_for_cpa_gates(pay_for_order=85.0)
    resolve = compute_resolve_cost_threshold(plan, fact)
    assert float(fact.pay_for_order) >= 0.9 * float(resolve)
    assert float(fact.pay_for_order) <= float(plan.max_pay_for_order)

    realloc, cal_up, cal_down, _, _, step_cache = await _run_preamble_with_fact_cpa(
        pay_for_order=85.0,
        plan_fact_equal=False,
        cached_views=100,
        current_views=200,
    )

    realloc.assert_called_once()
    cal_down.assert_called_once()
    cal_up.assert_not_called()
    step_cache.set_state.assert_awaited_once()


@pytest.mark.unit
@pytest.mark.asyncio
async def test_resolve_calibration_loosen_when_fact_below_ninety_percent_resolve() -> None:
    """``fact < 0.9 * resolve`` — realloc + calibration LOOSEN (plan/views changed)."""
    plan = _plan_for_cpa_gates()
    fact = _fact_for_cpa_gates(pay_for_order=50.0)
    resolve = compute_resolve_cost_threshold(plan, fact)
    assert float(fact.pay_for_order) < 0.9 * float(resolve)

    realloc, cal_up, cal_down, _, _, _ = await _run_preamble_with_fact_cpa(
        pay_for_order=50.0,
        plan_fact_equal=False,
        cached_views=100,
        current_views=200,
    )

    realloc.assert_called_once()
    cal_up.assert_called_once()
    cal_down.assert_not_called()


@pytest.mark.unit
@pytest.mark.asyncio
async def test_resolve_calibration_skipped_when_fact_above_max() -> None:
    """``fact > max`` — calibration skip (fact_gt_max), realloc может выполниться."""
    plan = _plan_for_cpa_gates()
    fact = _fact_for_cpa_gates(pay_for_order=150.0)
    resolve = compute_resolve_cost_threshold(plan, fact)
    assert float(fact.pay_for_order) > float(plan.max_pay_for_order)

    realloc, cal_up, cal_down, _, _, step_cache = await _run_preamble_with_fact_cpa(
        pay_for_order=150.0
    )

    realloc.assert_called_once()
    cal_up.assert_not_called()
    cal_down.assert_not_called()
    step_cache.set_state.assert_not_awaited()
