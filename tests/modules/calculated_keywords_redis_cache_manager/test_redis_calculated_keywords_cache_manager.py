"""Unit tests for RedisCalculatedKeywordsCacheManager."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock

import pytest

from app.modules.calculated_keywords_redis_cache_manager.redis_manager import (
    RedisCalculatedKeywordsCacheManager,
)


@pytest.mark.unit
@pytest.mark.asyncio
async def test_get_all_calculated_keywords_for_adv_returns_none_when_key_missing() -> (
    None
):
    mgr = RedisCalculatedKeywordsCacheManager()
    mock_client = MagicMock()
    mock_client.hgetall = AsyncMock(return_value={})
    mgr._client = mock_client

    result = await mgr.get_all_calculated_keywords_for_adv(12345)
    assert result is None
    mock_client.hgetall.assert_awaited_once_with("calculated_keywords:12345")
