"""Unit-тесты FactSalesDeltaManager: BY_CARTS/DIRECT_SALES и выбор PlanFactProvider."""

from __future__ import annotations

from datetime import datetime, timedelta
from types import SimpleNamespace
from uuid import UUID, uuid4

import pytest
from zoneinfo import ZoneInfo
from unittest.mock import AsyncMock

from app.modules.common_slaves.wildberries.models.fact_methods_enum import FactMethods
from app.modules.shop_runner.service_manager.services.increment_fact_data_manager.dto.fact_stat_snapshot import (
    FactStatSnapshot,
)
from app.modules.shop_runner.service_manager.services.increment_fact_data_manager import (
    fact_sales_delta_manager as fact_sales_delta_manager_module,
)
from app.modules.shop_runner.service_manager.services.increment_fact_data_manager.fact_sales_delta_manager import (
    FactSalesDeltaManager,
)

from app.modules.shop_runner.service_manager.old_modules.setting_auto_updater.data_classes import (
    FactData,
)
from app.modules.plan_fact.provider import PlanFactProvider

_MOSCOW_TZ = ZoneInfo("Europe/Moscow")
_FROZEN_NOW = datetime(2026, 8, 2, 12, 0, 0, tzinfo=_MOSCOW_TZ)


def _freeze_manager_now(
    monkeypatch: pytest.MonkeyPatch,
    frozen_now: datetime,
) -> None:
    """Фиксирует datetime.now в FactSalesDeltaManager.

    Без freeze wall-clock drift между snapshot.src_ts и повторным now()
    внутри calculate_fact_data ломает exact float asserts (например 119.99 vs 120.0).
    """

    class _FrozenDateTime(datetime):
        @classmethod
        def now(cls, tz: object | None = None) -> datetime:
            if tz is None:
                return frozen_now.replace(tzinfo=None)
            return frozen_now.astimezone(tz)  # type: ignore[arg-type]

    monkeypatch.setattr(fact_sales_delta_manager_module, "datetime", _FrozenDateTime)


def _create_snapshot(shop_id: UUID, complex_adv_id: int, src_ts: datetime) -> FactStatSnapshot:
    """Собирает минимальный FactStatSnapshot с заданным src_ts."""
    return FactStatSnapshot(
        shop_id=shop_id,
        complex_adv_id=complex_adv_id,
        bucket_start=src_ts,
        src_ts=src_ts,
        version=1,
        views_adv_sum=0,
        clicks_adv_sum=0,
        carts_adv_sum=0,
        orders_adv_sum=0,
        spend_adv_sum_rub=0,
        orders_sum_adv_rub=0,
        open_card_sum=0,
        carts_card_sum=0,
        orders_card_sum=0,
        orders_sum_card_rub=0,
        buy_outs_sum=0,
    )


@pytest.mark.asyncio
async def test_fact_sales_delta_manager_by_carts_converts_carts_to_orders(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """BY_CARTS: predict_orders = carts/period * 24h * ratio; без wall-clock drift."""
    _freeze_manager_now(monkeypatch, _FROZEN_NOW)
    repo = AsyncMock()
    manager = FactSalesDeltaManager(repository=repo)
    shop_uuid = uuid4()
    period_hours = 1
    start_ts = _FROZEN_NOW - timedelta(hours=period_hours)
    snapshot = _create_snapshot(shop_uuid, 12, start_ts)

    repo.fetch_closest_snapshot.return_value = snapshot
    repo.aggregate_deltas_between.return_value = {
        "orders": 60,
        "carts": 20,
        "spend": 500,
    }
    repo.get_carts_to_orders_ratio.return_value = 0.25

    fact_data = await manager.calculate_fact_data(
        12,
        FactMethods.BY_CARTS,
        [42],
        analysis_hours=period_hours,
    )

    assert fact_data is not None
    assert fact_data.predict_orders == 120.0
    assert fact_data.pay_for_order == 100.0


@pytest.mark.asyncio
async def test_fact_sales_delta_manager_direct_sales_scales_orders_per_day(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """DIRECT_SALES: масштабирование orders на сутки при фиксированном period."""
    _freeze_manager_now(monkeypatch, _FROZEN_NOW)
    repo = AsyncMock()
    manager = FactSalesDeltaManager(repository=repo)
    shop_uuid = uuid4()
    period_hours = 2
    start_ts = _FROZEN_NOW - timedelta(hours=period_hours)
    snapshot = _create_snapshot(shop_uuid, 23, start_ts)

    repo.fetch_closest_snapshot.return_value = snapshot
    repo.aggregate_deltas_between.return_value = {
        "orders": 24,
        "carts": 0,
        "spend": 200,
    }

    fact_data = await manager.calculate_fact_data(
        23,
        FactMethods.DIRECT_SALES,
        None,
        analysis_hours=period_hours,
    )

    assert fact_data is not None
    assert fact_data.predict_orders == 288.0
    assert fact_data.pay_for_order == 8.33


@pytest.mark.asyncio
async def test_plan_fact_provider_prefers_delta_manager() -> None:
    """PlanFactProvider предпочитает incremental delta manager при флаге use_incremental_stats."""
    fake_adv = SimpleNamespace(
        sales_predict_method=FactMethods.BY_CARTS,
        adv_id=10,
        shop_id=str(uuid4()),
        nmids=[42],
        use_incremental_stats=True,
    )
    delta_manager = AsyncMock()
    expected_fact = FactData(
        predict_orders=1.0,
        original_orders=1.0,
        pay_for_order=1.0,
        fact_method=FactMethods.BY_CARTS,
    )
    delta_manager.calculate_fact_data.return_value = expected_fact

    provider = PlanFactProvider(fake_adv, fact_sales_manager=delta_manager)
    provider.get_stat_data = AsyncMock()

    result = await provider.get_fact_data([])

    assert result == expected_fact
    delta_manager.calculate_fact_data.assert_awaited_once_with(
        fake_adv.adv_id,
        fake_adv.sales_predict_method,
        fake_adv.nmids,
    )
    provider.get_stat_data.assert_not_awaited()
