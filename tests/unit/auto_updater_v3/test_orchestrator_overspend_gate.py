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
from app.modules.shop_runner.service_manager.services.auto_updater_v3.orchestrator import (
    process_adv_v3,
)
from app.modules.plan_fact.provider import PlanFactProvider
from app.modules.shop_runner.service_manager.services.auto_updater_v3.rollout_planner import (
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

    select_mock = MagicMock(return_value=[])

    with (
        patch(
            "app.modules.shop_runner.service_manager.services.auto_updater_v3.orchestrator._load_v3_wb_context",
            new=AsyncMock(return_value=(dto, {})),
        ),
        patch(
            "app.modules.shop_runner.service_manager.services.auto_updater_v3.orchestrator.AdvSettingAutoUpdater.get_plan_data",
            return_value=MagicMock(max_pay_for_order=100.0, orders=10, target_pay_for_order=80.0),
        ),
        patch(
            "app.modules.shop_runner.service_manager.services.auto_updater_v3.orchestrator.AdvSettingAutoUpdater"
        ) as updater_cls,
        patch(
            "app.modules.shop_runner.service_manager.services.auto_updater_v3.orchestrator.ChangePlanFact",
            return_value=plan_fact,
        ),
        patch(
            "app.modules.shop_runner.service_manager.services.auto_updater_v3.orchestrator.detect_campaign_state",
            return_value=SalesStates.OVERSPEND,
        ),
        patch(
            "app.modules.shop_runner.service_manager.services.auto_updater_v3.orchestrator.plan_data_bootstrap_v3",
            return_value=[],
        ),
        patch(
            "app.modules.shop_runner.service_manager.services.auto_updater_v3.orchestrator.plan_cost_reallocation",
            return_value=[],
        ),
        patch(
            "app.modules.shop_runner.service_manager.services.auto_updater_v3.orchestrator.plan_resolve_calibration_trim",
            return_value=[],
        ),
        patch(
            "app.modules.shop_runner.service_manager.services.auto_updater_v3.orchestrator.plan_profitable_expansion",
            return_value=[],
        ),
        patch(
            "app.modules.shop_runner.service_manager.services.auto_updater_v3.orchestrator.select_v3_post_gate_actions",
            select_mock,
        ),
        patch(
            "app.modules.shop_runner.service_manager.services.auto_updater_v3.orchestrator.V3TickKeywordLedger.flush_to_db",
            new=AsyncMock(return_value=False),
        ),
    ):
        updater_cls.return_value.get_fact_data = AsyncMock(
            return_value=MagicMock(pay_for_order=150.0, predict_orders=5)
        )
        await process_adv_v3(complex_adv, wb_shop_data_manager=wb_manager)

    select_mock.assert_called_once()
    plan_fact.set_new_plan_fact.assert_awaited_once()


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


@pytest.mark.unit
@pytest.mark.asyncio
async def test_max_cpa_guard_runs_when_resolve_invalid() -> None:
    """OVERSPEND trim по plan.max, даже если realloc/expansion пропущены (resolve=0)."""
    complex_adv = MagicMock()
    complex_adv.adv_id = 20
    complex_adv.adv_setting = MagicMock()
    complex_adv.shelf_promotion_active = False
    complex_adv.individual_keywords_target_place_mode = False
    complex_adv.v3_rollout_aggressiveness = 2
    complex_adv.get_keywords = AsyncMock(return_value=[])

    dto = MagicMock()
    plan = PlanData(orders=10, target_pay_for_order=0.0, max_pay_for_order=100.0)
    fact = FactData(
        predict_orders=10.0,
        pay_for_order=150.0,
        original_orders=10,
        fact_method=FactMethods.DIRECT_SALES,
    )

    realloc = MagicMock(return_value=[])
    expansion = MagicMock(return_value=[])
    guard = MagicMock(return_value=[])

    with (
        patch(
            "app.modules.shop_runner.service_manager.services.auto_updater_v3.orchestrator._load_v3_wb_context",
            new=AsyncMock(return_value=(dto, {})),
        ),
        patch(
            "app.modules.shop_runner.service_manager.services.auto_updater_v3.orchestrator.build_keyword_v3_contexts",
            return_value=[],
        ),
        patch(
            "app.modules.shop_runner.service_manager.services.auto_updater_v3.orchestrator.plan_data_bootstrap_v3",
            return_value=[],
        ),
        patch.object(PlanFactProvider, "get_plan_data", return_value=plan),
        patch(
            "app.modules.shop_runner.service_manager.services.auto_updater_v3.orchestrator.is_resolve_valid",
            return_value=False,
        ),
        patch(
            "app.modules.shop_runner.service_manager.services.auto_updater_v3.orchestrator.AdvSettingAutoUpdater"
        ) as updater_cls,
        patch(
            "app.modules.shop_runner.service_manager.services.auto_updater_v3.orchestrator.detect_campaign_state",
            return_value=SalesStates.OVERSPEND,
        ),
        patch(
            "app.modules.shop_runner.service_manager.services.auto_updater_v3.orchestrator.plan_cost_reallocation",
            realloc,
        ),
        patch(
            "app.modules.shop_runner.service_manager.services.auto_updater_v3.orchestrator.plan_resolve_calibration_trim",
            return_value=[],
        ),
        patch(
            "app.modules.shop_runner.service_manager.services.auto_updater_v3.orchestrator.plan_profitable_expansion",
            expansion,
        ),
        patch(
            "app.modules.shop_runner.service_manager.services.auto_updater_v3.orchestrator.plan_max_cpa_guard",
            guard,
        ),
        patch(
            "app.modules.shop_runner.service_manager.services.auto_updater_v3.orchestrator.select_v3_post_gate_actions",
            return_value=[],
        ),
        patch(
            "app.modules.shop_runner.service_manager.services.auto_updater_v3.orchestrator.ChangePlanFact"
        ) as pfc_cls,
        patch(
            "app.modules.shop_runner.service_manager.services.auto_updater_v3.orchestrator.V3TickKeywordLedger.flush_to_db",
            new=AsyncMock(return_value=False),
        ),
    ):
        plan_fact = MagicMock()
        plan_fact.check_equal_in_cache = AsyncMock(return_value=True)
        plan_fact.set_new_plan_fact = AsyncMock()
        pfc_cls.return_value = plan_fact
        updater_cls.return_value.get_fact_data = AsyncMock(return_value=fact)
        await process_adv_v3(complex_adv, wb_shop_data_manager=MagicMock())

    realloc.assert_not_called()
    expansion.assert_not_called()
    guard.assert_called_once()
    assert "max_pay_for_order" in guard.call_args.kwargs


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


async def _run_preamble_with_fact_cpa(*, pay_for_order: float) -> tuple[MagicMock, MagicMock, MagicMock]:
    """NORMAL preamble: моки realloc/calibration/guard, fact CPA = ``pay_for_order``."""
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
    complex_adv.get_keywords = AsyncMock(return_value=[])

    dto = MagicMock()
    realloc = MagicMock(return_value=[])
    calibration = MagicMock(return_value=[])
    guard = MagicMock(return_value=[])

    with (
        patch(
            "app.modules.shop_runner.service_manager.services.auto_updater_v3.orchestrator._load_v3_wb_context",
            new=AsyncMock(return_value=(dto, {})),
        ),
        patch(
            "app.modules.shop_runner.service_manager.services.auto_updater_v3.orchestrator.build_keyword_v3_contexts",
            return_value=[],
        ),
        patch(
            "app.modules.shop_runner.service_manager.services.auto_updater_v3.orchestrator.plan_data_bootstrap_v3",
            return_value=[],
        ),
        patch(
            "app.modules.shop_runner.service_manager.services.auto_updater_v3.orchestrator.AdvSettingAutoUpdater"
        ) as updater_cls,
        patch(
            "app.modules.shop_runner.service_manager.services.auto_updater_v3.orchestrator.plan_cost_reallocation",
            realloc,
        ),
        patch(
            "app.modules.shop_runner.service_manager.services.auto_updater_v3.orchestrator.plan_resolve_calibration_trim",
            calibration,
        ),
        patch(
            "app.modules.shop_runner.service_manager.services.auto_updater_v3.orchestrator.plan_profitable_expansion",
            return_value=[],
        ),
        patch(
            "app.modules.shop_runner.service_manager.services.auto_updater_v3.orchestrator.plan_max_cpa_guard",
            guard,
        ),
        patch(
            "app.modules.shop_runner.service_manager.services.auto_updater_v3.orchestrator.select_v3_post_gate_actions",
            return_value=[],
        ),
        patch(
            "app.modules.shop_runner.service_manager.services.auto_updater_v3.orchestrator.ChangePlanFact"
        ) as pfc_cls,
        patch(
            "app.modules.shop_runner.service_manager.services.auto_updater_v3.orchestrator.V3TickKeywordLedger.flush_to_db",
            new=AsyncMock(return_value=False),
        ),
    ):
        plan_fact = MagicMock()
        plan_fact.check_equal_in_cache = AsyncMock(return_value=True)
        plan_fact.set_new_plan_fact = AsyncMock()
        pfc_cls.return_value = plan_fact
        updater_cls.get_plan_data.return_value = plan
        updater_cls.return_value.get_fact_data = AsyncMock(return_value=fact)
        await process_adv_v3(complex_adv, wb_shop_data_manager=MagicMock())

    return realloc, calibration, guard


@pytest.mark.unit
@pytest.mark.asyncio
async def test_cost_reallocation_runs_when_fact_cpa_below_ninety_percent_resolve() -> None:
    """``fact.pay_for_order < 0.9 * resolve`` — portfolio DOWN (запас по CPA)."""
    plan = _plan_for_cpa_gates()
    fact = _fact_for_cpa_gates(pay_for_order=50.0)
    resolve = compute_resolve_cost_threshold(plan, fact)
    assert float(fact.pay_for_order) < 0.9 * float(resolve)

    realloc, calibration, guard = await _run_preamble_with_fact_cpa(pay_for_order=50.0)

    realloc.assert_called_once()
    calibration.assert_not_called()
    guard.assert_not_called()


@pytest.mark.unit
@pytest.mark.asyncio
async def test_cost_reallocation_skipped_when_fact_cpa_near_resolve_but_below_max() -> None:
    """``0.9 * resolve <= fact <= max`` — calibration trim, realloc/guard нет."""
    plan = _plan_for_cpa_gates()
    fact = _fact_for_cpa_gates(pay_for_order=85.0)
    resolve = compute_resolve_cost_threshold(plan, fact)
    assert float(fact.pay_for_order) >= 0.9 * float(resolve)
    assert float(fact.pay_for_order) <= float(plan.max_pay_for_order)

    realloc, calibration, guard = await _run_preamble_with_fact_cpa(pay_for_order=85.0)

    realloc.assert_not_called()
    calibration.assert_called_once()
    guard.assert_not_called()


@pytest.mark.unit
@pytest.mark.asyncio
async def test_resolve_calibration_trim_skipped_when_fact_below_ninety_percent_resolve() -> None:
    """``fact < 0.9 * resolve`` — realloc да, calibration нет."""
    plan = _plan_for_cpa_gates()
    fact = _fact_for_cpa_gates(pay_for_order=50.0)
    resolve = compute_resolve_cost_threshold(plan, fact)
    assert float(fact.pay_for_order) < 0.9 * float(resolve)

    realloc, calibration, guard = await _run_preamble_with_fact_cpa(pay_for_order=50.0)

    realloc.assert_called_once()
    calibration.assert_not_called()
    guard.assert_not_called()


@pytest.mark.unit
@pytest.mark.asyncio
async def test_resolve_calibration_trim_skipped_when_fact_above_max() -> None:
    """``fact > max`` — guard да, calibration нет."""
    plan = _plan_for_cpa_gates()
    fact = _fact_for_cpa_gates(pay_for_order=150.0)
    resolve = compute_resolve_cost_threshold(plan, fact)
    assert float(fact.pay_for_order) > float(plan.max_pay_for_order)

    realloc, calibration, guard = await _run_preamble_with_fact_cpa(pay_for_order=150.0)

    realloc.assert_not_called()
    calibration.assert_not_called()
    guard.assert_called_once()


@pytest.mark.unit
@pytest.mark.asyncio
async def test_max_cpa_guard_runs_when_fact_cpa_above_plan_max() -> None:
    """``fact.pay_for_order > plan.max_pay_for_order`` — MAX_CPA_GUARD, не realloc."""
    plan = _plan_for_cpa_gates()
    fact = _fact_for_cpa_gates(pay_for_order=150.0)
    resolve = compute_resolve_cost_threshold(plan, fact)
    assert float(fact.pay_for_order) > float(plan.max_pay_for_order)
    assert float(fact.pay_for_order) >= 0.9 * float(resolve)

    realloc, calibration, guard = await _run_preamble_with_fact_cpa(pay_for_order=150.0)

    realloc.assert_not_called()
    calibration.assert_not_called()
    guard.assert_called_once()
