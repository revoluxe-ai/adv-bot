"""Интеграционные тесты для полного цикла план-факта"""

from datetime import date, datetime
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.core.redis_manager_v2.redis_client import RedisClient
from app.modules.common_slaves.wildberries.models.fact_methods_enum import FactMethods
from app.modules.shop_runner.modules.wb_api import WBApi
from app.modules.shop_runner.service_manager import CoroutinesManager
from app.modules.shop_runner.tasks_manager.tasks_manager import TasksManager
from app.modules.shop_runner.service_manager.old_modules.setting_auto_updater import (
    AdvSettingAutoUpdater,
)
from app.modules.shop_runner.service_manager.old_modules.setting_auto_updater.data_classes import (
    FactData,
    PlanData,
)
from app.utils.ch_semaphore import anti_ch_crash_semaphore


def _create_manager(wb_api, redis_client_wrapper):
    return CoroutinesManager(
        wb_api,
        redis_client_wrapper,
        tasks_manager=TasksManager(max_workers=1),
    )


@pytest.mark.integration
@pytest.mark.asyncio
async def test_full_cycle_plan_fact_stats(
    clickhouse_client, complex_adv, access_mock, fake_redis
):
    """Тест полного цикла: получение кампаний → получение плана/факта → запись в ClickHouse"""
    await clickhouse_client.command("TRUNCATE TABLE default_db.plan_fact_stats")

    wb_api = WBApi(access_mock, AsyncMock())
    redis_client_wrapper = RedisClient(redis_client=fake_redis)
    manager = _create_manager(wb_api, redis_client_wrapper)

    # Настраиваем план и факт для кампании
    plan = PlanData(orders=100, target_pay_for_order=500, max_pay_for_order=1000)
    fact = FactData(
        predict_orders=95.5,
        original_orders=90.0,
        pay_for_order=520.0,
        fact_method=FactMethods.DIRECT_SALES,
    )

    with (
        patch(
            "app.modules.shop_runner.service_manager.manager.WBShopDataManager.get_complex_advs",
            new=AsyncMock(return_value=[complex_adv]),
        ),
        patch(
            "app.modules.shop_runner.service_manager.services.plan_fact_controller.plan_fact_controller.AdvSettingAutoUpdater.get_plan_data",
            return_value=plan,
        ),
        patch.object(
            AdvSettingAutoUpdater,
            "get_fact_data",
            return_value=fact,
        ),
    ):
        # Используем __wrapped__ для обхода декоратора
        await manager.update_plan_fact_stats.__wrapped__(manager)  # noqa
    async with anti_ch_crash_semaphore:
        # Проверяем, что данные записались в ClickHouse
        result = await clickhouse_client.query(
            f"""
            SELECT
                adv_id, shop_id, date, timestamp,
                plan_orders, plan_target_pay_for_order, plan_max_pay_for_order,
                fact_predict_orders, fact_original_orders, fact_pay_for_order, fact_method,
                version
            FROM default_db.plan_fact_stats
            WHERE adv_id = {complex_adv.adv_id}
            ORDER BY timestamp DESC
            LIMIT 1
            """
        )

    assert result is not None
    assert len(result.result_rows) == 1

    row = result.result_rows[0]
    assert row[0] == complex_adv.adv_id  # adv_id
    assert row[1] == complex_adv.shop_id  # shop_id (используется shop_id из ComplexAdv, а не из manager)
    assert isinstance(row[2], date)  # date
    assert isinstance(row[3], datetime)  # timestamp
    assert row[4] == 100  # plan_orders
    assert row[5] == 500  # plan_target_pay_for_order
    assert row[6] == 1000  # plan_max_pay_for_order
    assert row[7] == 95.5  # fact_predict_orders
    assert row[8] == 90.0  # fact_original_orders
    assert row[9] == 520.0  # fact_pay_for_order
    assert row[10] == "DIRECT_SALES"  # fact_method
    assert isinstance(row[11], float)  # version


@pytest.mark.integration
@pytest.mark.asyncio
async def test_full_cycle_with_real_complex_adv(
    clickhouse_client, complex_adv, access_mock, fake_redis
):
    """Тест с реальными ComplexAdv из фикстуры"""
    await clickhouse_client.command("TRUNCATE TABLE default_db.plan_fact_stats")

    wb_api = WBApi(access_mock, AsyncMock())
    redis_client_wrapper = RedisClient(redis_client=fake_redis)
    manager = _create_manager(wb_api, redis_client_wrapper)

    # Используем реальные данные из complex_adv
    plan = PlanData(orders=200, target_pay_for_order=600, max_pay_for_order=1200)
    fact = FactData(
        predict_orders=190.0,
        original_orders=180.0,
        pay_for_order=610.0,
        fact_method=FactMethods.BY_CARTS,
    )

    with (
        patch(
            "app.modules.shop_runner.service_manager.manager.WBShopDataManager.get_complex_advs",
            new=AsyncMock(return_value=[complex_adv]),
        ),
        patch(
            "app.modules.shop_runner.service_manager.services.plan_fact_controller.plan_fact_controller.AdvSettingAutoUpdater.get_plan_data",
            return_value=plan,
        ),
        patch.object(
            AdvSettingAutoUpdater,
            "get_fact_data",
            return_value=fact,
        ),
    ):
        await manager.update_plan_fact_stats.__wrapped__(manager)  # noqa
    async with anti_ch_crash_semaphore:
        # Проверяем, что данные записались с правильным adv_id из complex_adv
        result = await clickhouse_client.query(
            f"""
            SELECT adv_id, shop_id, plan_orders, fact_predict_orders, fact_method
            FROM default_db.plan_fact_stats
            WHERE adv_id = {complex_adv.adv_id}
            LIMIT 1
            """
        )

    assert len(result.result_rows) == 1
    row = result.result_rows[0]
    assert row[0] == complex_adv.adv_id
    assert row[1] == complex_adv.shop_id
    assert row[2] == 200
    assert row[3] == 190.0
    assert row[4] == "BY_CARTS"


@pytest.mark.integration
@pytest.mark.asyncio
async def test_full_cycle_error_handling_for_some_advs(
    clickhouse_client, complex_adv, access_mock, fake_redis
):
    """Тест обработки ошибок получения данных для отдельных кампаний"""
    await clickhouse_client.command("TRUNCATE TABLE default_db.plan_fact_stats")

    wb_api = WBApi(access_mock, AsyncMock())
    redis_client_wrapper = RedisClient(redis_client=fake_redis)
    manager = _create_manager(wb_api, redis_client_wrapper)

    # Создаем второй ComplexAdv
    adv2 = MagicMock()
    adv2.adv_id = 99999
    adv2.shop_id = "test_shop_2"
    adv2.adv_setting = MagicMock()
    adv2.get_keywords = AsyncMock(return_value=[])

    plan1 = PlanData(orders=100, target_pay_for_order=500, max_pay_for_order=1000)
    plan2 = PlanData(orders=50, target_pay_for_order=300, max_pay_for_order=800)

    fact1 = FactData(
        predict_orders=95.5,
        original_orders=90.0,
        pay_for_order=520.0,
        fact_method=FactMethods.DIRECT_SALES,
    )

    with (
        patch(
            "app.modules.shop_runner.service_manager.manager.WBShopDataManager.get_complex_advs",
            new=AsyncMock(return_value=[complex_adv, adv2]),
        ),
        patch(
            "app.modules.shop_runner.service_manager.services.plan_fact_controller.plan_fact_controller.AdvSettingAutoUpdater.get_plan_data",
            side_effect=[plan1, plan2],
        ),
        patch.object(
            AdvSettingAutoUpdater,
            "get_fact_data",
            new=AsyncMock(side_effect=[fact1, Exception("Fact data error")]),
        ),
    ):
        # Должно обработать ошибку для второй кампании и продолжить
        await manager.update_plan_fact_stats.__wrapped__(manager)  # noqa
    async with anti_ch_crash_semaphore:
        # Проверяем, что записались данные для обеих кампаний
        result = await clickhouse_client.query(
            f"""
            SELECT adv_id, plan_orders, fact_predict_orders
            FROM default_db.plan_fact_stats
            WHERE adv_id IN ({complex_adv.adv_id}, 99999)
            ORDER BY adv_id
            """
        )

    assert len(result.result_rows) == 2

    # Первая кампания с полными данными
    row1 = result.result_rows[0]
    assert row1[0] == complex_adv.adv_id
    assert row1[1] == 100  # plan_orders
    assert row1[2] == 95.5  # fact_predict_orders

    # Вторая кампания без факта из-за ошибки
    row2 = result.result_rows[1]
    assert row2[0] == 99999
    assert row2[1] == 50  # plan_orders
    assert row2[2] is None  # fact_predict_orders (ошибка получения факта)


@pytest.mark.integration
@pytest.mark.asyncio
async def test_full_cycle_multiple_advs_simultaneously(
    clickhouse_client, complex_adv, access_mock, fake_redis
):
    """Тест записи данных для нескольких кампаний одновременно"""
    await clickhouse_client.command("TRUNCATE TABLE default_db.plan_fact_stats")

    wb_api = WBApi(access_mock, AsyncMock())
    redis_client_wrapper = RedisClient(redis_client=fake_redis)
    manager = _create_manager(wb_api, redis_client_wrapper)

    # Создаем дополнительные кампании
    adv2 = MagicMock()
    adv2.adv_id = 11111
    adv2.shop_id = "test_shop_2"
    adv2.adv_setting = MagicMock()
    adv2.get_keywords = AsyncMock(return_value=[])

    adv3 = MagicMock()
    adv3.adv_id = 22222
    adv3.shop_id = "test_shop_3"
    adv3.adv_setting = MagicMock()
    adv3.get_keywords = AsyncMock(return_value=[])

    plans = [
        PlanData(orders=100, target_pay_for_order=500, max_pay_for_order=1000),
        PlanData(orders=150, target_pay_for_order=550, max_pay_for_order=1100),
        PlanData(orders=200, target_pay_for_order=600, max_pay_for_order=1200),
    ]

    facts = [
        FactData(
            predict_orders=95.5,
            original_orders=90.0,
            pay_for_order=520.0,
            fact_method=FactMethods.DIRECT_SALES,
        ),
        FactData(
            predict_orders=145.3,
            original_orders=140.0,
            pay_for_order=560.0,
            fact_method=FactMethods.BY_CARTS,
        ),
        FactData(
            predict_orders=190.0,
            original_orders=180.0,
            pay_for_order=610.0,
            fact_method=FactMethods.DIRECT_SALES,
        ),
    ]

    with (
        patch(
            "app.modules.shop_runner.service_manager.manager.WBShopDataManager.get_complex_advs",
            new=AsyncMock(return_value=[complex_adv, adv2, adv3]),
        ),
        patch(
            "app.modules.shop_runner.service_manager.services.plan_fact_controller.plan_fact_controller.AdvSettingAutoUpdater.get_plan_data",
            side_effect=plans,
        ),
        patch.object(
            AdvSettingAutoUpdater,
            "get_fact_data",
            new=AsyncMock(side_effect=facts),
        ),
    ):
        await manager.update_plan_fact_stats.__wrapped__(manager)  # noqa
    async with anti_ch_crash_semaphore:
        # Проверяем, что все три кампании записались
        result = await clickhouse_client.query(
            f"""
            SELECT adv_id, plan_orders, fact_predict_orders, fact_method
            FROM default_db.plan_fact_stats
            WHERE adv_id IN ({complex_adv.adv_id}, 11111, 22222)
            ORDER BY adv_id
            """
        )

    assert len(result.result_rows) == 3

    # Проверяем данные для каждой кампании
    assert result.result_rows[0][0] == complex_adv.adv_id
    assert result.result_rows[0][1] == 100
    assert result.result_rows[0][2] == 95.5
    assert result.result_rows[0][3] == "DIRECT_SALES"

    assert result.result_rows[1][0] == 11111
    assert result.result_rows[1][1] == 150
    assert result.result_rows[1][2] == 145.3
    assert result.result_rows[1][3] == "BY_CARTS"

    assert result.result_rows[2][0] == 22222
    assert result.result_rows[2][1] == 200
    assert result.result_rows[2][2] == 190.0
    assert result.result_rows[2][3] == "DIRECT_SALES"


@pytest.mark.integration
@pytest.mark.asyncio
async def test_full_cycle_data_correctness_in_clickhouse(
    clickhouse_client, complex_adv, access_mock, fake_redis
):
    """Тест корректности данных в ClickHouse после записи"""
    await clickhouse_client.command("TRUNCATE TABLE default_db.plan_fact_stats")

    wb_api = WBApi(access_mock, AsyncMock())
    redis_client_wrapper = RedisClient(redis_client=fake_redis)
    manager = _create_manager(wb_api, redis_client_wrapper)

    plan = PlanData(orders=100, target_pay_for_order=500, max_pay_for_order=1000)
    fact = FactData(
        predict_orders=95.5,
        original_orders=90.0,
        pay_for_order=520.0,
        fact_method=FactMethods.DIRECT_SALES,
    )

    with (
        patch(
            "app.modules.shop_runner.service_manager.manager.WBShopDataManager.get_complex_advs",
            new=AsyncMock(return_value=[complex_adv]),
        ),
        patch(
            "app.modules.shop_runner.service_manager.services.plan_fact_controller.plan_fact_controller.AdvSettingAutoUpdater.get_plan_data",
            return_value=plan,
        ),
        patch.object(
            AdvSettingAutoUpdater,
            "get_fact_data",
            return_value=fact,
        ),
    ):
        await manager.update_plan_fact_stats.__wrapped__(manager)  # noqa
    async with anti_ch_crash_semaphore:
        # Проверяем все поля на корректность
        result = await clickhouse_client.query(
            f"""
            SELECT
                adv_id, shop_id, date, timestamp,
                plan_orders, plan_target_pay_for_order, plan_max_pay_for_order,
                fact_predict_orders, fact_original_orders, fact_pay_for_order, fact_method,
                version
            FROM default_db.plan_fact_stats
            WHERE adv_id = {complex_adv.adv_id}
            LIMIT 1
            """
        )

    assert len(result.result_rows) == 1
    row = result.result_rows[0]

    # Проверяем обязательные поля
    assert row[0] == complex_adv.adv_id
    assert row[1] == complex_adv.shop_id
    assert isinstance(row[2], date)
    assert isinstance(row[3], datetime)

    # Проверяем план
    assert row[4] == 100
    assert row[5] == 500
    assert row[6] == 1000

    # Проверяем факт
    assert row[7] == 95.5
    assert row[8] == 90.0
    assert row[9] == 520.0
    assert row[10] == "DIRECT_SALES"

    # Проверяем версию
    assert isinstance(row[11], float)
    assert row[11] > 0

    # Проверяем, что timestamp близок к текущему времени
    # ClickHouse возвращает datetime с timezone, нормализуем для сравнения
    timestamp_from_db = row[3].replace(tzinfo=None) if row[3].tzinfo else row[3]
    time_diff = abs((datetime.now() - timestamp_from_db).total_seconds())
    assert time_diff < 60  # Разница должна быть меньше минуты

