"""Поведение _collect_keywords: только Redis, miss → ошибка."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock

import pytest

from app.modules.shop_runner.service_manager.wb_shop_data_manager.wb_shop_data_manager import (
    WBShopDataManager,
)
from app.snapshot_data_updater.cache_freshness import KeywordsCacheMissError


@pytest.mark.unit
@pytest.mark.asyncio
async def test_collect_keywords_raises_on_cache_miss() -> None:
    adv = MagicMock()
    adv.shop_id = "shop-1"
    adv.adv_id = 99
    adv.get_keywords = AsyncMock(return_value=None)

    with pytest.raises(KeywordsCacheMissError, match="cache miss"):
        await WBShopDataManager._collect_keywords(adv)

    adv.get_keywords.assert_awaited_once_with(cache_only=True)


@pytest.mark.unit
@pytest.mark.asyncio
async def test_collect_keywords_returns_redis_hit() -> None:
    kw = MagicMock()
    adv = MagicMock()
    adv.shop_id = "shop-1"
    adv.adv_id = 99
    adv.get_keywords = AsyncMock(return_value=[kw])

    result = await WBShopDataManager._collect_keywords(adv)
    assert result == [kw]
    adv.get_keywords.assert_awaited_once_with(cache_only=True)
