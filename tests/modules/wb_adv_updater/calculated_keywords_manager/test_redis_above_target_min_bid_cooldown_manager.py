"""Unit tests for RedisAboveTargetMinBidCooldownManager."""

import json
from datetime import UTC, datetime
from unittest.mock import AsyncMock, MagicMock

import pytest

from app.modules.wb_adv_updater.calculated_keywords_manager.above_target_cooldown_entry import (
    AboveTargetCooldownEntry,
)
from app.modules.wb_adv_updater.calculated_keywords_manager.redis_above_target_min_bid_cooldown_manager import (
    RedisAboveTargetMinBidCooldownManager,
)


@pytest.mark.asyncio
async def test_get_many_parse_json_and_legacy_float() -> None:
    ts = datetime(2025, 6, 15, 12, 0, 0, tzinfo=UTC).timestamp()
    payload_json = json.dumps({"t": ts, "v": 42}, separators=(",", ":"))

    redis_client = MagicMock()
    redis_client.mget = AsyncMock(return_value=[payload_json])

    mgr = RedisAboveTargetMinBidCooldownManager(redis_client)
    out = await mgr.get_many(42, ["Hello"])
    assert out["Hello"] is not None
    assert out["Hello"].views_at_freeze == 42
    assert abs(out["Hello"].last_disabled_at.timestamp() - ts) < 0.01

    redis_client.mget = AsyncMock(return_value=[str(ts)])
    out2 = await mgr.get_many(1, ["x"])
    assert out2["x"] is not None
    assert out2["x"].views_at_freeze == 0


@pytest.mark.asyncio
async def test_apply_updates_set_and_delete() -> None:
    redis_client = MagicMock()
    redis_client.set = AsyncMock()
    redis_client.delete = AsyncMock()

    mgr = RedisAboveTargetMinBidCooldownManager(redis_client)
    at = datetime(2025, 1, 2, 3, 4, 5, tzinfo=UTC)
    entry = AboveTargetCooldownEntry(at, 1000)
    await mgr.apply_updates(7, {"a": entry, "b": None})

    assert redis_client.set.await_count == 1
    assert redis_client.delete.await_count == 1
    set_args = redis_client.set.call_args[0]
    assert json.loads(set_args[1])["v"] == 1000
