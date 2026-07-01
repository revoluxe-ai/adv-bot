"""Unit tests for Redis-first ``PlanFactReader``."""

from __future__ import annotations

import logging
from unittest.mock import AsyncMock, patch

import pytest
from fakeredis.aioredis import FakeRedis

from app.modules.shop_runner.service_manager.services.plan_fact_controller.plan_fact_reader import (
    PLAN_FACT_CACHE_TTL_SECONDS,
    PlanFactCacheManager,
    PlanFactReader,
    PlanFactSummary,
)


pytestmark = pytest.mark.unit


def _reader(fake_redis: FakeRedis) -> PlanFactReader:
    return PlanFactReader(cache_manager=PlanFactCacheManager(redis_client=fake_redis))


def _summary(
    adv_id: int,
    *,
    fact_predict_orders: float = 95.5,
    fact_pay_for_order: float | None = 520.0,
    fact_original_orders: float | None = 90.0,
    fact_method: str | None = "DIRECT_SALES",
    plan_fact_ch_ts_msk: str | None = "02.01.2025 03:04",
) -> PlanFactSummary:
    return PlanFactSummary(
        adv_id=adv_id,
        fact_predict_orders=fact_predict_orders,
        fact_pay_for_order=fact_pay_for_order,
        fact_original_orders=fact_original_orders,
        fact_method=fact_method,
        plan_fact_ch_ts_msk=plan_fact_ch_ts_msk,
    )


@pytest.mark.asyncio
async def test_get_latest_plan_fact_cache_hit_skips_clickhouse(
    fake_redis: FakeRedis,
) -> None:
    reader = _reader(fake_redis)
    cached = _summary(111)
    await reader._cache_manager.set_one(cached)

    with patch.object(
        reader,
        "_query_latest_plan_fact_from_clickhouse",
        new=AsyncMock(return_value=_summary(999)),
    ) as query_mock:
        result = await reader.get_latest_plan_fact(111)

    assert result == cached
    query_mock.assert_not_awaited()


@pytest.mark.asyncio
async def test_get_latest_plan_facts_full_cache_hit_uses_batch_redis_only(
    fake_redis: FakeRedis,
) -> None:
    reader = _reader(fake_redis)
    cached = [_summary(111), _summary(222, fact_predict_orders=180.0)]
    await reader._cache_manager.set_many(cached)

    with patch.object(
        reader,
        "_query_latest_plan_facts_from_clickhouse",
        new=AsyncMock(return_value={}),
    ) as query_mock:
        result = await reader.get_latest_plan_facts([111, 222])

    assert result == {111: cached[0], 222: cached[1]}
    query_mock.assert_not_awaited()


@pytest.mark.asyncio
async def test_get_latest_plan_facts_partial_cache_hit_merges_and_writes_ttl(
    fake_redis: FakeRedis,
) -> None:
    reader = _reader(fake_redis)
    cached = _summary(111)
    missing = _summary(222, fact_predict_orders=180.0, fact_pay_for_order=610.0)
    await reader._cache_manager.set_one(cached)

    with patch.object(
        reader,
        "_query_latest_plan_facts_from_clickhouse",
        new=AsyncMock(return_value={222: missing}),
    ) as query_mock:
        result = await reader.get_latest_plan_facts([111, 222])

    assert result == {111: cached, 222: missing}
    query_mock.assert_awaited_once_with([222])
    ttl = await fake_redis.ttl(reader._cache_manager._get_key(222))
    assert 0 < ttl <= PLAN_FACT_CACHE_TTL_SECONDS


@pytest.mark.asyncio
async def test_get_latest_plan_facts_invalid_payload_is_miss_and_logs(
    fake_redis: FakeRedis,
    caplog: pytest.LogCaptureFixture,
) -> None:
    reader = _reader(fake_redis)
    invalid_key = reader._cache_manager._get_key(222)
    await fake_redis.set(invalid_key, "not-json")
    fallback = _summary(222, fact_predict_orders=200.0)

    caplog.set_level(logging.WARNING)
    with patch.object(
        reader,
        "_query_latest_plan_facts_from_clickhouse",
        new=AsyncMock(return_value={222: fallback}),
    ) as query_mock:
        result = await reader.get_latest_plan_facts([222])

    assert result == {222: fallback}
    query_mock.assert_awaited_once_with([222])
    assert "plan_fact_cache_invalid" in caplog.text


@pytest.mark.asyncio
async def test_get_latest_plan_fact_fallback_success_writes_cache_and_ttl(
    fake_redis: FakeRedis,
) -> None:
    reader = _reader(fake_redis)
    fallback = _summary(111)

    with patch.object(
        reader,
        "_query_latest_plan_fact_from_clickhouse",
        new=AsyncMock(return_value=fallback),
    ):
        result = await reader.get_latest_plan_fact(111)

    assert result == fallback
    ttl = await fake_redis.ttl(reader._cache_manager._get_key(111))
    assert 0 < ttl <= PLAN_FACT_CACHE_TTL_SECONDS


@pytest.mark.asyncio
async def test_get_latest_plan_fact_timeout_returns_none_and_logs(
    fake_redis: FakeRedis,
    caplog: pytest.LogCaptureFixture,
) -> None:
    reader = _reader(fake_redis)
    caplog.set_level(logging.WARNING)

    with patch.object(
        reader,
        "_query_latest_plan_fact_from_clickhouse",
        new=AsyncMock(side_effect=TimeoutError()),
    ):
        result = await reader.get_latest_plan_fact(333)

    assert result is None
    assert "plan_fact_clickhouse_fallback_timeout" in caplog.text


@pytest.mark.asyncio
async def test_get_latest_plan_facts_timeout_returns_cached_partial(
    fake_redis: FakeRedis,
    caplog: pytest.LogCaptureFixture,
) -> None:
    reader = _reader(fake_redis)
    cached = _summary(111)
    await reader._cache_manager.set_one(cached)
    caplog.set_level(logging.WARNING)

    with patch.object(
        reader,
        "_query_latest_plan_facts_from_clickhouse",
        new=AsyncMock(side_effect=TimeoutError()),
    ) as query_mock:
        result = await reader.get_latest_plan_facts([111, 222])

    assert result == {111: cached}
    query_mock.assert_awaited_once_with([222])
    assert "plan_fact_clickhouse_fallback_timeout" in caplog.text


@pytest.mark.asyncio
async def test_get_latest_plan_facts_error_returns_empty_without_cache_write(
    fake_redis: FakeRedis,
    caplog: pytest.LogCaptureFixture,
) -> None:
    reader = _reader(fake_redis)
    caplog.set_level(logging.ERROR)

    with patch.object(
        reader,
        "_query_latest_plan_facts_from_clickhouse",
        new=AsyncMock(side_effect=RuntimeError("ch broken")),
    ):
        result = await reader.get_latest_plan_facts([999])

    assert result == {}
    assert await fake_redis.get(reader._cache_manager._get_key(999)) is None
    assert "plan_fact_clickhouse_fallback_error" in caplog.text


@pytest.mark.asyncio
async def test_refresh_cache_from_clickhouse_writes_shape_reader_reads(
    fake_redis: FakeRedis,
) -> None:
    reader = _reader(fake_redis)
    fresh = {
        111: _summary(111),
        222: _summary(222, fact_predict_orders=180.0, fact_pay_for_order=610.0),
    }

    with patch.object(
        reader,
        "_query_latest_plan_facts_from_clickhouse",
        new=AsyncMock(return_value=fresh),
    ) as query_mock:
        refreshed = await reader.refresh_cache_from_clickhouse([111, 222])

    assert refreshed == fresh
    query_mock.assert_awaited_once_with([111, 222])
    from_cache = await reader.get_latest_plan_facts([111, 222])
    assert from_cache == fresh
    for adv_id in fresh:
        ttl = await fake_redis.ttl(reader._cache_manager._get_key(adv_id))
        assert 0 < ttl <= PLAN_FACT_CACHE_TTL_SECONDS
