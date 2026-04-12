"""Tests for WBManager.get_min_bids with adv+placement+nmid cache."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, PropertyMock, patch

import pytest

from app.core.mp.wb.dto.adv_min_bids import AdvMinNmidsBids
from app.modules.shop_runner.service_manager.services.update_cluster_bids_manager.excs import (
    ClusterBidsUpdateError,
)
from app.modules.shop_runner.service_manager.services.update_cluster_bids_manager.wb_manager.wb_manager import (
    WBManager,
)


def _make_adv(*, nmids: list[int], auto_id: int, search_id: int | None = None) -> MagicMock:
    adv = MagicMock()
    adv.nmids = nmids
    adv.auto_adv_id = auto_id
    adv.search_adv_id = search_id
    return adv


@pytest.mark.asyncio
async def test_cache_possible_false_skips_redis_cache_manager() -> None:
    hub = MagicMock()
    hub.wb_data_manager.get_min_bids = AsyncMock(
        return_value=AdvMinNmidsBids(auto={1: 10}, search={}),
    )

    with (
        patch.object(WBManager, "wb_manager_hub", PropertyMock(return_value=hub)),
        patch(
            "app.modules.shop_runner.service_manager.services.update_cluster_bids_manager.wb_manager.wb_manager.MinBidsCacheManager",
        ) as mock_cache_cls,
    ):
        mgr = WBManager("shop-x")
        out = await mgr.get_min_bids([_make_adv(nmids=[1], auto_id=100)], cache_possible=False)

    assert out.auto[1] == 10
    hub.wb_data_manager.get_min_bids.assert_awaited_once()
    hub.wb_data_manager.get_min_bids_for_command.assert_not_called()
    mock_cache_cls.assert_not_called()


@pytest.mark.asyncio
async def test_full_cache_hit_no_api_call() -> None:
    hub = MagicMock()
    hub.wb_data_manager.get_min_bids_for_command = AsyncMock()

    cache_instance = MagicMock()
    cache_instance.get_min_bid_for_adv_placement_nmid = AsyncMock(return_value=55)

    with (
        patch.object(WBManager, "wb_manager_hub", PropertyMock(return_value=hub)),
        patch(
            "app.modules.shop_runner.service_manager.services.update_cluster_bids_manager.wb_manager.wb_manager.MinBidsCacheManager",
            return_value=cache_instance,
        ),
    ):
        mgr = WBManager("shop-x")
        out = await mgr.get_min_bids([_make_adv(nmids=[7], auto_id=200)], cache_possible=True)

    assert out.auto == {7: 55}
    assert out.search == {}
    hub.wb_data_manager.get_min_bids_for_command.assert_not_called()
    cache_instance.set_min_bid_for_adv_placement_nmid.assert_not_called()


@pytest.mark.asyncio
async def test_partial_miss_calls_get_min_bids_for_command_and_merges() -> None:
    hub = MagicMock()
    hub.wb_data_manager.get_min_bids_for_command = AsyncMock(
        return_value=AdvMinNmidsBids(auto={8: 99}, search={}),
    )

    async def cache_get(adv_id: int, _placement: object, nmid: int) -> int | None:
        if nmid == 7:
            return 50
        return None

    cache_instance = MagicMock()
    cache_instance.get_min_bid_for_adv_placement_nmid = AsyncMock(side_effect=cache_get)
    cache_instance.set_min_bid_for_adv_placement_nmid = AsyncMock()

    with (
        patch.object(WBManager, "wb_manager_hub", PropertyMock(return_value=hub)),
        patch(
            "app.modules.shop_runner.service_manager.services.update_cluster_bids_manager.wb_manager.wb_manager.MinBidsCacheManager",
            return_value=cache_instance,
        ),
    ):
        mgr = WBManager("shop-x")
        out = await mgr.get_min_bids(
            [_make_adv(nmids=[7, 8], auto_id=300)],
            cache_possible=True,
        )

    assert out.auto[7] == 50
    assert out.auto[8] == 99
    hub.wb_data_manager.get_min_bids_for_command.assert_awaited_once()
    cmd = hub.wb_data_manager.get_min_bids_for_command.await_args.args[0]
    assert len(cmd.items) == 1
    assert cmd.items[0].nmids == [8]
    cache_instance.set_min_bid_for_adv_placement_nmid.assert_awaited()


@pytest.mark.asyncio
async def test_full_miss_no_hits() -> None:
    hub = MagicMock()
    hub.wb_data_manager.get_min_bids_for_command = AsyncMock(
        return_value=AdvMinNmidsBids(auto={1: 12}, search={}),
    )

    cache_instance = MagicMock()
    cache_instance.get_min_bid_for_adv_placement_nmid = AsyncMock(return_value=None)
    cache_instance.set_min_bid_for_adv_placement_nmid = AsyncMock()

    with (
        patch.object(WBManager, "wb_manager_hub", PropertyMock(return_value=hub)),
        patch(
            "app.modules.shop_runner.service_manager.services.update_cluster_bids_manager.wb_manager.wb_manager.MinBidsCacheManager",
            return_value=cache_instance,
        ),
    ):
        mgr = WBManager("shop-x")
        out = await mgr.get_min_bids([_make_adv(nmids=[1], auto_id=400)], cache_possible=True)

    assert out.auto[1] == 12
    hub.wb_data_manager.get_min_bids.assert_not_called()
    hub.wb_data_manager.get_min_bids_for_command.assert_awaited_once()


@pytest.mark.asyncio
async def test_api_none_raises() -> None:
    hub = MagicMock()
    hub.wb_data_manager.get_min_bids_for_command = AsyncMock(return_value=None)

    cache_instance = MagicMock()
    cache_instance.get_min_bid_for_adv_placement_nmid = AsyncMock(return_value=None)

    with (
        patch.object(WBManager, "wb_manager_hub", PropertyMock(return_value=hub)),
        patch(
            "app.modules.shop_runner.service_manager.services.update_cluster_bids_manager.wb_manager.wb_manager.MinBidsCacheManager",
            return_value=cache_instance,
        ),
        pytest.raises(ClusterBidsUpdateError),
    ):
        mgr = WBManager("shop-x")
        await mgr.get_min_bids([_make_adv(nmids=[1], auto_id=500)], cache_possible=True)
