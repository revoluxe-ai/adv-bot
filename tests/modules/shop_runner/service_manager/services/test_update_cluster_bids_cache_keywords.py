"""Тесты cache-only получения ключей в UpdateClusterBidsManager."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock

import pytest

from app.core.mp.wb.api.adapter.promotion_client.normquery_bids.dto import NormqueryBidDTO
from app.modules.shop_runner.service_manager.services.update_cluster_bids_manager.mappers.adv_id_item_map import (
    AdvIdItemCalculateData,
)
from app.modules.shop_runner.service_manager.services.update_cluster_bids_manager.update_cluster_bids_manager import (
    UpdateClusterBidsManager,
)
from tests.factories.keyword_pipeline import GoodKeywordFactory


@pytest.mark.unit
@pytest.mark.asyncio
async def test_get_calculate_data_returns_empty_on_keywords_cache_miss() -> None:
    manager = UpdateClusterBidsManager(
        wb_manager=MagicMock(),
        redis_keyword_bidder_status_manager=MagicMock(),
        redis_cluster_bids_manager=MagicMock(),
        redis_api_cluster_bids_manager=MagicMock(),
        redis_cluster_bids_timestamp_manager=MagicMock(),
    )
    adv = MagicMock()
    adv.auction_adv_id = 10
    adv.adv_id = 1
    adv.get_keywords = AsyncMock(return_value=None)

    result = await manager._UpdateClusterBidsManager__get_calculate_data(
        adv, set()
    )
    assert result == set()
    adv.get_keywords.assert_awaited_once_with(cache_only=True)


@pytest.mark.unit
@pytest.mark.asyncio
@pytest.mark.parametrize("adv_target_place", [99, None])
async def test_get_calculate_data_individual_mode_no_kw_target_snap_ignores_adv_target_place(
    adv_target_place: int | None,
) -> None:
    """Нет target_place у ключа: snap, target_position=None, цель РК в карту не попадает."""
    manager = UpdateClusterBidsManager(
        wb_manager=MagicMock(),
        redis_keyword_bidder_status_manager=MagicMock(),
        redis_cluster_bids_manager=MagicMock(),
        redis_api_cluster_bids_manager=MagicMock(),
        redis_cluster_bids_timestamp_manager=MagicMock(),
    )
    cluster_text = "normquery_snap_test"
    kw = GoodKeywordFactory.build(
        keyword_setting__text=cluster_text,
        keyword_setting__target_place=None,
        cluster_stat__norm_query=cluster_text,
    )
    adv = MagicMock()
    adv.auction_adv_id = 10
    adv.adv_id = 1
    adv.nmids = [200]
    adv.individual_keywords_target_place_mode = True
    adv.target_place = adv_target_place
    adv.max_user_cpm = 500
    adv.bid_cpm_step = 10
    adv.get_keywords = AsyncMock(return_value=[kw])

    result = await manager._UpdateClusterBidsManager__get_calculate_data(
        adv, {cluster_text}
    )

    assert len(result) == 1
    (md,) = tuple(result)
    assert md.snap_to_min_bid_no_keyword_target is True
    assert md.target_position is None
    assert md.nmid == 200
    assert md.cluster == cluster_text
    if adv_target_place is not None:
        assert md.target_position is not adv_target_place


@pytest.mark.unit
@pytest.mark.asyncio
async def test_get_fact_datas_uses_batch_plan_fact_reader_once(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    manager = UpdateClusterBidsManager(
        wb_manager=MagicMock(),
        redis_keyword_bidder_status_manager=MagicMock(),
        redis_cluster_bids_manager=MagicMock(),
        redis_api_cluster_bids_manager=MagicMock(),
        redis_cluster_bids_timestamp_manager=MagicMock(),
    )
    adv1 = MagicMock()
    adv1.adv_id = 101
    adv1.adv_setting = MagicMock()
    adv2 = MagicMock()
    adv2.adv_id = 202
    adv2.adv_setting = MagicMock()

    batch_mock = AsyncMock(return_value={})
    single_mock = AsyncMock(return_value=None)
    monkeypatch.setattr(
        "app.modules.shop_runner.service_manager.services.update_cluster_bids_manager.update_cluster_bids_manager.PlanFactReader.get_latest_plan_facts",
        batch_mock,
    )
    monkeypatch.setattr(
        "app.modules.shop_runner.service_manager.services.update_cluster_bids_manager.update_cluster_bids_manager.PlanFactReader.get_latest_plan_fact",
        single_mock,
    )

    result = await manager._get_fact_datas([adv1, adv2])

    assert result == {}
    batch_mock.assert_awaited_once_with([101, 202])
    single_mock.assert_not_awaited()


@pytest.mark.unit
@pytest.mark.asyncio
async def test_get_cluster_bids_for_maps_fetches_wb_on_redis_miss() -> None:
    """Cold Redis API cache: WB fills bids and warms Redis (same as cache_current_cluster_bids)."""
    api_cache = MagicMock()
    api_cache.get_bids = AsyncMock(return_value={})
    api_cache.replace_from_api = AsyncMock(return_value=1)

    wb_manager = MagicMock()
    wb_manager.get_current_bids = AsyncMock(
        return_value=[
            NormqueryBidDTO(
                advert_id=100,
                nm_id=1,
                norm_query="q1",
                bid=42,
            )
        ]
    )

    manager = UpdateClusterBidsManager(
        wb_manager=wb_manager,
        redis_keyword_bidder_status_manager=MagicMock(),
        redis_cluster_bids_manager=MagicMock(),
        redis_api_cluster_bids_manager=api_cache,
        redis_cluster_bids_timestamp_manager=MagicMock(),
    )

    map_data = AdvIdItemCalculateData(
        adv_id=100,
        nmid=1,
        cluster="q1",
        current_position=1.0,
        target_position=5,
        max_cpm=500,
        step=10,
        current_cpm=None,
    )
    adv = MagicMock()
    adv.auction_adv_id = 100

    result = await manager._get_cluster_bids_for_maps({map_data}, [adv])

    assert len(result) == 1
    assert result[0].bid == 42
    wb_manager.get_current_bids.assert_awaited_once_with([adv])
    api_cache.replace_from_api.assert_awaited_once()
