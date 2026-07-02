"""Unit tests for Redis-first ``PlanFactReader``."""

from __future__ import annotations

import asyncio
import logging
from unittest.mock import AsyncMock, patch

import pytest
from fakeredis.aioredis import FakeRedis

from app.core.redis_manager_v2.redis_client import RedisClient
from app.modules.shop_runner.service_manager.services.plan_fact_controller.plan_fact_reader import (
    PLAN_FACT_CACHE_TTL_SECONDS,
    PlanFactCacheManager,
    PlanFactReader,
    PlanFactSummary,
)


pytestmark = pytest.mark.unit


def _reader(fake_redis: FakeRedis) -> PlanFactReader:
    redis_client = RedisClient(redis_client=fake_redis)
    return PlanFactReader(cache_manager=PlanFactCacheManager(redis_client=redis_client))


def _reader_with_redis_client(redis_client: object) -> PlanFactReader:
    return PlanFactReader(
        cache_manager=PlanFactCacheManager(redis_client=redis_client)  # type: ignore[arg-type]
    )


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


class _FailingRedisClient:
    def __init__(self, *, read_exc: Exception | None = None) -> None:
        self._read_exc = read_exc or RuntimeError("redis read failed")

    async def get(self, key: str) -> str | None:
        raise self._read_exc

    async def mget(self, keys: list[str]) -> list[str | None]:
        raise self._read_exc

    async def set(
        self,
        key: str,
        value: str,
        ex: int | None = None,
    ) -> bool:
        return True

    def write_pipeline(self) -> "_SuccessfulPipeline":
        return _SuccessfulPipeline()


class _WriteFailingRedisClient:
    def __init__(self, *, write_exc: Exception | None = None) -> None:
        self._write_exc = write_exc or RuntimeError("redis write failed")

    async def get(self, key: str) -> str | None:
        return None

    async def mget(self, keys: list[str]) -> list[str | None]:
        return [None for _ in keys]

    async def set(
        self,
        key: str,
        value: str,
        ex: int | None = None,
    ) -> bool:
        raise self._write_exc

    def write_pipeline(self) -> "_FailingPipeline":
        return _FailingPipeline(self._write_exc)


class _SuccessfulPipeline:
    async def __aenter__(self) -> "_SuccessfulPipeline":
        return self

    async def __aexit__(self, *args: object) -> None:
        return None

    def set(self, key: str, value: str, ex: int | None = None) -> None:
        return None

    async def execute(self) -> list[object]:
        return []


class _FailingPipeline:
    def __init__(self, exc: Exception) -> None:
        self._exc = exc

    async def __aenter__(self) -> "_FailingPipeline":
        return self

    async def __aexit__(self, *args: object) -> None:
        return None

    def set(self, key: str, value: str, ex: int | None = None) -> None:
        return None

    async def execute(self) -> list[object]:
        raise self._exc


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
async def test_get_latest_plan_fact_redis_read_error_uses_clickhouse(
    caplog: pytest.LogCaptureFixture,
) -> None:
    reader = _reader_with_redis_client(_FailingRedisClient())
    fallback = _summary(111)
    caplog.set_level(logging.ERROR)

    with patch.object(
        reader,
        "_query_latest_plan_fact_from_clickhouse",
        new=AsyncMock(return_value=fallback),
    ) as query_mock:
        result = await reader.get_latest_plan_fact(111)

    assert result == fallback
    query_mock.assert_awaited_once_with(111)
    assert "plan_fact_cache_read_error" in caplog.text


@pytest.mark.asyncio
async def test_get_latest_plan_fact_redis_read_error_and_ch_timeout_returns_none(
    caplog: pytest.LogCaptureFixture,
) -> None:
    reader = _reader_with_redis_client(_FailingRedisClient())
    caplog.set_level(logging.WARNING)

    with patch.object(
        reader,
        "_query_latest_plan_fact_from_clickhouse",
        new=AsyncMock(side_effect=TimeoutError()),
    ):
        result = await reader.get_latest_plan_fact(111)

    assert result is None
    assert "plan_fact_cache_read_error" in caplog.text
    assert "plan_fact_clickhouse_fallback_timeout" in caplog.text


@pytest.mark.asyncio
async def test_get_latest_plan_fact_redis_read_timeout_uses_clickhouse(
    caplog: pytest.LogCaptureFixture,
) -> None:
    reader = _reader_with_redis_client(
        _FailingRedisClient(read_exc=asyncio.TimeoutError())
    )
    fallback = _summary(111)
    caplog.set_level(logging.WARNING)

    with patch.object(
        reader,
        "_query_latest_plan_fact_from_clickhouse",
        new=AsyncMock(return_value=fallback),
    ):
        result = await reader.get_latest_plan_fact(111)

    assert result == fallback
    assert "plan_fact_cache_read_timeout" in caplog.text


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
async def test_get_latest_plan_facts_redis_mget_error_uses_clickhouse(
    caplog: pytest.LogCaptureFixture,
) -> None:
    reader = _reader_with_redis_client(_FailingRedisClient())
    fallback = {111: _summary(111), 222: _summary(222)}
    caplog.set_level(logging.ERROR)

    with patch.object(
        reader,
        "_query_latest_plan_facts_from_clickhouse",
        new=AsyncMock(return_value=fallback),
    ) as query_mock:
        result = await reader.get_latest_plan_facts([111, 222])

    assert result == fallback
    query_mock.assert_awaited_once_with([111, 222])
    assert "plan_fact_cache_read_error" in caplog.text


@pytest.mark.asyncio
async def test_get_latest_plan_facts_redis_mget_error_and_ch_timeout_returns_empty(
    caplog: pytest.LogCaptureFixture,
) -> None:
    reader = _reader_with_redis_client(_FailingRedisClient())
    caplog.set_level(logging.WARNING)

    with patch.object(
        reader,
        "_query_latest_plan_facts_from_clickhouse",
        new=AsyncMock(side_effect=TimeoutError()),
    ):
        result = await reader.get_latest_plan_facts([111, 222])

    assert result == {}
    assert "plan_fact_cache_read_error" in caplog.text
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
async def test_get_latest_plan_fact_ch_success_redis_write_error_returns_ch_data(
    caplog: pytest.LogCaptureFixture,
) -> None:
    reader = _reader_with_redis_client(_WriteFailingRedisClient())
    fallback = _summary(111)
    caplog.set_level(logging.ERROR)

    with patch.object(
        reader,
        "_query_latest_plan_fact_from_clickhouse",
        new=AsyncMock(return_value=fallback),
    ):
        result = await reader.get_latest_plan_fact(111)

    assert result == fallback
    assert "plan_fact_cache_write_error" in caplog.text


@pytest.mark.asyncio
async def test_get_latest_plan_facts_pipeline_execute_timeout_returns_ch_data(
    caplog: pytest.LogCaptureFixture,
) -> None:
    reader = _reader_with_redis_client(
        _WriteFailingRedisClient(write_exc=asyncio.TimeoutError())
    )
    fallback = {111: _summary(111), 222: _summary(222)}
    caplog.set_level(logging.WARNING)

    with patch.object(
        reader,
        "_query_latest_plan_facts_from_clickhouse",
        new=AsyncMock(return_value=fallback),
    ):
        result = await reader.get_latest_plan_facts([111, 222])

    assert result == fallback
    assert "plan_fact_cache_write_timeout" in caplog.text


@pytest.mark.asyncio
async def test_refresh_cache_from_clickhouse_writes_shape_reader_reads(
    fake_redis: FakeRedis,
    caplog: pytest.LogCaptureFixture,
) -> None:
    reader = _reader(fake_redis)
    fresh = {
        111: _summary(111),
        222: _summary(222, fact_predict_orders=180.0, fact_pay_for_order=610.0),
    }
    caplog.set_level(logging.DEBUG)

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
    assert "plan_fact_warmup_success" in caplog.text
    for adv_id in fresh:
        ttl = await fake_redis.ttl(reader._cache_manager._get_key(adv_id))
        assert 0 < ttl <= PLAN_FACT_CACHE_TTL_SECONDS


@pytest.mark.asyncio
async def test_refresh_cache_from_clickhouse_write_error_does_not_escape(
    caplog: pytest.LogCaptureFixture,
) -> None:
    reader = _reader_with_redis_client(_WriteFailingRedisClient())
    fresh = {111: _summary(111)}
    caplog.set_level(logging.ERROR)

    with patch.object(
        reader,
        "_query_latest_plan_facts_from_clickhouse",
        new=AsyncMock(return_value=fresh),
    ):
        refreshed = await reader.refresh_cache_from_clickhouse([111])

    assert refreshed == fresh
    assert "plan_fact_cache_write_error" in caplog.text


@pytest.mark.asyncio
async def test_refresh_cache_from_clickhouse_handles_empty_result(
    fake_redis: FakeRedis,
    caplog: pytest.LogCaptureFixture,
) -> None:
    reader = _reader(fake_redis)
    caplog.set_level(logging.DEBUG)

    with patch.object(
        reader,
        "_query_latest_plan_facts_from_clickhouse",
        new=AsyncMock(return_value={}),
    ) as query_mock:
        refreshed = await reader.refresh_cache_from_clickhouse([333])

    assert refreshed == {}
    query_mock.assert_awaited_once_with([333])
    assert await fake_redis.get(reader._cache_manager._get_key(333)) is None
    assert "plan_fact_warmup_success" in caplog.text


@pytest.mark.asyncio
async def test_refresh_cache_from_clickhouse_timeout_returns_empty(
    fake_redis: FakeRedis,
    caplog: pytest.LogCaptureFixture,
) -> None:
    reader = _reader(fake_redis)
    caplog.set_level(logging.WARNING)

    with patch.object(
        reader,
        "_query_latest_plan_facts_from_clickhouse",
        new=AsyncMock(side_effect=TimeoutError()),
    ):
        refreshed = await reader.refresh_cache_from_clickhouse([444])

    assert refreshed == {}
    assert await fake_redis.get(reader._cache_manager._get_key(444)) is None
    assert "plan_fact_warmup_timeout" in caplog.text


@pytest.mark.asyncio
async def test_refresh_cache_from_clickhouse_error_returns_empty(
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
        refreshed = await reader.refresh_cache_from_clickhouse([555])

    assert refreshed == {}
    assert await fake_redis.get(reader._cache_manager._get_key(555)) is None
    assert "plan_fact_warmup_error" in caplog.text
