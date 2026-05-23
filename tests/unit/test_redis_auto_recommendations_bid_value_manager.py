from __future__ import annotations

from datetime import datetime

import pytest
from fakeredis.aioredis import FakeRedis

from app.core.redis_manager_v2.redis_client import RedisClient
from app.modules.shop_runner.service_manager.services.auto_shelf_bid_increment_manager.redis_auto_recommendations_bid_value_manager import (
    RedisAutoRecommendationsBidValueManager,
)


pytestmark = pytest.mark.unit


@pytest.fixture
def redis_client_wrapper(fake_redis: FakeRedis) -> RedisClient:
    return RedisClient(redis_client=fake_redis)


@pytest.fixture
def manager(
    redis_client_wrapper: RedisClient,
) -> RedisAutoRecommendationsBidValueManager:
    return RedisAutoRecommendationsBidValueManager(redis_client=redis_client_wrapper)


@pytest.mark.asyncio
async def test_set_and_get_bid_roundtrip(
    manager: RedisAutoRecommendationsBidValueManager,
) -> None:
    await manager.set_bids(auto_adv_id=1001, bids={111: 1500})

    cached = await manager.get_bid(auto_adv_id=1001, nmid=111)

    assert cached is not None
    assert cached.bid_minor == 1500
    assert isinstance(cached.updated_at, datetime)


@pytest.mark.asyncio
async def test_get_bids_returns_only_valid(
    manager: RedisAutoRecommendationsBidValueManager,
    fake_redis: FakeRedis,
) -> None:
    valid_key = manager._get_key(1001, 111)
    invalid_key = manager._get_key(1001, 222)
    await manager.set_bids(auto_adv_id=1001, bids={111: 1700})
    await fake_redis.set(invalid_key, "not-json")

    result = await manager.get_bids(auto_adv_id=1001, nmids=[111, 222, 333])

    assert set(result.keys()) == {111}
    assert result[111].bid_minor == 1700
    assert isinstance(result[111].updated_at, datetime)
    raw = await fake_redis.get(valid_key)
    assert raw is not None


@pytest.mark.asyncio
async def test_set_bids_respects_ttl(
    redis_client_wrapper: RedisClient,
    fake_redis: FakeRedis,
) -> None:
    manager = RedisAutoRecommendationsBidValueManager(
        redis_client=redis_client_wrapper,
        ttl=5,
    )
    await manager.set_bids(auto_adv_id=1, bids={10: 1200})

    ttl = await fake_redis.ttl(manager._get_key(1, 10))
    assert 0 < ttl <= 5

