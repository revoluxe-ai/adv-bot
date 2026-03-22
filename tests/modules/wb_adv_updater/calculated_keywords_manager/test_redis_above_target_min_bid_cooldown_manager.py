"""Unit tests for RedisAboveTargetMinBidCooldownManager."""

from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock

import pytest

from app.modules.wb_adv_updater.calculated_keywords_manager.redis_above_target_min_bid_cooldown_manager import (
    RedisAboveTargetMinBidCooldownManager,
    normalize_cooldown_keyword_text,
)


@pytest.mark.unit
def test_normalize_cooldown_keyword_text() -> None:
    assert normalize_cooldown_keyword_text("  Foo Бар  ") == "foo бар"


@pytest.mark.asyncio
async def test_get_many_parse_timestamp() -> None:
    inner = MagicMock()
    ts = datetime(2025, 6, 15, 12, 0, 0, tzinfo=timezone.utc).timestamp()
    inner.get = AsyncMock(return_value=str(ts))
    redis_client = MagicMock()
    redis_client.get = inner.get
    redis_client.set = AsyncMock()
    redis_client.delete = AsyncMock()

    mgr = RedisAboveTargetMinBidCooldownManager(redis_client)
    out = await mgr.get_many(42, ["Hello"])
    assert out["Hello"] is not None
    assert abs(out["Hello"].timestamp() - ts) < 0.01


@pytest.mark.asyncio
async def test_apply_updates_set_and_delete() -> None:
    redis_client = MagicMock()
    redis_client.set = AsyncMock()
    redis_client.delete = AsyncMock()

    mgr = RedisAboveTargetMinBidCooldownManager(redis_client)
    at = datetime(2025, 1, 2, 3, 4, 5, tzinfo=timezone.utc)
    await mgr.apply_updates(7, {"a": at, "b": None})

    assert redis_client.set.await_count == 1
    assert redis_client.delete.await_count == 1
