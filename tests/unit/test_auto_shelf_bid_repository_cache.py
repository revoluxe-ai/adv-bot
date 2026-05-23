from __future__ import annotations

from datetime import datetime, timedelta
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock

import pytest

from app.modules.shop_runner.service_manager.services.auto_shelf_bid_increment_manager.auto_shelf_bid_repository import (
    AutoShelfBidRepository,
)
from app.modules.shop_runner.service_manager.services.auto_shelf_bid_increment_manager.redis_auto_recommendations_bid_value_manager import (
    AutoRecommendationsBidCacheValue,
)


pytestmark = pytest.mark.unit


def _build_adv(auto_adv_id: int = 1001) -> SimpleNamespace:
    return SimpleNamespace(auto_adv_id=auto_adv_id, adv_id=auto_adv_id)


@pytest.mark.asyncio
async def test_fetch_current_auto_common_bid_returns_cache_value() -> None:
    cache = MagicMock()
    now = datetime.now()
    cache.get_bid = AsyncMock(
        return_value=AutoRecommendationsBidCacheValue(bid_minor=1550, updated_at=now)
    )
    repository = AutoShelfBidRepository(
        wb_manager_hub=MagicMock(),
        auto_recommendations_bid_cache_manager=cache,
    )

    bid = await repository.fetch_current_auto_common_bid(_build_adv(), nmid=111)

    assert bid == 1550
    cache.get_bid.assert_awaited_once_with(1001, 111)


@pytest.mark.asyncio
async def test_fetch_current_auto_common_bid_returns_none_on_cache_miss() -> None:
    cache = MagicMock()
    cache.get_bid = AsyncMock(return_value=None)
    repository = AutoShelfBidRepository(
        wb_manager_hub=MagicMock(),
        auto_recommendations_bid_cache_manager=cache,
    )

    bid = await repository.fetch_current_auto_common_bid(_build_adv(), nmid=111)

    assert bid is None


@pytest.mark.asyncio
async def test_fetch_current_auto_common_bid_returns_none_when_cache_stale() -> None:
    cache = MagicMock()
    cache.get_bid = AsyncMock(
        return_value=AutoRecommendationsBidCacheValue(
            bid_minor=1550,
            updated_at=datetime.now() - timedelta(minutes=10),
        )
    )
    repository = AutoShelfBidRepository(
        wb_manager_hub=MagicMock(),
        auto_recommendations_bid_cache_manager=cache,
        max_bid_age_sec=60,
    )

    bid = await repository.fetch_current_auto_common_bid(_build_adv(), nmid=111)

    assert bid is None

