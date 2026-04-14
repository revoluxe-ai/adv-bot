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
