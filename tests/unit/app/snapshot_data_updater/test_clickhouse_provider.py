"""Unit: ClickHouse snapshot provider (plan/fact mapping)."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock

import pytest

from app.modules.shop_runner.service_manager.services.plan_fact_controller.plan_fact_reader import (
    PlanFactSummary,
)
from app.snapshot_data_updater.providers.clickhouse_provider import (
    ClickHouseSnapshotProviderLive,
)


@pytest.mark.unit
@pytest.mark.asyncio
async def test_fetch_plan_facts_uses_original_orders_for_fact_orders() -> None:
    """``fact_orders`` — фактические заказы; ``fact_predict_orders`` — прогноз."""
    reader = MagicMock()
    reader.refresh_cache_from_clickhouse = AsyncMock(
        return_value={
            10: PlanFactSummary(
                adv_id=10,
                fact_predict_orders=100.0,
                fact_original_orders=42.0,
                fact_pay_for_order=5.0,
                fact_method="method_a",
            ),
        }
    )
    provider = ClickHouseSnapshotProviderLive(plan_fact_reader=reader)

    result = await provider.fetch_plan_facts("shop-1", [10])

    snap = result[10]
    assert snap.fact_orders == 42.0
    assert snap.fact_predict_orders == 100.0


@pytest.mark.unit
@pytest.mark.asyncio
async def test_fetch_plan_facts_fact_orders_falls_back_to_predict() -> None:
    """Если ``fact_original_orders`` нет — как в ``fact_data_from_plan_fact_summary``."""
    reader = MagicMock()
    reader.refresh_cache_from_clickhouse = AsyncMock(
        return_value={
            11: PlanFactSummary(
                adv_id=11,
                fact_predict_orders=80.0,
                fact_pay_for_order=None,
                fact_original_orders=None,
            ),
        }
    )
    provider = ClickHouseSnapshotProviderLive(plan_fact_reader=reader)

    result = await provider.fetch_plan_facts("shop-1", [11])

    assert result[11].fact_orders == 80.0
    assert result[11].fact_predict_orders == 80.0
