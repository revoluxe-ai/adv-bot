from typing import Any
from unittest.mock import AsyncMock, MagicMock, Mock, patch

import pytest

from app.core.redis_manager_v2.redis_client import RedisClient
from app.modules.shop_runner.modules.wb_api import WBApi
from app.modules.shop_runner.shop_run_worker.redis_manager import RedisShopManager
from app.modules.shop_runner.tasks_manager.tasks_manager import TasksManager
from app.modules.shop_runner.service_manager.services.plan_fact_controller.plan_fact_reader import (
    PlanFactReader,
)
from app.modules.shop_runner.wb_shop import WBShop


class _FakeTaskGroup:
    """Fake asyncio.TaskGroup that records created tasks for test assertions."""

    def __init__(self) -> None:
        self.created: list[Any] = []

    async def __aenter__(self) -> "_FakeTaskGroup":
        return self

    async def __aexit__(self, exc_type: Any, exc: Any, tb: Any) -> bool:
        return False

    def create_task(self, coro: Any) -> MagicMock:
        self.created.append(coro)
        return MagicMock()


@pytest.mark.asyncio
async def test_wb_shop_all_coroutines_launched(fake_redis):
    """Test that WBShop.run() launches all expected coroutines.

    This test helps catch when coroutines are accidentally left commented out
    after development, which is a common issue.
    """
    wb_api_mock = Mock(spec=WBApi)
    wb_api_mock.shop_id = "test_shop_id"
    redis_manager_mock = Mock(spec=RedisShopManager)
    redis_manager_mock.DEFAULT_TTL = 60
    redis_manager_mock.renew_shop_ttl = AsyncMock()

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

    # Mock the CoroutinesManager and all its methods
    expected_coroutines = {
        "parsing_keywords_run": AsyncMock(),
        "update_advs_data_from_wb_to_pg": AsyncMock(),
        "update_cards_data_from_wb_to_pg": AsyncMock(),
        "update_cpm_bid_in_search_advs": AsyncMock(),
        "update_common_sale_stat": AsyncMock(),
        "update_full_adv_stat": AsyncMock(),
        "adv_settings_auto_update": AsyncMock(),
        "update_top_key_in_advs": AsyncMock(),
        "update_predict_ctr": AsyncMock(),
        "auto_adv_active_control": AsyncMock(),
    }

    wb_shop._alive_worker_run = AsyncMock()

    with (
        patch(
            "app.modules.shop_runner.wb_shop.CoroutinesManager"
        ) as mock_coroutines_manager,
        patch("asyncio.TaskGroup", new=_FakeTaskGroup),
    ):
        # Set up all the expected methods on the mock
        mock_manager_instance = mock_coroutines_manager.return_value
        for method_name, mock_method in expected_coroutines.items():
            setattr(mock_manager_instance, method_name, mock_method)

        await wb_shop.run()

        # Verify that all expected coroutines were launched
        for method_name, mock_method in expected_coroutines.items():
            (
                mock_method.assert_called_once(),
                f"Coroutine {method_name} was not launched! "
                f"Check if it's commented out in WBShop.run()",
            )

        wb_shop._alive_worker_run.assert_called_once()


@pytest.mark.asyncio
async def test_wb_shop_commented_coroutines_detection(fake_redis):
    """Test that detects if important coroutines are commented out."""
    wb_api_mock = Mock(spec=WBApi)
    wb_api_mock.shop_id = "test_shop_id"
    redis_manager_mock = Mock(spec=RedisShopManager)
    redis_manager_mock.DEFAULT_TTL = 60

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

    # Core coroutines that should ALWAYS be running
    core_coroutines = {
        "parsing_keywords_run": AsyncMock(),
        "update_advs_data_from_wb_to_pg": AsyncMock(),
        "update_cards_data_from_wb_to_pg": AsyncMock(),
        "update_cpm_bid_in_search_advs": AsyncMock(),
        "update_common_sale_stat": AsyncMock(),
        "update_full_adv_stat": AsyncMock(),
        "adv_settings_auto_update": AsyncMock(),
        "update_top_key_in_advs": AsyncMock(),
        "update_predict_ctr": AsyncMock(),
        "auto_adv_active_control": AsyncMock(),
    }

    # Optional coroutines that might be commented during development
    optional_coroutines = {
        "update_features_in_redis": AsyncMock(),
        "update_data_in_neo4j": AsyncMock(),
    }

    wb_shop._alive_worker_run = AsyncMock()

    with (
        patch(
            "app.modules.shop_runner.wb_shop.CoroutinesManager"
        ) as mock_coroutines_manager,
        patch("asyncio.TaskGroup", new=_FakeTaskGroup),
    ):
        # Set up all methods on the mock
        mock_manager_instance = mock_coroutines_manager.return_value
        for method_name, mock_method in {
            **core_coroutines,
            **optional_coroutines,
        }.items():
            setattr(mock_manager_instance, method_name, mock_method)

        await wb_shop.run()

        # Verify all CORE coroutines are running
        missing_core_coroutines = []
        for method_name, mock_method in core_coroutines.items():
            try:
                mock_method.assert_called_once()
            except AssertionError:
                missing_core_coroutines.append(method_name)

        if missing_core_coroutines:
            pytest.fail(
                f"CRITICAL: Core coroutines are not running: {missing_core_coroutines}. "
                f"These should never be commented out! Check WBShop.run() method."
            )
