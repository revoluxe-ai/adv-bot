import asyncio
from typing import Any
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.core.redis_manager_v2.redis_client import RedisClient
from app.modules.shop_runner.shop_run_worker.redis_manager import RedisShopManager
from app.modules.shop_runner.tasks_manager.tasks_manager import TasksManager
from app.modules.shop_runner.service_manager.services.plan_fact_controller.plan_fact_reader import (
    PlanFactReader,
)
from app.modules.shop_runner.wb_shop import WBShop


@pytest.mark.asyncio
async def test_wb_shop_run_calls_all_coroutines(fake_redis) -> None:
    """
    Тест проверяет, что метод run класса WBShop запускает необходимые корутины
    """
    # Создаем моки
    wb_api_mock = MagicMock()
    wb_api_mock.shop_id = "test_shop_id"
    redis_manager_mock = MagicMock(spec=RedisShopManager)
    redis_manager_mock.DEFAULT_TTL = 60
    redis_manager_mock.renew_shop_ttl = AsyncMock()

    wb_manager_hub = MagicMock()
    wb_manager_hub.wb_data_manager = MagicMock()
    wb_manager_hub.wb_manager = MagicMock()

    # Создаем экземпляр WBShop
    redis_client_wrapper = RedisClient(redis_client=fake_redis)
    wb_shop = WBShop(
        wb_api_mock,
        redis_manager_mock,
        redis_client_wrapper,
        tasks_manager=TasksManager(max_workers=1),
        plan_fact_reader=PlanFactReader(),
        wb_manager_hub=wb_manager_hub,
    )

    coroutines_manager_mock = MagicMock()
    coroutines_manager_mock.update_common_bid_in_search_adv = AsyncMock()

    with patch(
        "app.modules.shop_runner.wb_shop.CoroutinesManager",
        return_value=coroutines_manager_mock,
    ):
        await wb_shop.run()

    coroutines_manager_mock.update_common_bid_in_search_adv.assert_awaited_once()

@pytest.mark.asyncio
async def test_wb_shop_run_gathers_correct_number_of_coroutines(fake_redis) -> None:
    """
    Тест проверяет, что метод run класса WBShop передает правильное количество
    корутин в asyncio.gather
    """
    # Создаем моки
    wb_api_mock = MagicMock()
    wb_api_mock.shop_id = "test_shop_id"
    redis_manager_mock = MagicMock(spec=RedisShopManager)
    redis_manager_mock.DEFAULT_TTL = 60
    redis_manager_mock.renew_shop_ttl = AsyncMock()

    # Создаем экземпляр WBShop
    redis_client_wrapper = RedisClient(redis_client=fake_redis)
    wb_manager_hub = MagicMock()
    wb_manager_hub.wb_data_manager = MagicMock()
    wb_manager_hub.wb_manager = MagicMock()

    wb_shop = WBShop(
        wb_api_mock,
        redis_manager_mock,
        redis_client_wrapper,
        tasks_manager=TasksManager(max_workers=1),
        plan_fact_reader=PlanFactReader(),
        wb_manager_hub=wb_manager_hub,
    )

    coroutines_manager_mock = MagicMock()
    coroutines_manager_mock.update_common_bid_in_search_adv = AsyncMock()

    original_task_group = asyncio.TaskGroup
    recorded_groups: list["RecordingTaskGroup"] = []

    class RecordingTaskGroup:
        def __init__(self):
            self.created: list[object] = []
            self._inner = original_task_group()

        async def __aenter__(self):
            await self._inner.__aenter__()
            return self

        async def __aexit__(self, exc_type, exc, tb):
            return await self._inner.__aexit__(exc_type, exc, tb)

        def create_task(self, coro):
            self.created.append(coro)
            return self._inner.create_task(coro)

    def recording_task_group_factory(*args, **kwargs):
        group = RecordingTaskGroup()
        recorded_groups.append(group)
        return group

    with patch(
        "app.modules.shop_runner.wb_shop.CoroutinesManager",
        return_value=coroutines_manager_mock,
    ), patch("asyncio.TaskGroup", new=recording_task_group_factory):
        await wb_shop.run()

    assert recorded_groups, "TaskGroup was not created"
    assert len(recorded_groups[0].created) == 1
    coroutines_manager_mock.update_common_bid_in_search_adv.assert_awaited_once()
