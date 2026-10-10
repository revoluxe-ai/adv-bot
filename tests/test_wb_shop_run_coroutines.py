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

pytestmark = pytest.mark.unit


def _build_coroutines_manager_mock() -> MagicMock:
    # Order matches WBShop.run() create_task list
    methods = [
        "update_advs_data_from_wb_to_pg",
        "update_cards_data_from_wb_to_pg",
        "update_common_sale_stat",
        "update_full_adv_stat",
        "update_clusters_adv_stats_today",
        "update_clusters_adv_stats_history",
        "refresh_stats_freshness_cache",
        "adv_settings_auto_update",
        "hierarchical_ad_control_diagnostics",
        "update_minus_phrases_in_advs",
        "update_cluster_bids",
        "cache_current_cluster_bids",
        "preload_min_bids_cache_miss",
        "preload_min_bids_cache_old",
        "handle_stats_stale_emergency",
        "update_plan_fact_stats",
        "auto_budget_watchdog",
        "update_top_key_in_advs",
        "update_common_bid_in_search_adv",
        "increment_fact_data_stats",
        "auto_shelf_bid_increment_stats",
        "auto_shelf_bid_control",
        "white_list_tail_trimmer",
        "auto_reset_bid_for_auto_adv",
        "update_individual_keyword_target_places",
        "change_adv_strategy",
    ]

    manager = MagicMock()
    for method in methods:
        setattr(manager, method, AsyncMock(return_value=None))
    return manager


class RecordingTaskGroup:
    def __init__(self):
        self.created: list[object] = []
        self._tasks: list[asyncio.Task[Any]] = []

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc, tb):
        if self._tasks:
            await asyncio.gather(*self._tasks)
        return False

    def create_task(self, coro):
        self.created.append(coro)
        task = asyncio.create_task(coro)
        self._tasks.append(task)
        return task


@pytest.mark.asyncio
async def test_wb_shop_run_calls_all_coroutines(fake_redis) -> None:
    wb_api_mock = MagicMock()
    wb_api_mock.shop_id = "test_shop_id"
    redis_manager_mock = MagicMock(spec=RedisShopManager)
    redis_manager_mock.DEFAULT_TTL = 60
    redis_manager_mock.renew_shop_ttl = AsyncMock()

    wb_manager_hub = MagicMock()
    wb_manager_hub.wb_data_manager = MagicMock()
    wb_manager_hub.wb_manager = MagicMock()

    redis_client_wrapper = RedisClient(redis_client=fake_redis)
    wb_shop = WBShop(
        wb_api_mock,
        redis_manager_mock,
        redis_client_wrapper,
        tasks_manager=TasksManager(max_workers=1),
        plan_fact_reader=PlanFactReader(),
        wb_manager_hub=wb_manager_hub,
    )

    coroutines_manager_mock = _build_coroutines_manager_mock()

    with patch(
        "app.modules.shop_runner.wb_shop.CoroutinesManager",
        return_value=coroutines_manager_mock,
    ), patch("app.modules.shop_runner.wb_shop.WBShop._alive_worker_run", AsyncMock(return_value=None)), patch("asyncio.TaskGroup", new=RecordingTaskGroup):
        await wb_shop.run()

    for method in (
        "update_advs_data_from_wb_to_pg",
        "update_cards_data_from_wb_to_pg",
        "update_common_sale_stat",
        "update_full_adv_stat",
        "adv_settings_auto_update",
        "hierarchical_ad_control_diagnostics",
        "update_minus_phrases_in_advs",
        "update_clusters_adv_stats_today",
        "update_clusters_adv_stats_history",
        "refresh_stats_freshness_cache",
        "update_cluster_bids",
        "cache_current_cluster_bids",
        "preload_min_bids_cache_miss",
        "preload_min_bids_cache_old",
        "handle_stats_stale_emergency",
        "update_plan_fact_stats",
        "auto_budget_watchdog",
        "update_top_key_in_advs",
        "update_common_bid_in_search_adv",
        "increment_fact_data_stats",
        "auto_shelf_bid_increment_stats",
        "auto_shelf_bid_control",
        "white_list_tail_trimmer",
        "auto_reset_bid_for_auto_adv",
        "update_individual_keyword_target_places",
        "change_adv_strategy",
    ):
        getattr(coroutines_manager_mock, method).assert_called_once()


@pytest.mark.asyncio
async def test_wb_shop_run_gathers_correct_number_of_coroutines(fake_redis) -> None:
    wb_api_mock = MagicMock()
    wb_api_mock.shop_id = "test_shop_id"
    redis_manager_mock = MagicMock(spec=RedisShopManager)
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

    coroutines_manager_mock = _build_coroutines_manager_mock()

    recorded_group = RecordingTaskGroup()

    with patch(
        "app.modules.shop_runner.wb_shop.CoroutinesManager",
        return_value=coroutines_manager_mock,
    ), patch("app.modules.shop_runner.wb_shop.WBShop._alive_worker_run", AsyncMock(return_value=None)), patch("asyncio.TaskGroup", new=lambda *args, **kwargs: recorded_group):
        await wb_shop.run()

    # 1 _alive_worker_run + 26 coroutines from WBShop.run() TaskGroup
    assert len(recorded_group.created) == 27
    for method in (
        "update_advs_data_from_wb_to_pg",
        "update_cards_data_from_wb_to_pg",
        "update_common_sale_stat",
        "update_full_adv_stat",
        "adv_settings_auto_update",
        "hierarchical_ad_control_diagnostics",
        "update_minus_phrases_in_advs",
        "update_clusters_adv_stats_today",
        "update_clusters_adv_stats_history",
        "refresh_stats_freshness_cache",
        "update_cluster_bids",
        "cache_current_cluster_bids",
        "preload_min_bids_cache_miss",
        "preload_min_bids_cache_old",
        "handle_stats_stale_emergency",
        "update_plan_fact_stats",
        "auto_budget_watchdog",
        "update_top_key_in_advs",
        "update_common_bid_in_search_adv",
        "increment_fact_data_stats",
        "auto_shelf_bid_increment_stats",
        "auto_shelf_bid_control",
        "white_list_tail_trimmer",
        "auto_reset_bid_for_auto_adv",
        "update_individual_keyword_target_places",
        "change_adv_strategy",
    ):
        getattr(coroutines_manager_mock, method).assert_called_once()
