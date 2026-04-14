"""Tests for parallel preload_min_bids_cache_miss / preload_min_bids_cache_old."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, call, patch

import pytest

from app.core.mp.wb.dto.adv_placement_type import AdvPlacementType
from app.modules.shop_runner.service_manager.manager import CoroutinesManager
from app.modules.shop_runner.tasks_manager.tasks_manager import TasksManager


def _unwrap(coro_method):
    inner = getattr(coro_method, "__wrapped__", None)
    assert inner is not None
    return inner


@pytest.mark.asyncio
async def test_preload_min_bids_cache_miss_calls_only_miss_refresh() -> None:
    wb_api = MagicMock()
    wb_api.wb_cabinet = MagicMock()
    wb_api.access = MagicMock()
    wb_api.shop_id = "shop-1"
    wb_api.session = MagicMock()

    adv = MagicMock()
    adv.bot_active = True

    wb_shop_dm = MagicMock()
    wb_shop_dm.get_complex_advs = AsyncMock(return_value=[adv])

    wb_manager = MagicMock()
    wb_manager.find_min_bids_cache_miss_cells = AsyncMock(
        return_value=[(100, AdvPlacementType.AUTO_ADV, 1)],
    )
    wb_manager.refresh_min_bids_cache_miss_cells = AsyncMock(return_value=3)
    wb_manager.refresh_min_bids_cache = AsyncMock()

    container_instance = MagicMock()
    container_instance.wb_manager = MagicMock(return_value=wb_manager)

    wb_manager_hub = MagicMock()

    with (
        patch(
            "app.modules.shop_runner.service_manager.manager.settings",
        ) as mock_settings,
        patch(
            "app.modules.shop_runner.service_manager.manager.WBShopDataManager",
            return_value=wb_shop_dm,
        ),
        patch(
            "app.modules.shop_runner.service_manager.manager.WBManagerHubFactory.get_wb_manager_from_context",
            return_value=wb_manager_hub,
        ),
        patch(
            "app.modules.shop_runner.service_manager.services.update_cluster_bids_manager.di.ClusterBidsManagerContainer",
            return_value=container_instance,
        ),
    ):
        mock_settings.AUTO_SETTING_ACTIVE = True

        mgr = CoroutinesManager(
            wb_api,
            MagicMock(),
            tasks_manager=TasksManager(max_workers=1),
            wb_manager_hub=wb_manager_hub,
        )
        await _unwrap(mgr.preload_min_bids_cache_miss)(mgr)

    wb_manager.find_min_bids_cache_miss_cells.assert_has_calls(
        [
            call([adv]),
            call(
                [adv],
                emit_app_log=True,
                log_label="min_bids_cache_miss after refresh",
            ),
        ]
    )
    wb_manager.refresh_min_bids_cache_miss_cells.assert_awaited_once()
    wb_manager.refresh_min_bids_cache.assert_not_called()


@pytest.mark.asyncio
async def test_preload_min_bids_cache_miss_no_cells_does_not_touch_event_refresh() -> None:
    wb_api = MagicMock()
    wb_api.wb_cabinet = MagicMock()
    wb_api.access = MagicMock()
    wb_api.shop_id = "shop-1b"
    wb_api.session = MagicMock()

    adv = MagicMock()
    adv.bot_active = True

    wb_shop_dm = MagicMock()
    wb_shop_dm.get_complex_advs = AsyncMock(return_value=[adv])

    wb_manager = MagicMock()
    wb_manager.find_min_bids_cache_miss_cells = AsyncMock(return_value=[])
    wb_manager.refresh_min_bids_cache_miss_cells = AsyncMock()
    wb_manager.refresh_min_bids_cache = AsyncMock()

    container_instance = MagicMock()
    container_instance.wb_manager = MagicMock(return_value=wb_manager)

    wb_manager_hub = MagicMock()

    with (
        patch(
            "app.modules.shop_runner.service_manager.manager.settings",
        ) as mock_settings,
        patch(
            "app.modules.shop_runner.service_manager.manager.WBShopDataManager",
            return_value=wb_shop_dm,
        ),
        patch(
            "app.modules.shop_runner.service_manager.manager.WBManagerHubFactory.get_wb_manager_from_context",
            return_value=wb_manager_hub,
        ),
        patch(
            "app.modules.shop_runner.service_manager.services.update_cluster_bids_manager.di.ClusterBidsManagerContainer",
            return_value=container_instance,
        ),
    ):
        mock_settings.AUTO_SETTING_ACTIVE = True

        mgr = CoroutinesManager(
            wb_api,
            MagicMock(),
            tasks_manager=TasksManager(max_workers=1),
            wb_manager_hub=wb_manager_hub,
        )
        clear_mock = MagicMock(wraps=mgr._min_bids_old_refresh_permitted.clear)
        mgr._min_bids_old_refresh_permitted.clear = clear_mock
        await _unwrap(mgr.preload_min_bids_cache_miss)(mgr)

    clear_mock.assert_not_called()
    wb_manager.refresh_min_bids_cache_miss_cells.assert_not_called()


@pytest.mark.asyncio
async def test_preload_min_bids_cache_old_calls_full_refresh_after_wait() -> None:
    wb_api = MagicMock()
    wb_api.wb_cabinet = MagicMock()
    wb_api.access = MagicMock()
    wb_api.shop_id = "shop-2"
    wb_api.session = MagicMock()

    adv = MagicMock()
    adv.bot_active = True

    wb_shop_dm = MagicMock()
    wb_shop_dm.get_complex_advs = AsyncMock(return_value=[adv])

    wb_manager = MagicMock()
    wb_manager.refresh_min_bids_cache = AsyncMock()

    container_instance = MagicMock()
    container_instance.wb_manager = MagicMock(return_value=wb_manager)

    wb_manager_hub = MagicMock()

    with (
        patch(
            "app.modules.shop_runner.service_manager.manager.settings",
        ) as mock_settings,
        patch(
            "app.modules.shop_runner.service_manager.manager.WBShopDataManager",
            return_value=wb_shop_dm,
        ),
        patch(
            "app.modules.shop_runner.service_manager.manager.WBManagerHubFactory.get_wb_manager_from_context",
            return_value=wb_manager_hub,
        ),
        patch(
            "app.modules.shop_runner.service_manager.services.update_cluster_bids_manager.di.ClusterBidsManagerContainer",
            return_value=container_instance,
        ),
    ):
        mock_settings.AUTO_SETTING_ACTIVE = True

        mgr = CoroutinesManager(
            wb_api,
            MagicMock(),
            tasks_manager=TasksManager(max_workers=1),
            wb_manager_hub=wb_manager_hub,
        )
        await _unwrap(mgr.preload_min_bids_cache_old)(mgr)

    wb_manager.refresh_min_bids_cache.assert_awaited_once_with([adv])
    wb_manager.find_min_bids_cache_miss_cells.assert_not_called()
