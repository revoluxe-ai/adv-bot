import datetime

import pytest
from fakeredis.aioredis import FakeRedis

from app.core.redis_manager_v2.redis_client import RedisClient
from app.modules.shop_runner.wb_statistic_manager.redis_common_stat_timestamp_manager import (
    RedisCommonStatTimestampManager,
)


@pytest.fixture
def redis_client_wrapper(fake_redis: FakeRedis) -> RedisClient:
    return RedisClient(redis_client=fake_redis)


@pytest.fixture
def common_stat_timestamp_manager(
    redis_client_wrapper: RedisClient,
) -> RedisCommonStatTimestampManager:
    return RedisCommonStatTimestampManager(redis_client=redis_client_wrapper)


@pytest.mark.asyncio
async def test_get_returns_none_when_missing(
    common_stat_timestamp_manager: RedisCommonStatTimestampManager,
) -> None:
    assert await common_stat_timestamp_manager.get(adv_id=123) is None


@pytest.mark.asyncio
async def test_set_and_get_roundtrip(
    common_stat_timestamp_manager: RedisCommonStatTimestampManager,
) -> None:
    await common_stat_timestamp_manager.set(adv_id=1)
    value = await common_stat_timestamp_manager.get(adv_id=1)
    assert value is not None
    assert isinstance(value, datetime.datetime)


@pytest.mark.asyncio
async def test_get_returns_none_when_invalid_value(
    common_stat_timestamp_manager: RedisCommonStatTimestampManager,
    fake_redis: FakeRedis,
) -> None:
    key = common_stat_timestamp_manager._get_key(adv_id=777)
    await fake_redis.set(key, "not-a-datetime")
    assert await common_stat_timestamp_manager.get(adv_id=777) is None


@pytest.mark.asyncio
async def test_set_respects_ttl(
    redis_client_wrapper: RedisClient,
    fake_redis: FakeRedis,
) -> None:
    mgr = RedisCommonStatTimestampManager(redis_client=redis_client_wrapper, ttl=5)
    await mgr.set(adv_id=42)
    ttl_value = await fake_redis.ttl(mgr._get_key(adv_id=42))
    assert 0 < ttl_value <= 5



