"""Тесты cache-only получения ключей в UpdateClusterBidsManager."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock

import pytest

from app.modules.shop_runner.service_manager.services.update_cluster_bids_manager.update_cluster_bids_manager import (
    UpdateClusterBidsManager,
)


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
async def test_get_fact_data_returns_none_on_keywords_cache_miss() -> None:
    manager = UpdateClusterBidsManager(
        wb_manager=MagicMock(),
        redis_keyword_bidder_status_manager=MagicMock(),
        redis_cluster_bids_manager=MagicMock(),
        redis_api_cluster_bids_manager=MagicMock(),
        redis_cluster_bids_timestamp_manager=MagicMock(),
    )
    adv = MagicMock()
    adv.adv_id = 42
    adv.get_keywords = AsyncMock(return_value=None)

    result = await manager._UpdateClusterBidsManager__get_fact_data(adv)
    assert result is None
    adv.get_keywords.assert_awaited_once_with(cache_only=True)
