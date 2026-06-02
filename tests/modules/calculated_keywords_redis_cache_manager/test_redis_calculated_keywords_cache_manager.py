"""Unit tests for RedisCalculatedKeywordsCacheManager."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock

import pytest

from app.modules.calculated_keywords_redis_cache_manager.redis_manager import (
    RedisCalculatedKeywordsCacheManager,
    _CALCULATED_KEYWORDS_EMPTY_FIELD,
)


@pytest.mark.unit
@pytest.mark.asyncio
async def test_get_all_calculated_keywords_for_adv_returns_none_when_key_missing() -> (
    None
):
    mgr = RedisCalculatedKeywordsCacheManager()
    mock_client = MagicMock()
    mock_client.exists = AsyncMock(return_value=0)
    mock_client.hgetall = AsyncMock(return_value={})
    mgr._client = mock_client

    result = await mgr.get_all_calculated_keywords_for_adv(12345)
    assert result is None
    mock_client.exists.assert_awaited_once_with("calculated_keywords:12345")
    mock_client.hgetall.assert_not_awaited()


@pytest.mark.unit
@pytest.mark.asyncio
async def test_get_all_returns_empty_list_when_empty_marker_present() -> None:
    mgr = RedisCalculatedKeywordsCacheManager()
    mock_client = MagicMock()
    mock_client.exists = AsyncMock(return_value=1)
    mock_client.hgetall = AsyncMock(
        return_value={_CALCULATED_KEYWORDS_EMPTY_FIELD: b"1"}
    )
    mgr._client = mock_client

    result = await mgr.get_all_calculated_keywords_for_adv(99)
    assert result == []


@pytest.mark.unit
@pytest.mark.asyncio
async def test_set_calculated_keywords_empty_writes_marker() -> None:
    mgr = RedisCalculatedKeywordsCacheManager()
    pipe = MagicMock()
    pipe.delete = MagicMock(return_value=pipe)
    pipe.hset = MagicMock(return_value=pipe)
    pipe.expire = MagicMock(return_value=pipe)
    pipe.execute = AsyncMock(return_value=[1, 1])

    class _PipeCtx:
        async def __aenter__(self) -> MagicMock:
            return pipe

        async def __aexit__(self, *_: object) -> None:
            return None

    mock_client = MagicMock()
    mock_client.pipeline = MagicMock(return_value=_PipeCtx())
    mgr._client = mock_client

    await mgr.set_calculated_keywords([], adv_id=77)

    pipe.delete.assert_called_once_with("calculated_keywords:77")
    pipe.hset.assert_called_once_with(
        name="calculated_keywords:77",
        key=_CALCULATED_KEYWORDS_EMPTY_FIELD,
        value="1",
    )
    pipe.expire.assert_called_once()
    assert pipe.expire.call_args[0][0] == "calculated_keywords:77"
    assert pipe.expire.call_args[0][1] > 0
    pipe.execute.assert_awaited_once()
