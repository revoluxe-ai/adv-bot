"""Tests for WBManager min bids cache-only read and refresh_min_bids_cache."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, PropertyMock, patch

import pytest

from app.core.mp.wb.dto.adv_min_bids import AdvMinNmidsBids
from app.core.mp.wb.dto.adv_placement_type import AdvPlacementType
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
    cache_instance.get_min_bids_v2_batch = AsyncMock(
        side_effect=lambda cells: {(200, AdvPlacementType.AUTO_ADV, 7): 55}
    )
    cache_instance.set_min_bids_v2_batch = AsyncMock()

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
    cache_instance.set_min_bids_v2_batch.assert_not_called()


@pytest.mark.asyncio
async def test_partial_miss_returns_only_cached_nmids_no_api() -> None:
    hub = MagicMock()
    hub.wb_data_manager.get_min_bids_for_command = AsyncMock(
        return_value=AdvMinNmidsBids(auto={8: 99}, search={}),
    )

    async def cache_batch(
        cells: list[tuple[int, AdvPlacementType, int]],
    ) -> dict[tuple[int, AdvPlacementType, int], int]:
        out: dict[tuple[int, AdvPlacementType, int], int] = {}
        for cell in cells:
            if cell[2] == 7:
                out[cell] = 50
        return out

    cache_instance = MagicMock()
    cache_instance.get_min_bids_v2_batch = AsyncMock(side_effect=cache_batch)
    cache_instance.set_min_bids_v2_batch = AsyncMock()

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

    assert out.auto == {7: 50}
    assert 8 not in out.auto
    hub.wb_data_manager.get_min_bids_for_command.assert_not_called()
    cache_instance.set_min_bids_v2_batch.assert_not_called()


@pytest.mark.asyncio
async def test_full_miss_no_api_empty_auto() -> None:
    hub = MagicMock()
    hub.wb_data_manager.get_min_bids_for_command = AsyncMock(
        return_value=AdvMinNmidsBids(auto={1: 12}, search={}),
    )

    cache_instance = MagicMock()
    cache_instance.get_min_bids_v2_batch = AsyncMock(return_value={})
    cache_instance.set_min_bids_v2_batch = AsyncMock()

    with (
        patch.object(WBManager, "wb_manager_hub", PropertyMock(return_value=hub)),
        patch(
            "app.modules.shop_runner.service_manager.services.update_cluster_bids_manager.wb_manager.wb_manager.MinBidsCacheManager",
            return_value=cache_instance,
        ),
    ):
        mgr = WBManager("shop-x")
        out = await mgr.get_min_bids([_make_adv(nmids=[1], auto_id=400)], cache_possible=True)

    assert out.auto == {}
    hub.wb_data_manager.get_min_bids.assert_not_called()
    hub.wb_data_manager.get_min_bids_for_command.assert_not_called()


@pytest.mark.asyncio
async def test_cache_only_miss_does_not_raise() -> None:
    hub = MagicMock()
    hub.wb_data_manager.get_min_bids_for_command = AsyncMock(return_value=None)

    cache_instance = MagicMock()
    cache_instance.get_min_bids_v2_batch = AsyncMock(return_value={})

    with (
        patch.object(WBManager, "wb_manager_hub", PropertyMock(return_value=hub)),
        patch(
            "app.modules.shop_runner.service_manager.services.update_cluster_bids_manager.wb_manager.wb_manager.MinBidsCacheManager",
            return_value=cache_instance,
        ),
    ):
        mgr = WBManager("shop-x")
        out = await mgr.get_min_bids([_make_adv(nmids=[1], auto_id=500)], cache_possible=True)

    assert out.auto == {}
    hub.wb_data_manager.get_min_bids_for_command.assert_not_called()


@pytest.mark.asyncio
async def test_refresh_min_bids_cache_calls_api_and_batch_write() -> None:
    hub = MagicMock()
    hub.wb_data_manager.get_min_bids_for_command = AsyncMock(
        return_value=AdvMinNmidsBids(auto={7: 40, 8: 41}, search={}),
    )

    cache_instance = MagicMock()
    cache_instance.set_min_bids_v2_batch = AsyncMock()

    with (
        patch.object(WBManager, "wb_manager_hub", PropertyMock(return_value=hub)),
        patch(
            "app.modules.shop_runner.service_manager.services.update_cluster_bids_manager.wb_manager.wb_manager.MinBidsCacheManager",
            return_value=cache_instance,
        ),
    ):
        mgr = WBManager("shop-x")
        await mgr.refresh_min_bids_cache([_make_adv(nmids=[7, 8], auto_id=600)])

    hub.wb_data_manager.get_min_bids_for_command.assert_awaited_once()
    cache_instance.set_min_bids_v2_batch.assert_awaited_once()
    written = cache_instance.set_min_bids_v2_batch.await_args.args[0]
    assert len(written) == 2
    assert (600, AdvPlacementType.AUTO_ADV, 7, 40) in written
    assert (600, AdvPlacementType.AUTO_ADV, 8, 41) in written


@pytest.mark.asyncio
async def test_refresh_min_bids_cache_writes_per_command_item() -> None:
    """auto + search => два WB-вызова и две отдельные записи в Redis по мере получения."""
    hub = MagicMock()
    hub.wb_data_manager.get_min_bids_for_command = AsyncMock(
        side_effect=[
            AdvMinNmidsBids(auto={7: 40}, search={}),
            AdvMinNmidsBids(auto={}, search={7: 50}),
        ],
    )

    cache_instance = MagicMock()
    cache_instance.set_min_bids_v2_batch = AsyncMock()

    with (
        patch.object(WBManager, "wb_manager_hub", PropertyMock(return_value=hub)),
        patch(
            "app.modules.shop_runner.service_manager.services.update_cluster_bids_manager.wb_manager.wb_manager.MinBidsCacheManager",
            return_value=cache_instance,
        ),
    ):
        mgr = WBManager("shop-x")
        await mgr.refresh_min_bids_cache(
            [_make_adv(nmids=[7], auto_id=600, search_id=601)],
        )

    assert hub.wb_data_manager.get_min_bids_for_command.await_count == 2
    assert cache_instance.set_min_bids_v2_batch.await_count == 2
    first_batch = cache_instance.set_min_bids_v2_batch.await_args_list[0].args[0]
    second_batch = cache_instance.set_min_bids_v2_batch.await_args_list[1].args[0]
    assert first_batch == [(600, AdvPlacementType.AUTO_ADV, 7, 40)]
    assert second_batch == [(601, AdvPlacementType.SEARCH_ADV, 7, 50)]


@pytest.mark.asyncio
async def test_get_min_bids_api_none_raises_cluster_bids_update_error() -> None:
    hub = MagicMock()
    hub.wb_data_manager.get_min_bids = AsyncMock(return_value=None)

    with (
        patch.object(WBManager, "wb_manager_hub", PropertyMock(return_value=hub)),
        pytest.raises(ClusterBidsUpdateError),
    ):
        mgr = WBManager("shop-x")
        await mgr.get_min_bids([_make_adv(nmids=[1], auto_id=700)], cache_possible=False)


@pytest.mark.asyncio
async def test_find_min_bids_cache_miss_cells_only_absent_keys() -> None:
    hub = MagicMock()
    hub.wb_data_manager.get_min_bids_for_command = AsyncMock()

    async def cache_batch(
        cells: list[tuple[int, AdvPlacementType, int]],
    ) -> dict[tuple[int, AdvPlacementType, int], int]:
        out: dict[tuple[int, AdvPlacementType, int], int] = {}
        for cell in cells:
            if cell[2] == 7:
                out[cell] = 50
        return out

    cache_instance = MagicMock()
    cache_instance.get_min_bids_v2_batch = AsyncMock(side_effect=cache_batch)

    with (
        patch.object(WBManager, "wb_manager_hub", PropertyMock(return_value=hub)),
        patch(
            "app.modules.shop_runner.service_manager.services.update_cluster_bids_manager.wb_manager.wb_manager.MinBidsCacheManager",
            return_value=cache_instance,
        ),
    ):
        mgr = WBManager("shop-x")
        miss = await mgr.find_min_bids_cache_miss_cells(
            [_make_adv(nmids=[7, 8], auto_id=300)],
        )

    assert miss == [(300, AdvPlacementType.AUTO_ADV, 8)]
    hub.wb_data_manager.get_min_bids_for_command.assert_not_called()


@pytest.mark.asyncio
async def test_refresh_min_bids_cache_miss_cells_batches_one_api_call() -> None:
    hub = MagicMock()
    hub.wb_data_manager.get_min_bids_for_command = AsyncMock(
        return_value=AdvMinNmidsBids(auto={7: 40, 8: 41}, search={}),
    )

    cache_instance = MagicMock()
    cache_instance.set_min_bids_v2_batch = AsyncMock()

    miss_cells = [
        (600, AdvPlacementType.AUTO_ADV, 7),
        (600, AdvPlacementType.AUTO_ADV, 8),
    ]

    with (
        patch.object(WBManager, "wb_manager_hub", PropertyMock(return_value=hub)),
        patch(
            "app.modules.shop_runner.service_manager.services.update_cluster_bids_manager.wb_manager.wb_manager.MinBidsCacheManager",
            return_value=cache_instance,
        ),
    ):
        mgr = WBManager("shop-x")
        written = await mgr.refresh_min_bids_cache_miss_cells(miss_cells)

    assert written == 2
    hub.wb_data_manager.get_min_bids_for_command.assert_awaited_once()
    cache_instance.set_min_bids_v2_batch.assert_awaited_once()
    written_batch = cache_instance.set_min_bids_v2_batch.await_args.args[0]
    assert len(written_batch) == 2
    assert (600, AdvPlacementType.AUTO_ADV, 7, 40) in written_batch
    assert (600, AdvPlacementType.AUTO_ADV, 8, 41) in written_batch


@pytest.mark.asyncio
async def test_refresh_min_bids_cache_miss_cells_splits_on_exception() -> None:
    """Два item: первый падает целиком, второй успешен после split."""

    class Boom(Exception):
        pass

    hub = MagicMock()

    async def get_cmd(cmd) -> AdvMinNmidsBids:
        items = cmd.items
        if len(items) == 2:
            raise Boom("batch")
        if len(items) == 1 and items[0].adv_id == 1:
            raise Boom("bad adv")
        return AdvMinNmidsBids(auto={7: 10}, search={})

    hub.wb_data_manager.get_min_bids_for_command = AsyncMock(side_effect=get_cmd)

    cache_instance = MagicMock()
    cache_instance.set_min_bids_v2_batch = AsyncMock()

    miss_cells = [
        (1, AdvPlacementType.AUTO_ADV, 7),
        (2, AdvPlacementType.AUTO_ADV, 7),
    ]

    with (
        patch.object(WBManager, "wb_manager_hub", PropertyMock(return_value=hub)),
        patch(
            "app.modules.shop_runner.service_manager.services.update_cluster_bids_manager.wb_manager.wb_manager.MinBidsCacheManager",
            return_value=cache_instance,
        ),
    ):
        mgr = WBManager("shop-x")
        written = await mgr.refresh_min_bids_cache_miss_cells(miss_cells)

    assert written == 1
    cache_instance.set_min_bids_v2_batch.assert_awaited_once()
    batch = cache_instance.set_min_bids_v2_batch.await_args.args[0]
    assert batch == [(2, AdvPlacementType.AUTO_ADV, 7, 10)]


@pytest.mark.asyncio
async def test_refresh_min_bids_cache_miss_cells_splits_nmids_on_none() -> None:
    """Один item с двумя nmid: None на всей пачке, после split по nmid один успех."""

    hub = MagicMock()
    calls: list[int] = []

    async def get_cmd(cmd) -> AdvMinNmidsBids | None:
        calls.append(len(cmd.items[0].nmids))
        if len(cmd.items[0].nmids) == 2:
            return None
        if cmd.items[0].nmids == [7]:
            return AdvMinNmidsBids(auto={7: 11}, search={})
        return None

    hub.wb_data_manager.get_min_bids_for_command = AsyncMock(side_effect=get_cmd)

    cache_instance = MagicMock()
    cache_instance.set_min_bids_v2_batch = AsyncMock()

    miss_cells = [
        (600, AdvPlacementType.AUTO_ADV, 7),
        (600, AdvPlacementType.AUTO_ADV, 8),
    ]

    with (
        patch.object(WBManager, "wb_manager_hub", PropertyMock(return_value=hub)),
        patch(
            "app.modules.shop_runner.service_manager.services.update_cluster_bids_manager.wb_manager.wb_manager.MinBidsCacheManager",
            return_value=cache_instance,
        ),
    ):
        mgr = WBManager("shop-x")
        written = await mgr.refresh_min_bids_cache_miss_cells(miss_cells)

    assert written == 1
    assert calls == [2, 1, 1]
    cache_instance.set_min_bids_v2_batch.assert_awaited_once()
    assert cache_instance.set_min_bids_v2_batch.await_args.args[0] == [
        (600, AdvPlacementType.AUTO_ADV, 7, 11),
    ]
