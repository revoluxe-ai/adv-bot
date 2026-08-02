"""Интеграционные проверки min bids: Redis v2, wiring WBManager и порядок miss/old через Event.

Используется fakeredis (тот же RedisClient, что в проде), ответы WB API — моки.
Это закрывает разрыв между юнит-тестами слоёв и даёт проверку реальных ключей v2
и координации корутин; поведение живого WB API и кластера Redis остаётся вне scope.
"""

from __future__ import annotations

import asyncio
import json
from unittest.mock import AsyncMock, MagicMock, PropertyMock, patch

import pytest

from app.core.mp.wb.dto.adv_min_bids import AdvMinNmidsBids
from app.core.mp.wb.dto.adv_placement_type import AdvPlacementType
from app.core.redis_manager_v2.redis_client import RedisClient
from app.modules.shop_runner.service_manager.manager import CoroutinesManager
from app.modules.shop_runner.service_manager.services.update_cluster_bids_manager.redis_min_bids_cache_manager import (
    MinBidsAdvPlacementCacheMixin,
)
from app.modules.shop_runner.service_manager.services.update_cluster_bids_manager.wb_manager.wb_manager import (
    WBManager,
)
from app.modules.shop_runner.tasks_manager.tasks_manager import TasksManager


def _unwrap(coro_method):
    inner = getattr(coro_method, "__wrapped__", None)
    assert inner is not None
    return inner


def _make_adv(*, nmids: list[int], auto_id: int, search_id: int | None = None) -> MagicMock:
    adv = MagicMock()
    adv.bot_active = True
    adv.nmids = nmids
    adv.auto_adv_id = auto_id
    adv.search_adv_id = search_id
    return adv


def _hub_with_redis(redis_wrapper: RedisClient) -> MagicMock:
    hub = MagicMock()
    hub.redis_client_wrapper = redis_wrapper
    return hub


@pytest.mark.integration
@pytest.mark.asyncio
async def test_refresh_min_bids_cache_writes_v2_keys_readable_from_redis(
    fake_redis,
) -> None:
    """После refresh_min_bids_cache ячейки читаются из того же Redis через v2-ключи."""
    redis_wrapper = RedisClient(redis_client=fake_redis)
    hub = _hub_with_redis(redis_wrapper)
    hub.wb_data_manager.get_min_bids_for_command = AsyncMock(
        return_value=AdvMinNmidsBids(auto={101: 40, 102: 41}, search={}),
    )

    adv = _make_adv(nmids=[101, 102], auto_id=600)

    with patch.object(WBManager, "wb_manager_hub", PropertyMock(return_value=hub)):
        mgr = WBManager("shop-integration")
        await mgr.refresh_min_bids_cache([adv])

    for nmid, cpm in ((101, 40), (102, 41)):
        key = MinBidsAdvPlacementCacheMixin.min_bids_v2_key(
            600, AdvPlacementType.AUTO_ADV, nmid
        )
        raw = await fake_redis.get(key)
        assert raw is not None
        assert json.loads(raw)["cpm"] == cpm


@pytest.mark.integration
@pytest.mark.asyncio
async def test_miss_snapshot_empty_after_full_refresh_same_redis(
    fake_redis,
) -> None:
    """Полный refresh заполняет кеш; find_min_bids_cache_miss_cells возвращает пусто."""
    redis_wrapper = RedisClient(redis_client=fake_redis)
    hub = _hub_with_redis(redis_wrapper)
    hub.wb_data_manager.get_min_bids_for_command = AsyncMock(
        return_value=AdvMinNmidsBids(auto={7: 100}, search={}),
    )

    adv = _make_adv(nmids=[7], auto_id=200)

    with patch.object(WBManager, "wb_manager_hub", PropertyMock(return_value=hub)):
        mgr = WBManager("shop-integration")
        misses_before = await mgr.find_min_bids_cache_miss_cells([adv])
        assert len(misses_before) >= 1
        await mgr.refresh_min_bids_cache([adv])
        misses_after = await mgr.find_min_bids_cache_miss_cells([adv])
        assert misses_after == []


@pytest.mark.integration
@pytest.mark.asyncio
async def test_parallel_preload_miss_blocks_old_until_miss_finishes(
    fake_redis,
) -> None:
    """При очищенном Event сначала отрабатывает miss-refresh, затем old-refresh."""
    redis_wrapper = RedisClient(redis_client=fake_redis)
    hub = _hub_with_redis(redis_wrapper)
    hub.wb_data_manager.get_min_bids_for_command = AsyncMock(
        return_value=AdvMinNmidsBids(auto={5: 33}, search={}),
    )
    hub.wb_data_manager.get_min_bids_per_command_item = AsyncMock(
        return_value=[
            AdvMinNmidsBids(auto={5: 33}, search={}),
        ],
    )

    wb_api = MagicMock()
    wb_api.shop_id = "shop-parallel"
    wb_api.wb_cabinet = MagicMock()
    wb_api.access = MagicMock()
    wb_api.session = MagicMock()

    adv = _make_adv(nmids=[5], auto_id=900)
    wb_shop_dm = MagicMock()
    wb_shop_dm.get_complex_advs = AsyncMock(return_value=[adv])

    call_order: list[str] = []

    orig_old = WBManager.refresh_min_bids_cache
    orig_miss_cells = WBManager.refresh_min_bids_cache_miss_cells

    async def tracked_old(self, advs):  # noqa: ANN001
        call_order.append("old_refresh")
        return await orig_old(self, advs)

    async def tracked_miss_cells(self, miss_cells):  # noqa: ANN001
        call_order.append("miss_refresh")
        return await orig_miss_cells(self, miss_cells)

    with (
        patch(
            "app.modules.shop_runner.service_manager.manager.settings",
        ) as mock_settings,
        patch(
            "app.modules.shop_runner.service_manager.manager.WBShopDataManager",
            return_value=wb_shop_dm,
        ),
        patch.object(WBManager, "refresh_min_bids_cache", tracked_old),
        patch.object(WBManager, "refresh_min_bids_cache_miss_cells", tracked_miss_cells),
        patch.object(WBManager, "wb_manager_hub", PropertyMock(return_value=hub)),
    ):
        mock_settings.AUTO_SETTING_ACTIVE = True

        mgr = CoroutinesManager(
            wb_api,
            redis_wrapper,
            tasks_manager=TasksManager(max_workers=2),
            wb_manager_hub=hub,
        )
        mgr._min_bids_old_refresh_permitted.clear()

        old_coro = _unwrap(mgr.preload_min_bids_cache_old)(
            mgr, only_bot_active=False
        )
        miss_coro = _unwrap(mgr.preload_min_bids_cache_miss)(
            mgr, only_bot_active=False
        )

        t_old = asyncio.create_task(old_coro)
        for _ in range(5):
            await asyncio.sleep(0)
        t_miss = asyncio.create_task(miss_coro)
        await asyncio.gather(t_old, t_miss)

    assert call_order == ["miss_refresh", "old_refresh"]


@pytest.mark.integration
@pytest.mark.asyncio
async def test_preload_min_bids_cache_old_no_wb_when_auto_setting_off(
    fake_redis,
) -> None:
    """При AUTO_SETTING_ACTIVE=False refresh к WB не вызывается."""
    redis_wrapper = RedisClient(redis_client=fake_redis)
    hub = _hub_with_redis(redis_wrapper)
    hub.wb_data_manager.get_min_bids_for_command = AsyncMock()

    wb_api = MagicMock()
    wb_api.shop_id = "shop-off"
    wb_api.wb_cabinet = MagicMock()
    wb_api.access = MagicMock()
    wb_api.session = MagicMock()

    adv = _make_adv(nmids=[1], auto_id=1)
    wb_shop_dm = MagicMock()
    wb_shop_dm.get_complex_advs = AsyncMock(return_value=[adv])

    with (
        patch(
            "app.modules.shop_runner.service_manager.manager.settings",
        ) as mock_settings,
        patch(
            "app.modules.shop_runner.service_manager.manager.WBShopDataManager",
            return_value=wb_shop_dm,
        ),
        patch.object(WBManager, "wb_manager_hub", PropertyMock(return_value=hub)),
    ):
        mock_settings.AUTO_SETTING_ACTIVE = False

        mgr = CoroutinesManager(
            wb_api,
            redis_wrapper,
            tasks_manager=TasksManager(max_workers=1),
            wb_manager_hub=hub,
        )
        await _unwrap(mgr.preload_min_bids_cache_old)(mgr, only_bot_active=False)

    hub.wb_data_manager.get_min_bids_for_command.assert_not_called()
