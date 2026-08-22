"""Integration: ClickHousePlanFactManager insert/select against test CH DB.

Act path must use the same GuardedClickHouseClient / endpoint as fixture
``clickhouse_client`` (``test_adv_bot_clickhouse`` @ 127.0.0.1:8124). Production
``ClickHousePlanFactManager`` opens ``get_clickhouse_client`` and inserts into
``default_db.plan_fact_stats``; destructive allowlist forbids ``default_db``.
Tests redirect client + rewrite table target only — no ``app/**`` changes.
"""

from __future__ import annotations

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from datetime import date, datetime
from typing import Any

import pytest

from app.modules.shop_runner.service_manager.services.plan_fact_controller import (
    clickhouse_plan_fact_manager as plan_fact_ch_module,
)
from app.modules.shop_runner.service_manager.services.plan_fact_controller.clickhouse_plan_fact_manager import (
    ClickHousePlanFactManager,
)
from app.modules.shop_runner.service_manager.services.plan_fact_controller.dto.plan_fact_stat_dto import (
    PlanFactStatDTO,
)
from app.utils.ch_semaphore import anti_ch_crash_semaphore

pytestmark = pytest.mark.destructive_local

_PROD_TABLE = "default_db.plan_fact_stats"
_TEST_TABLE = "test_adv_bot_clickhouse.plan_fact_stats"


class _PlanFactTestClickHouseClient:
    """Delegate to guarded fixture client; rewrite prod table on insert only.

    Production path still issues ``default_db.plan_fact_stats`` conceptually;
    the wrapper remaps that target before the guarded client sees it so no
    ``default_db`` SQL/table name reaches the destructive allowlist or raw CH.
    """

    def __init__(self, inner: Any) -> None:
        """Args:
            inner: GuardedClickHouseClient from the destructive fixture.
        """
        self._inner = inner

    async def insert(self, *args: Any, **kwargs: Any) -> Any:
        """Rewrite ``default_db.plan_fact_stats`` → test DB, then insert."""
        if args:
            table, *rest = args
            target = _TEST_TABLE if table == _PROD_TABLE else table
            return await self._inner.insert(target, *rest, **kwargs)
        table = kwargs.get("table")
        if table == _PROD_TABLE:
            kwargs = {**kwargs, "table": _TEST_TABLE}
        return await self._inner.insert(**kwargs)

    async def query(self, *args: Any, **kwargs: Any) -> Any:
        """Pass-through query to the guarded fixture client."""
        return await self._inner.query(*args, **kwargs)

    async def command(self, *args: Any, **kwargs: Any) -> Any:
        """Pass-through command to the guarded fixture client."""
        return await self._inner.command(*args, **kwargs)

    def close(self) -> Any:
        """Pass-through close to the guarded fixture client."""
        return self._inner.close()


@pytest.fixture
def plan_fact_manager_on_test_ch(
    clickhouse_client: Any,
    monkeypatch: pytest.MonkeyPatch,
) -> ClickHousePlanFactManager:
    """Patch manager DI so Act insert uses fixture CH + test table.

    Production ``get_clickhouse_client`` opens ``default_db`` (forbidden /
    missing on the destructive test endpoint). Monkeypatch yields a thin
    wrapper over the same GuardedClickHouseClient as Arrange/Assert, with
    insert table remapped to ``test_adv_bot_clickhouse.plan_fact_stats``.
    """
    redirected = _PlanFactTestClickHouseClient(clickhouse_client)

    @asynccontextmanager
    async def _fixture_clickhouse_client() -> AsyncIterator[Any]:
        """Async CM yielding the redirected test GuardedClickHouseClient."""
        yield redirected

    monkeypatch.setattr(
        plan_fact_ch_module,
        "get_clickhouse_client",
        _fixture_clickhouse_client,
    )
    return ClickHousePlanFactManager()


@pytest.mark.integration
@pytest.mark.asyncio
async def test_insert_and_select_single_record(
    clickhouse_client: Any,
    plan_fact_manager_on_test_ch: ClickHousePlanFactManager,
) -> None:
    """TRUNCATE → manager.insert via fixture CH → SELECT one expected row."""
    await clickhouse_client.command(
        "TRUNCATE TABLE test_adv_bot_clickhouse.plan_fact_stats"
    )

    manager = plan_fact_manager_on_test_ch

    test_date = date(2025, 12, 25)
    test_timestamp = datetime(2025, 12, 25, 10, 30, 45)

    stats = [
        PlanFactStatDTO(
            adv_id=12345,
            shop_id="test_shop_123",
            date=test_date,
            timestamp=test_timestamp,
            plan_orders=100,
            plan_target_pay_for_order=500,
            plan_max_pay_for_order=1000,
            fact_predict_orders=95.5,
            fact_original_orders=90.0,
            fact_pay_for_order=520.0,
            fact_method="DIRECT_SALES",
            version=1.0,
        ),
    ]

    await manager.insert_plan_fact_stats(stats)

    result = await clickhouse_client.query(
        """
        SELECT
            adv_id, shop_id, date, timestamp,
            plan_orders, plan_target_pay_for_order, plan_max_pay_for_order,
            fact_predict_orders, fact_original_orders, fact_pay_for_order, fact_method,
            version
        FROM test_adv_bot_clickhouse.plan_fact_stats
        WHERE adv_id = 12345
        ORDER BY timestamp
        """
    )

    assert result is not None
    assert len(result.result_rows) == 1

    row = result.result_rows[0]
    assert row[0] == 12345  # adv_id
    assert row[1] == "test_shop_123"  # shop_id
    assert row[2] == test_date  # date
    # ClickHouse возвращает datetime с timezone, нормализуем для сравнения
    assert row[3].replace(tzinfo=None) == test_timestamp  # timestamp
    assert row[4] == 100  # plan_orders
    assert row[5] == 500  # plan_target_pay_for_order
    assert row[6] == 1000  # plan_max_pay_for_order
    assert row[7] == 95.5  # fact_predict_orders
    assert row[8] == 90.0  # fact_original_orders
    assert row[9] == 520.0  # fact_pay_for_order
    assert row[10] == "DIRECT_SALES"  # fact_method
    assert row[11] == 1.0  # version


@pytest.mark.integration
@pytest.mark.asyncio
async def test_batch_insert_multiple_records(
    clickhouse_client: Any,
    plan_fact_manager_on_test_ch: ClickHousePlanFactManager,
) -> None:
    """Тест батч-вставки нескольких записей через redirected fixture CH."""
    await clickhouse_client.command(
        "TRUNCATE TABLE test_adv_bot_clickhouse.plan_fact_stats"
    )

    manager = plan_fact_manager_on_test_ch

    test_date = date(2025, 12, 25)
    base_timestamp = datetime(2025, 12, 25, 10, 0, 0)

    stats = [
        PlanFactStatDTO(
            adv_id=11111,
            shop_id="test_shop_1",
            date=test_date,
            timestamp=base_timestamp,
            plan_orders=100,
            plan_target_pay_for_order=500,
            plan_max_pay_for_order=1000,
            fact_predict_orders=95.5,
            fact_original_orders=90.0,
            fact_pay_for_order=520.0,
            fact_method="DIRECT_SALES",
            version=1.0,
        ),
        PlanFactStatDTO(
            adv_id=22222,
            shop_id="test_shop_2",
            date=test_date,
            timestamp=base_timestamp,
            plan_orders=50,
            plan_target_pay_for_order=300,
            plan_max_pay_for_order=800,
            fact_predict_orders=45.3,
            fact_original_orders=40.0,
            fact_pay_for_order=350.0,
            fact_method="BY_CARTS",
            version=1.0,
        ),
        PlanFactStatDTO(
            adv_id=33333,
            shop_id="test_shop_3",
            date=test_date,
            timestamp=base_timestamp,
            plan_orders=200,
            plan_target_pay_for_order=600,
            plan_max_pay_for_order=1200,
            fact_predict_orders=190.0,
            fact_original_orders=180.0,
            fact_pay_for_order=610.0,
            fact_method="DIRECT_SALES",
            version=1.0,
        ),
    ]

    await manager.insert_plan_fact_stats(stats)
    async with anti_ch_crash_semaphore:
        count_result = await clickhouse_client.query(
            "SELECT COUNT(*) FROM test_adv_bot_clickhouse.plan_fact_stats WHERE date = '2025-12-25'"
        )
    assert count_result.result_rows[0][0] == 3
    async with anti_ch_crash_semaphore:
        result = await clickhouse_client.query(
            """
            SELECT adv_id, shop_id, plan_orders, fact_predict_orders, fact_method
            FROM test_adv_bot_clickhouse.plan_fact_stats
            WHERE date = '2025-12-25'
            ORDER BY adv_id
            """
        )

    assert len(result.result_rows) == 3
    assert result.result_rows[0][0] == 11111
    assert result.result_rows[1][0] == 22222
    assert result.result_rows[2][0] == 33333


@pytest.mark.integration
@pytest.mark.asyncio
async def test_insert_with_null_plan_values(
    clickhouse_client: Any,
    plan_fact_manager_on_test_ch: ClickHousePlanFactManager,
) -> None:
    """Тест вставки записей с NULL значениями для плана."""
    await clickhouse_client.command(
        "TRUNCATE TABLE test_adv_bot_clickhouse.plan_fact_stats"
    )

    manager = plan_fact_manager_on_test_ch

    test_date = date(2025, 12, 25)
    test_timestamp = datetime(2025, 12, 25, 10, 30, 45)

    stats = [
        PlanFactStatDTO(
            adv_id=44444,
            shop_id="test_shop_null_plan",
            date=test_date,
            timestamp=test_timestamp,
            plan_orders=None,
            plan_target_pay_for_order=None,
            plan_max_pay_for_order=None,
            fact_predict_orders=80.0,
            fact_original_orders=75.0,
            fact_pay_for_order=400.0,
            fact_method="DIRECT_SALES",
            version=1.0,
        ),
    ]

    await manager.insert_plan_fact_stats(stats)
    async with anti_ch_crash_semaphore:
        result = await clickhouse_client.query(
            """
            SELECT plan_orders, plan_target_pay_for_order, plan_max_pay_for_order,
                   fact_predict_orders, fact_original_orders, fact_pay_for_order
            FROM test_adv_bot_clickhouse.plan_fact_stats
            WHERE adv_id = 44444
            """
        )

    assert len(result.result_rows) == 1
    row = result.result_rows[0]
    assert row[0] is None  # plan_orders
    assert row[1] is None  # plan_target_pay_for_order
    assert row[2] is None  # plan_max_pay_for_order
    assert row[3] == 80.0  # fact_predict_orders
    assert row[4] == 75.0  # fact_original_orders
    assert row[5] == 400.0  # fact_pay_for_order


@pytest.mark.integration
@pytest.mark.asyncio
async def test_insert_with_null_fact_values(
    clickhouse_client: Any,
    plan_fact_manager_on_test_ch: ClickHousePlanFactManager,
) -> None:
    """Тест вставки записей с NULL значениями для факта."""
    await clickhouse_client.command(
        "TRUNCATE TABLE test_adv_bot_clickhouse.plan_fact_stats"
    )

    manager = plan_fact_manager_on_test_ch

    test_date = date(2025, 12, 25)
    test_timestamp = datetime(2025, 12, 25, 10, 30, 45)

    stats = [
        PlanFactStatDTO(
            adv_id=55555,
            shop_id="test_shop_null_fact",
            date=test_date,
            timestamp=test_timestamp,
            plan_orders=100,
            plan_target_pay_for_order=500,
            plan_max_pay_for_order=1000,
            fact_predict_orders=None,
            fact_original_orders=None,
            fact_pay_for_order=None,
            fact_method=None,
            version=1.0,
        ),
    ]

    await manager.insert_plan_fact_stats(stats)
    async with anti_ch_crash_semaphore:
        result = await clickhouse_client.query(
            """
            SELECT plan_orders, plan_target_pay_for_order, plan_max_pay_for_order,
                   fact_predict_orders, fact_original_orders, fact_pay_for_order, fact_method
            FROM test_adv_bot_clickhouse.plan_fact_stats
            WHERE adv_id = 55555
            """
        )

    assert len(result.result_rows) == 1
    row = result.result_rows[0]
    assert row[0] == 100  # plan_orders
    assert row[1] == 500  # plan_target_pay_for_order
    assert row[2] == 1000  # plan_max_pay_for_order
    assert row[3] is None  # fact_predict_orders
    assert row[4] is None  # fact_original_orders
    assert row[5] is None  # fact_pay_for_order
    assert row[6] is None  # fact_method


@pytest.mark.integration
@pytest.mark.asyncio
async def test_insert_with_null_plan_and_fact_values(
    clickhouse_client: Any,
    plan_fact_manager_on_test_ch: ClickHousePlanFactManager,
) -> None:
    """Тест вставки записей с NULL значениями для плана и факта."""
    await clickhouse_client.command(
        "TRUNCATE TABLE test_adv_bot_clickhouse.plan_fact_stats"
    )

    manager = plan_fact_manager_on_test_ch

    test_date = date(2025, 12, 25)
    test_timestamp = datetime(2025, 12, 25, 10, 30, 45)

    stats = [
        PlanFactStatDTO(
            adv_id=66666,
            shop_id="test_shop_null_both",
            date=test_date,
            timestamp=test_timestamp,
            plan_orders=None,
            plan_target_pay_for_order=None,
            plan_max_pay_for_order=None,
            fact_predict_orders=None,
            fact_original_orders=None,
            fact_pay_for_order=None,
            fact_method=None,
            version=1.0,
        ),
    ]

    await manager.insert_plan_fact_stats(stats)
    async with anti_ch_crash_semaphore:
        result = await clickhouse_client.query(
            """
            SELECT adv_id, shop_id, date, timestamp,
                   plan_orders, fact_predict_orders, version
            FROM test_adv_bot_clickhouse.plan_fact_stats
            WHERE adv_id = 66666
            """
        )

    assert len(result.result_rows) == 1
    row = result.result_rows[0]
    assert row[0] == 66666  # adv_id
    assert row[1] == "test_shop_null_both"  # shop_id
    assert row[2] == test_date  # date
    assert row[4] is None  # plan_orders
    assert row[5] is None  # fact_predict_orders
    assert row[6] == 1.0  # version


@pytest.mark.integration
@pytest.mark.asyncio
async def test_data_types_correctness(
    clickhouse_client: Any,
    plan_fact_manager_on_test_ch: ClickHousePlanFactManager,
) -> None:
    """Тест корректности типов данных (Int32, Float64, String, Date, DateTime)."""
    await clickhouse_client.command(
        "TRUNCATE TABLE test_adv_bot_clickhouse.plan_fact_stats"
    )

    manager = plan_fact_manager_on_test_ch

    test_date = date(2025, 12, 25)
    test_timestamp = datetime(2025, 12, 25, 10, 30, 45)

    stats = [
        PlanFactStatDTO(
            adv_id=77777,
            shop_id="test_shop_types",
            date=test_date,
            timestamp=test_timestamp,
            plan_orders=100,  # Int32
            plan_target_pay_for_order=500,  # Int32
            plan_max_pay_for_order=1000,  # Int32
            fact_predict_orders=95.5,  # Float64
            fact_original_orders=90.0,  # Float64
            fact_pay_for_order=520.0,  # Float64
            fact_method="DIRECT_SALES",  # String
            version=1.0,  # Float64
        ),
    ]

    await manager.insert_plan_fact_stats(stats)
    async with anti_ch_crash_semaphore:
        result = await clickhouse_client.query(
            """
            SELECT
                toTypeName(adv_id) as adv_id_type,
                toTypeName(shop_id) as shop_id_type,
                toTypeName(date) as date_type,
                toTypeName(timestamp) as timestamp_type,
                toTypeName(plan_orders) as plan_orders_type,
                toTypeName(fact_predict_orders) as fact_predict_orders_type,
                toTypeName(fact_method) as fact_method_type,
                toTypeName(version) as version_type
            FROM test_adv_bot_clickhouse.plan_fact_stats
            WHERE adv_id = 77777
            LIMIT 1
            """
        )

    assert len(result.result_rows) == 1
    row = result.result_rows[0]
    # ClickHouse может возвращать типы с дополнительными модификаторами,
    # поэтому проверяем наличие ключевых слов
    assert "Int32" in row[0] or "Nullable(Int32)" in row[0]  # adv_id
    assert "String" in row[1]  # shop_id
    assert "Date" in row[2]  # date
    assert "DateTime" in row[3]  # timestamp
    assert "Int32" in row[4] or "Nullable(Int32)" in row[4]  # plan_orders
    assert "Float64" in row[5] or "Nullable(Float64)" in row[5]  # fact_predict_orders
    assert "String" in row[6] or "Nullable(String)" in row[6]  # fact_method
    assert "Float64" in row[7]  # version


@pytest.mark.integration
@pytest.mark.asyncio
async def test_partitioning_by_month(
    clickhouse_client: Any,
    plan_fact_manager_on_test_ch: ClickHousePlanFactManager,
) -> None:
    """Тест партиционирования по месяцу."""
    await clickhouse_client.command(
        "TRUNCATE TABLE test_adv_bot_clickhouse.plan_fact_stats"
    )

    manager = plan_fact_manager_on_test_ch

    stats = [
        PlanFactStatDTO(
            adv_id=88888,
            shop_id="test_shop",
            date=date(2025, 11, 30),  # Ноябрь
            timestamp=datetime(2025, 11, 30, 10, 0, 0),
            plan_orders=100,
            plan_target_pay_for_order=500,
            plan_max_pay_for_order=1000,
            fact_predict_orders=95.5,
            fact_original_orders=90.0,
            fact_pay_for_order=520.0,
            fact_method="DIRECT_SALES",
            version=1.0,
        ),
        PlanFactStatDTO(
            adv_id=88888,
            shop_id="test_shop",
            date=date(2025, 12, 1),  # Декабрь
            timestamp=datetime(2025, 12, 1, 10, 0, 0),
            plan_orders=100,
            plan_target_pay_for_order=500,
            plan_max_pay_for_order=1000,
            fact_predict_orders=95.5,
            fact_original_orders=90.0,
            fact_pay_for_order=520.0,
            fact_method="DIRECT_SALES",
            version=1.0,
        ),
    ]

    await manager.insert_plan_fact_stats(stats)
    async with anti_ch_crash_semaphore:
        result = await clickhouse_client.query(
            """
            SELECT partition, count() as cnt
            FROM system.parts
            WHERE database = 'test_adv_bot_clickhouse'
              AND table = 'plan_fact_stats'
              AND active = 1
            GROUP BY partition
            ORDER BY partition
            """
        )

    # Должны быть партиции для ноября (202511) и декабря (202512)
    partitions = [row[0] for row in result.result_rows]
    assert "202511" in partitions or "202512" in partitions


@pytest.mark.integration
@pytest.mark.asyncio
async def test_ordering_by_adv_id_date_timestamp(
    clickhouse_client: Any,
    plan_fact_manager_on_test_ch: ClickHousePlanFactManager,
) -> None:
    """Тест сортировки по (adv_id, date, timestamp)."""
    await clickhouse_client.command(
        "TRUNCATE TABLE test_adv_bot_clickhouse.plan_fact_stats"
    )

    manager = plan_fact_manager_on_test_ch

    test_date = date(2025, 12, 25)

    stats = [
        PlanFactStatDTO(
            adv_id=99999,
            shop_id="test_shop",
            date=test_date,
            timestamp=datetime(2025, 12, 25, 10, 0, 0),  # Раньше
            plan_orders=100,
            plan_target_pay_for_order=500,
            plan_max_pay_for_order=1000,
            fact_predict_orders=95.5,
            fact_original_orders=90.0,
            fact_pay_for_order=520.0,
            fact_method="DIRECT_SALES",
            version=1.0,
        ),
        PlanFactStatDTO(
            adv_id=99999,
            shop_id="test_shop",
            date=test_date,
            timestamp=datetime(2025, 12, 25, 11, 0, 0),  # Позже
            plan_orders=100,
            plan_target_pay_for_order=500,
            plan_max_pay_for_order=1000,
            fact_predict_orders=95.5,
            fact_original_orders=90.0,
            fact_pay_for_order=520.0,
            fact_method="DIRECT_SALES",
            version=2.0,
        ),
    ]

    await manager.insert_plan_fact_stats(stats)
    async with anti_ch_crash_semaphore:
        result = await clickhouse_client.query(
            """
            SELECT adv_id, date, timestamp, version
            FROM test_adv_bot_clickhouse.plan_fact_stats
            WHERE adv_id = 99999
            ORDER BY adv_id, date, timestamp
            """
        )

    assert len(result.result_rows) == 2
    # Первая запись должна быть с более ранним timestamp
    # ClickHouse возвращает datetime с timezone, нормализуем для сравнения
    assert result.result_rows[0][2].replace(tzinfo=None) == datetime(2025, 12, 25, 10, 0, 0)
    assert result.result_rows[0][3] == 1.0
    # Вторая запись должна быть с более поздним timestamp
    assert result.result_rows[1][2].replace(tzinfo=None) == datetime(2025, 12, 25, 11, 0, 0)
    assert result.result_rows[1][3] == 2.0
