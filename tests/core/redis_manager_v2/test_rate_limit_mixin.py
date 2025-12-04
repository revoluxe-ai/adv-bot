# import pytest
# from fakeredis import aioredis as fake_aioredis
#
# from app.core.redis_manager_v2.redis_client import RedisClient
# from app.core.redis_manager_v2.mixins import RateLimitMixin
# from app.core.redis_manager_v2 import BaseRedisManager
#
#
# class TestRateLimitRedisManager(RateLimitMixin, BaseRedisManager):
#     prefix = "test_wb_rate_limit"
#
#     def _get_key(self, ip: str) -> str:  # type: ignore[override]
#         return f"{self.prefix}:{ip}"
#
#
# @pytest.fixture
# async def redis_client():
#     fake_redis = await fake_aioredis.FakeRedis().initialize()
#     yield RedisClient(fake_redis)
#     await fake_redis.close()
#
#
# @pytest.fixture
# def rate_limit_manager(redis_client):
#     return TestRateLimitRedisManager(redis_client=redis_client)
#
#
# @pytest.mark.asyncio
# async def test_is_ip_blocked_returns_false_when_no_block(rate_limit_manager):
#     blocked, ttl = await rate_limit_manager.is_ip_blocked("192.168.1.1")
#     assert blocked is False
#     assert ttl == 0.0
#
#
# @pytest.mark.asyncio
# async def test_block_ip_creates_block(rate_limit_manager):
#     ip = "192.168.1.1"
#     await rate_limit_manager.block_ip(ip, 1.0)
#
#     blocked, ttl = await rate_limit_manager.is_ip_blocked(ip)
#     assert blocked is True
#     assert 0.9 < ttl <= 1.0
#
#
# @pytest.mark.asyncio
# async def test_delete_block_removes_block(rate_limit_manager):
#     ip = "192.168.1.1"
#     await rate_limit_manager.block_ip(ip, 10.0)
#     await rate_limit_manager.delete_block(ip)
#
#     blocked, ttl = await rate_limit_manager.is_ip_blocked(ip)
#     assert blocked is False
#     assert ttl == 0.0
#
#
# @pytest.mark.asyncio
# async def test_refresh_block_updates_ttl(rate_limit_manager):
#     ip = "192.168.1.1"
#     await rate_limit_manager.block_ip(ip, 1.0)
#     await rate_limit_manager.refresh_block(ip, 5.0)
#
#     blocked, ttl = await rate_limit_manager.is_ip_blocked(ip)
#     assert blocked is True
#     assert 4.8 < ttl <= 5.0
#
#
# @pytest.mark.asyncio
# async def test_refresh_block_creates_if_not_exists(rate_limit_manager):
#     ip = "192.168.1.1"
#     await rate_limit_manager.refresh_block(ip, 3.0)
#
#     blocked, ttl = await rate_limit_manager.is_ip_blocked(ip)
#     assert blocked is True
#     assert 2.8 < ttl <= 3.0
#
#
# @pytest.mark.asyncio
# async def test_block_ip_with_fractional_seconds(rate_limit_manager):
#     ip = "192.168.1.1"
#     await rate_limit_manager.block_ip(ip, 0.5)
#
#     blocked, ttl = await rate_limit_manager.is_ip_blocked(ip)
#     assert blocked is True
#     assert ttl > 0
#
#
# @pytest.mark.asyncio
# async def test_multiple_ips_independent(rate_limit_manager):
#     ip1 = "192.168.1.1"
#     ip2 = "192.168.1.2"
#
#     await rate_limit_manager.block_ip(ip1, 2.0)
#
#     blocked1, _ = await rate_limit_manager.is_ip_blocked(ip1)
#     blocked2, _ = await rate_limit_manager.is_ip_blocked(ip2)
#
#     assert blocked1 is True
#     assert blocked2 is False
#
#
#
#
#
