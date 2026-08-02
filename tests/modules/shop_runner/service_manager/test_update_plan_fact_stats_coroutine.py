"""Unit тесты для корутины update_plan_fact_stats"""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.core.redis_manager_v2.redis_client import RedisClient
from app.modules.shop_runner.modules.wb_api import WBApi
from app.modules.shop_runner.service_manager import CoroutinesManager
from app.modules.shop_runner.service_manager import manager as coroutines_manager_module
from app.modules.shop_runner.service_manager.services.plan_fact_controller.plan_fact_reader import (
    PlanFactReader,
)
from app.modules.shop_runner.tasks_manager.tasks_manager import TasksManager
from app.modules.shop_runner.service_manager.wb_shop_data_manager.dto.pre_complex_adv import (
    PreComplexAdv,
)


def _create_manager(wb_api, redis_client_wrapper):
    plan_fact_reader = MagicMock(spec=PlanFactReader)
    plan_fact_reader.get_latest_plan_fact = AsyncMock(return_value=None)
    plan_fact_reader.refresh_cache_from_clickhouse = AsyncMock(return_value={})

    wb_manager_hub = MagicMock()
    wb_manager_hub.wb_data_manager = MagicMock()
    wb_manager_hub.wb_manager = MagicMock()

    return CoroutinesManager(
        wb_api,
        redis_client_wrapper,
        tasks_manager=TasksManager(max_workers=1),
        plan_fact_reader=plan_fact_reader,
        wb_manager_hub=wb_manager_hub,
    )


@pytest.mark.unit
@pytest.mark.asyncio
async def test_update_plan_fact_stats_success_with_full_data(
    access_mock, fake_redis
):
    """Тест успешного выполнения с полными данными (план и факт)"""
    wb_api = WBApi(access_mock, AsyncMock())
    redis_client_wrapper = RedisClient(redis_client=fake_redis)
    manager = _create_manager(wb_api, redis_client_wrapper)

    pre_adv1 = MagicMock(spec=PreComplexAdv)
    pre_adv1.adv_id = 11111
    pre_adv1.auto_adv = MagicMock()
    pre_adv2 = MagicMock(spec=PreComplexAdv)
    pre_adv2.adv_id = 22222
    pre_adv2.auto_adv = MagicMock()
    mock_plan_fact_manager = MagicMock()
    mock_plan_fact_manager.process_and_save_pre_complex_advs = AsyncMock()

    with (
        patch(
            "app.modules.shop_runner.service_manager.manager.WBShopDataManager.get_pre_complex_advs",
            new=AsyncMock(return_value=[pre_adv1, pre_adv2]),
        ),
        patch(
            "app.modules.shop_runner.service_manager.services.plan_fact_controller.plan_fact_manager.PlanFactManager",
            return_value=mock_plan_fact_manager,
        ),
    ):
        # Используем __wrapped__ для обхода декоратора
        await manager.update_plan_fact_stats.__wrapped__(manager, only_bot_active=False)  # noqa

    # Проверяем, что process_and_save был вызван с правильными аргументами
    mock_plan_fact_manager.process_and_save_pre_complex_advs.assert_called_once()
    call_args = mock_plan_fact_manager.process_and_save_pre_complex_advs.call_args
    advs_arg = call_args[0][0]
    refresh_call = manager._plan_fact_reader.refresh_cache_from_clickhouse.call_args

    assert len(advs_arg) == 2
    assert advs_arg[0].adv_id == 11111
    assert advs_arg[1].adv_id == 22222
    assert refresh_call is not None
    assert refresh_call.args == ([11111, 22222],)


@pytest.mark.unit
@pytest.mark.asyncio
async def test_update_plan_fact_stats_empty_advs_list(access_mock, fake_redis):
    """Тест обработки пустого списка кампаний"""
    wb_api = WBApi(access_mock, AsyncMock())
    redis_client_wrapper = RedisClient(redis_client=fake_redis)
    manager = _create_manager(wb_api, redis_client_wrapper)

    mock_plan_fact_manager = MagicMock()
    mock_plan_fact_manager.process_and_save_pre_complex_advs = AsyncMock()

    with (
        patch(
            "app.modules.shop_runner.service_manager.manager.WBShopDataManager.get_pre_complex_advs",
            new=AsyncMock(return_value=[]),
        ),
        patch(
            "app.modules.shop_runner.service_manager.services.plan_fact_controller.plan_fact_manager.PlanFactManager",
            return_value=mock_plan_fact_manager,
        ),
    ):
        await manager.update_plan_fact_stats.__wrapped__(manager, only_bot_active=False)  # noqa

    # Проверяем, что process_and_save не был вызван (early return в корутине)
    mock_plan_fact_manager.process_and_save_pre_complex_advs.assert_not_called()
    manager._plan_fact_reader.refresh_cache_from_clickhouse.assert_not_called()


@pytest.mark.unit
@pytest.mark.asyncio
async def test_update_plan_fact_stats_calls_process_and_save(access_mock, fake_redis):
    """Тест вызова process_and_save с правильными аргументами"""
    wb_api = WBApi(access_mock, AsyncMock())
    redis_client_wrapper = RedisClient(redis_client=fake_redis)
    manager = _create_manager(wb_api, redis_client_wrapper)

    pre_adv = MagicMock(spec=PreComplexAdv)
    pre_adv.adv_id = 12345
    pre_adv.auto_adv = MagicMock()

    mock_plan_fact_manager = MagicMock()
    mock_plan_fact_manager.process_and_save_pre_complex_advs = AsyncMock()

    with (
        patch(
            "app.modules.shop_runner.service_manager.manager.WBShopDataManager.get_pre_complex_advs",
            new=AsyncMock(return_value=[pre_adv]),
        ),
        patch(
            "app.modules.shop_runner.service_manager.services.plan_fact_controller.plan_fact_manager.PlanFactManager",
            return_value=mock_plan_fact_manager,
        ),
    ):
        await manager.update_plan_fact_stats.__wrapped__(manager, only_bot_active=False)  # noqa

    # Проверяем, что process_and_save был вызван с правильными аргументами
    mock_plan_fact_manager.process_and_save_pre_complex_advs.assert_called_once()
    call_args = mock_plan_fact_manager.process_and_save_pre_complex_advs.call_args
    advs_arg = call_args[0][0]
    refresh_call = manager._plan_fact_reader.refresh_cache_from_clickhouse.call_args

    assert len(advs_arg) == 1
    assert advs_arg[0].adv_id == 12345
    assert refresh_call is not None
    assert refresh_call.args == ([12345],)


@pytest.mark.unit
@pytest.mark.asyncio
async def test_update_plan_fact_stats_multiple_advs(access_mock, fake_redis):
    """Тест обработки нескольких кампаний"""
    wb_api = WBApi(access_mock, AsyncMock())
    redis_client_wrapper = RedisClient(redis_client=fake_redis)
    manager = _create_manager(wb_api, redis_client_wrapper)

    pre_advs = []
    for i in range(5):
        pre_adv = MagicMock(spec=PreComplexAdv)
        pre_adv.adv_id = 10000 + i
        pre_adv.auto_adv = MagicMock()
        pre_advs.append(pre_adv)

    mock_plan_fact_manager = MagicMock()
    mock_plan_fact_manager.process_and_save_pre_complex_advs = AsyncMock()

    with (
        patch(
            "app.modules.shop_runner.service_manager.manager.WBShopDataManager.get_pre_complex_advs",
            new=AsyncMock(return_value=pre_advs),
        ),
        patch(
            "app.modules.shop_runner.service_manager.services.plan_fact_controller.plan_fact_manager.PlanFactManager",
            return_value=mock_plan_fact_manager,
        ),
    ):
        await manager.update_plan_fact_stats.__wrapped__(manager, only_bot_active=False)  # noqa

    # Проверяем, что process_and_save был вызван с правильными аргументами
    mock_plan_fact_manager.process_and_save_pre_complex_advs.assert_called_once()
    call_args = mock_plan_fact_manager.process_and_save_pre_complex_advs.call_args
    advs_arg = call_args[0][0]
    refresh_call = manager._plan_fact_reader.refresh_cache_from_clickhouse.call_args

    assert len(advs_arg) == 5
    for i, adv in enumerate(advs_arg):
        assert adv.adv_id == 10000 + i
    assert refresh_call is not None
    assert refresh_call.args == ([10000, 10001, 10002, 10003, 10004],)


@pytest.mark.unit
@pytest.mark.asyncio
async def test_update_plan_fact_stats_uses_wrapped(access_mock, fake_redis):
    """Тест использования __wrapped__ для обхода декоратора"""
    wb_api = WBApi(access_mock, AsyncMock())
    redis_client_wrapper = RedisClient(redis_client=fake_redis)
    manager = _create_manager(wb_api, redis_client_wrapper)

    pre_adv = MagicMock(spec=PreComplexAdv)
    pre_adv.adv_id = 99999
    pre_adv.auto_adv = MagicMock()

    mock_plan_fact_manager = MagicMock()
    mock_plan_fact_manager.process_and_save_pre_complex_advs = AsyncMock()

    with (
        patch(
            "app.modules.shop_runner.service_manager.manager.WBShopDataManager.get_pre_complex_advs",
            new=AsyncMock(return_value=[pre_adv]),
        ),
        patch(
            "app.modules.shop_runner.service_manager.services.plan_fact_controller.plan_fact_manager.PlanFactManager",
            return_value=mock_plan_fact_manager,
        ),
    ):
        # Используем __wrapped__ для обхода декоратора while_coroutine_decorator
        await manager.update_plan_fact_stats.__wrapped__(manager, only_bot_active=False)  # noqa

    # Проверяем, что метод был вызван
    mock_plan_fact_manager.process_and_save_pre_complex_advs.assert_called_once()
    manager._plan_fact_reader.refresh_cache_from_clickhouse.assert_called_once()


@pytest.mark.unit
def test_collect_plan_fact_refresh_adv_ids_dedup_and_sort():
    """Проверяет стабильную дедупликацию и сортировку adv_id для refresh."""
    pre_adv_1 = MagicMock(spec=PreComplexAdv)
    pre_adv_1.adv_id = 22
    pre_adv_2 = MagicMock(spec=PreComplexAdv)
    pre_adv_2.adv_id = 11
    pre_adv_3 = MagicMock(spec=PreComplexAdv)
    pre_adv_3.adv_id = 22

    result = coroutines_manager_module._collect_plan_fact_refresh_adv_ids(
        [pre_adv_1, pre_adv_2, pre_adv_3]
    )

    assert result == [11, 22]
