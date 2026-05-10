"""Unit tests for ControlCascade force invariants and LastAdvControlSystemUpdate."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.modules.common_slaves.wildberries.models.fact_methods_enum import FactMethods
from app.modules.shop_runner.service_manager.old_modules.setting_auto_updater.data_classes import (
    FactData,
    PlanData,
)
from app.modules.shop_runner.service_manager.old_modules.setting_auto_updater_v2.adv_control_system.cascades.control_cascade import (
    ControlCascade,
)
from app.modules.shop_runner.service_manager.old_modules.setting_auto_updater_v2.adv_control_system.data_classes.data_classes import (
    ExecutionResult,
    ForceContext,
    PipelineContext,
)
from app.modules.shop_runner.service_manager.old_modules.setting_auto_updater_v2.adv_control_system.sales_state.sales_states import (
    SalesStates,
)

pytestmark = pytest.mark.unit


def _minimal_ctx(*, force_value: float) -> PipelineContext:
    complex_adv = MagicMock()
    complex_adv.adv_setting = MagicMock()
    plan = PlanData(orders=10, target_pay_for_order=100, max_pay_for_order=300)
    fact = FactData(
        predict_orders=5.0,
        pay_for_order=150.0,
        original_orders=5,
        fact_method=FactMethods.DIRECT_SALES,
    )
    session = MagicMock()
    return PipelineContext(
        complex_adv=complex_adv,
        plan=plan,
        fact=fact,
        session=session,
        state=SalesStates.OVERSPEND,
        force=ForceContext(value=force_value),
    )


class _RecordingExecutor:
    def __init__(self, name: str, result: ExecutionResult) -> None:
        self.name = name
        self.result = result
        self.calls = 0

    async def execute(self, ctx: PipelineContext) -> ExecutionResult:
        self.calls += 1
        return self.result


@pytest.mark.asyncio
async def test_control_cascade_runs_executors_sequentially_and_weakens_force() -> None:
    ctx = _minimal_ctx(force_value=1.0)
    ex1 = _RecordingExecutor(
        "a", ExecutionResult(success=True, efficiency=0.4, used_power=1)
    )
    ex2 = _RecordingExecutor(
        "b", ExecutionResult(success=True, efficiency=0.3, used_power=1)
    )
    with patch(
        "app.modules.shop_runner.service_manager.old_modules.setting_auto_updater_v2."
        "adv_control_system.cascades.control_cascade.LastAdvControlSystemUpdate"
    ) as cache_cls:
        cache_inst = MagicMock()
        cache_inst.set = AsyncMock()
        cache_cls.return_value = cache_inst

        cascade = ControlCascade([ex1, ex2])
        await cascade.run(ctx)

    assert ex1.calls == 1
    assert ex2.calls == 1
    assert ctx.force.value == pytest.approx(0.3)
    cache_cls.assert_called_once()
    cache_inst.set.assert_awaited_once()


@pytest.mark.asyncio
async def test_control_cascade_stops_when_force_reaches_zero() -> None:
    ctx = _minimal_ctx(force_value=1.0)
    ex1 = _RecordingExecutor(
        "a", ExecutionResult(success=True, efficiency=1.0, used_power=1)
    )
    ex2 = _RecordingExecutor(
        "b", ExecutionResult(success=True, efficiency=0.1, used_power=1)
    )
    with patch(
        "app.modules.shop_runner.service_manager.old_modules.setting_auto_updater_v2."
        "adv_control_system.cascades.control_cascade.LastAdvControlSystemUpdate"
    ) as cache_cls:
        cache_inst = MagicMock()
        cache_inst.set = AsyncMock()
        cache_cls.return_value = cache_inst
        cascade = ControlCascade([ex1, ex2])
        await cascade.run(ctx)

    assert ex1.calls == 1
    assert ex2.calls == 0
    assert ctx.force.value == 0


@pytest.mark.asyncio
async def test_control_cascade_executor_exception_propagates() -> None:
    ctx = _minimal_ctx(force_value=3.0)

    async def _boom(_ctx: PipelineContext) -> ExecutionResult:
        raise RuntimeError("executor boom")

    ex1 = MagicMock()
    ex1.execute = AsyncMock(side_effect=_boom)
    ex2 = MagicMock()
    ex2.execute = AsyncMock(
        return_value=ExecutionResult(success=True, efficiency=0.1, used_power=1)
    )

    with patch(
        "app.modules.shop_runner.service_manager.old_modules.setting_auto_updater_v2."
        "adv_control_system.cascades.control_cascade.LastAdvControlSystemUpdate"
    ) as cache_cls:
        cache_inst = MagicMock()
        cache_inst.set = AsyncMock()
        cache_cls.return_value = cache_inst
        cascade = ControlCascade([ex1, ex2])
        with pytest.raises(RuntimeError, match="executor boom"):
            await cascade.run(ctx)

    ex2.execute.assert_not_called()
    cache_inst.set.assert_not_called()
