"""Unit тесты для ClickHousePlanFactManager"""

from datetime import date, datetime
from unittest.mock import AsyncMock, patch

import pytest

from app.modules.shop_runner.service_manager.services.plan_fact_controller.clickhouse_plan_fact_manager import (
    ClickHousePlanFactManager,
)
from app.modules.shop_runner.service_manager.services.plan_fact_controller.dto.plan_fact_stat_dto import PlanFactStatDTO


@pytest.mark.unit
@pytest.mark.asyncio
async def test_insert_plan_fact_stats_success():
    """Тест успешной вставки данных (мок клиента)"""
    manager = ClickHousePlanFactManager()
    
    stats = [
        PlanFactStatDTO(
            adv_id=12345,
            shop_id="test_shop",
            date=date.today(),
            timestamp=datetime.now(),
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
            adv_id=67890,
            shop_id="test_shop",
            date=date.today(),
            timestamp=datetime.now(),
            plan_orders=50,
            plan_target_pay_for_order=300,
            plan_max_pay_for_order=800,
            fact_predict_orders=45.3,
            fact_original_orders=40.0,
            fact_pay_for_order=350.0,
            fact_method="BY_CARTS",
            version=1.0,
        ),
    ]
    
    mock_client = AsyncMock()
    mock_client.insert = AsyncMock()
    
    mock_context = AsyncMock()
    mock_context.__aenter__ = AsyncMock(return_value=mock_client)
    mock_context.__aexit__ = AsyncMock(return_value=None)
    
    with patch(
        "app.modules.shop_runner.service_manager.services.plan_fact_controller.clickhouse_plan_fact_manager.get_clickhouse_client",
        return_value=mock_context,
    ):
        await manager.insert_plan_fact_stats(stats)
    
    # Проверяем, что insert был вызван с правильными параметрами
    mock_client.insert.assert_called_once()
    call_args = mock_client.insert.call_args
    
    assert call_args[0][0] == "default_db.plan_fact_stats"
    assert len(call_args[0][1]) == 2  # Две записи
    assert call_args[1]["column_names"] == [
        "adv_id",
        "shop_id",
        "date",
        "timestamp",
        "plan_orders",
        "plan_target_pay_for_order",
        "plan_max_pay_for_order",
        "fact_predict_orders",
        "fact_original_orders",
        "fact_pay_for_order",
        "fact_method",
        "version",
    ]


@pytest.mark.unit
@pytest.mark.asyncio
async def test_insert_plan_fact_stats_empty_list():
    """Тест обработки пустого списка (early return)"""
    manager = ClickHousePlanFactManager()
    
    mock_context = AsyncMock()
    
    with patch(
        "app.modules.shop_runner.service_manager.services.plan_fact_controller.clickhouse_plan_fact_manager.get_clickhouse_client",
        return_value=mock_context,
    ):
        await manager.insert_plan_fact_stats([])
    
    # Проверяем, что контекстный менеджер не был вызван
    mock_context.__aenter__.assert_not_called()


@pytest.mark.unit
@pytest.mark.asyncio
async def test_insert_plan_fact_stats_error_handling():
    """Тест обработки ошибки при вставке (проверка логирования и re-raise)"""
    manager = ClickHousePlanFactManager()
    
    stats = [
        PlanFactStatDTO(
            adv_id=12345,
            shop_id="test_shop",
            date=date.today(),
            timestamp=datetime.now(),
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
    
    mock_client = AsyncMock()
    test_error = Exception("ClickHouse connection error")
    mock_client.insert = AsyncMock(side_effect=test_error)
    
    mock_context = AsyncMock()
    mock_context.__aenter__ = AsyncMock(return_value=mock_client)
    mock_context.__aexit__ = AsyncMock(return_value=None)
    
    with patch(
        "app.modules.shop_runner.service_manager.services.plan_fact_controller.clickhouse_plan_fact_manager.get_clickhouse_client",
        return_value=mock_context,
    ):
        with pytest.raises(Exception, match="ClickHouse connection error"):
            await manager.insert_plan_fact_stats(stats)


@pytest.mark.unit
@pytest.mark.asyncio
async def test_insert_plan_fact_stats_column_names():
    """Тест корректности формирования column_names"""
    manager = ClickHousePlanFactManager()
    
    stats = [
        PlanFactStatDTO(
            adv_id=12345,
            shop_id="test_shop",
            date=date.today(),
            timestamp=datetime.now(),
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
    
    mock_client = AsyncMock()
    mock_client.insert = AsyncMock()
    
    mock_context = AsyncMock()
    mock_context.__aenter__ = AsyncMock(return_value=mock_client)
    mock_context.__aexit__ = AsyncMock(return_value=None)
    
    with patch(
        "app.modules.shop_runner.service_manager.services.plan_fact_controller.clickhouse_plan_fact_manager.get_clickhouse_client",
        return_value=mock_context,
    ):
        await manager.insert_plan_fact_stats(stats)
    
    call_args = mock_client.insert.call_args
    column_names = call_args[1]["column_names"]
    
    expected_columns = [
        "adv_id",
        "shop_id",
        "date",
        "timestamp",
        "plan_orders",
        "plan_target_pay_for_order",
        "plan_max_pay_for_order",
        "fact_predict_orders",
        "fact_original_orders",
        "fact_pay_for_order",
        "fact_method",
        "version",
    ]
    
    assert column_names == expected_columns


@pytest.mark.unit
@pytest.mark.asyncio
async def test_insert_plan_fact_stats_data_formatting():
    """Тест корректности преобразования данных в формат для вставки"""
    manager = ClickHousePlanFactManager()
    
    test_date = date(2025, 12, 25)
    test_timestamp = datetime(2025, 12, 25, 10, 30, 45)
    
    stats = [
        PlanFactStatDTO(
            adv_id=12345,
            shop_id="test_shop",
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
    
    mock_client = AsyncMock()
    mock_client.insert = AsyncMock()
    
    mock_context = AsyncMock()
    mock_context.__aenter__ = AsyncMock(return_value=mock_client)
    mock_context.__aexit__ = AsyncMock(return_value=None)
    
    with patch(
        "app.modules.shop_runner.service_manager.services.plan_fact_controller.clickhouse_plan_fact_manager.get_clickhouse_client",
        return_value=mock_context,
    ):
        await manager.insert_plan_fact_stats(stats)
    
    call_args = mock_client.insert.call_args
    data = call_args[0][1]
    
    assert len(data) == 1
    row = data[0]
    assert row[0] == 12345  # adv_id
    assert row[1] == "test_shop"  # shop_id
    assert row[2] == test_date  # date
    assert row[3] == test_timestamp  # timestamp
    assert row[4] == 100  # plan_orders
    assert row[5] == 500  # plan_target_pay_for_order
    assert row[6] == 1000  # plan_max_pay_for_order
    assert row[7] == 95.5  # fact_predict_orders
    assert row[8] == 90.0  # fact_original_orders
    assert row[9] == 520.0  # fact_pay_for_order
    assert row[10] == "DIRECT_SALES"  # fact_method
    assert row[11] == 1.0  # version


@pytest.mark.unit
@pytest.mark.asyncio
async def test_insert_plan_fact_stats_with_null_values():
    """Тест обработки NULL значений в данных"""
    manager = ClickHousePlanFactManager()
    
    stats = [
        PlanFactStatDTO(
            adv_id=12345,
            shop_id="test_shop",
            date=date.today(),
            timestamp=datetime.now(),
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
    
    mock_client = AsyncMock()
    mock_client.insert = AsyncMock()
    
    mock_context = AsyncMock()
    mock_context.__aenter__ = AsyncMock(return_value=mock_client)
    mock_context.__aexit__ = AsyncMock(return_value=None)
    
    with patch(
        "app.modules.shop_runner.service_manager.services.plan_fact_controller.clickhouse_plan_fact_manager.get_clickhouse_client",
        return_value=mock_context,
    ):
        await manager.insert_plan_fact_stats(stats)
    
    call_args = mock_client.insert.call_args
    data = call_args[0][1]
    
    assert len(data) == 1
    row = data[0]
    # Проверяем, что NULL значения передаются корректно
    assert row[4] is None  # plan_orders
    assert row[5] is None  # plan_target_pay_for_order
    assert row[6] is None  # plan_max_pay_for_order
    assert row[7] is None  # fact_predict_orders
    assert row[8] is None  # fact_original_orders
    assert row[9] is None  # fact_pay_for_order
    assert row[10] is None  # fact_method
    # Обязательные поля не должны быть None
    assert row[0] == 12345  # adv_id
    assert row[1] == "test_shop"  # shop_id
    assert row[11] == 1.0  # version

