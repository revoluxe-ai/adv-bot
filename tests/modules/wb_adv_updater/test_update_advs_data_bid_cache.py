"""Тесты дефолтного Redis-кэша ставок полок в update_advs_data_from_wb_to_pg."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.core.redis_manager_v2.redis_client import RedisClient
from app.modules.shop_runner.service_manager.services.auto_shelf_bid_increment_manager.redis_auto_recommendations_bid_value_manager import (
    RedisAutoRecommendationsBidValueManager,
)
from app.modules.wb_adv_updater import data_manager


pytestmark = pytest.mark.unit


@pytest.mark.asyncio
async def test_update_advs_data_uses_default_bid_cache_when_not_passed() -> None:
    wb_api = MagicMock()
    redis_client_wrapper = MagicMock(spec=RedisClient)
    mock_updater = MagicMock()
    mock_updater.update_advs_data = AsyncMock(return_value=[])

    with patch.object(data_manager, "ShopDataUpdater") as updater_cls:
        updater_cls.return_value = mock_updater
        await data_manager.update_advs_data_from_wb_to_pg(
            wb_api,
            redis_client_wrapper=redis_client_wrapper,
        )

    updater_cls.assert_called_once()
    cache_manager = updater_cls.call_args.kwargs["auto_recommendations_bid_cache_manager"]
    assert isinstance(cache_manager, RedisAutoRecommendationsBidValueManager)
    assert cache_manager._client is redis_client_wrapper
    mock_updater.update_advs_data.assert_awaited_once()


@pytest.mark.asyncio
async def test_update_advs_data_keeps_explicit_bid_cache_manager() -> None:
    wb_api = MagicMock()
    redis_client_wrapper = MagicMock(spec=RedisClient)
    explicit_manager = MagicMock(spec=RedisAutoRecommendationsBidValueManager)
    mock_updater = MagicMock()
    mock_updater.update_advs_data = AsyncMock(return_value=[])

    with patch.object(data_manager, "ShopDataUpdater") as updater_cls:
        updater_cls.return_value = mock_updater
        await data_manager.update_advs_data_from_wb_to_pg(
            wb_api,
            auto_recommendations_bid_cache_manager=explicit_manager,
            redis_client_wrapper=redis_client_wrapper,
        )

    cache_manager = updater_cls.call_args.kwargs["auto_recommendations_bid_cache_manager"]
    assert cache_manager is explicit_manager
