from __future__ import annotations

from datetime import datetime, timedelta, timezone
from unittest.mock import AsyncMock

import pytest
from zoneinfo import ZoneInfo

from app.modules.shop_runner.service_manager.services.increment_fact_data_manager.bucket_calculator import (
    BucketCalculator,
)
from app.modules.shop_runner.service_manager.services.increment_fact_data_manager.redis_lock_manager import (
    RedisLockManager,
)
from app.modules.shop_runner.service_manager.services.increment_fact_data_manager.version_calculator import (
    VersionCalculator,
)


def test_bucket_calculator_rounds_to_15_minutes() -> None:
    calculator = BucketCalculator()
    test_cases = [
        (
            datetime(2026, 2, 1, 8, 14, tzinfo=timezone.utc),
            datetime(2026, 2, 1, 11, 0, tzinfo=ZoneInfo("Europe/Moscow")),
        ),
        (
            datetime(2026, 2, 1, 8, 15, tzinfo=timezone.utc),
            datetime(2026, 2, 1, 11, 15, tzinfo=ZoneInfo("Europe/Moscow")),
        ),
        (
            datetime(2026, 2, 1, 9, 59, tzinfo=timezone.utc),
            datetime(2026, 2, 1, 12, 45, tzinfo=ZoneInfo("Europe/Moscow")),
        ),
        (
            datetime(2026, 2, 1, 10, 7, tzinfo=timezone.utc),
            datetime(2026, 2, 1, 13, 0, tzinfo=ZoneInfo("Europe/Moscow")),
        ),
    ]

    for src_ts, expected in test_cases:
        bucket = calculator.calc_bucket_start(src_ts)
        assert bucket == expected


def test_version_calculator_monotonic() -> None:
    base = datetime(2026, 2, 1, 0, 0, tzinfo=timezone.utc)
    later = base + timedelta(milliseconds=42)
    assert VersionCalculator.calc_version(later) > VersionCalculator.calc_version(base)


@pytest.mark.asyncio
async def test_redis_lock_manager_acquire_release() -> None:
    class FakeRedisClient:
        def __init__(self) -> None:
            self.set = AsyncMock(side_effect=[True, False])
            self.eval = AsyncMock()

    fake_client = FakeRedisClient()
    lock_manager = RedisLockManager(fake_client)

    assert await lock_manager.acquire("key", "value", 120)
    assert not await lock_manager.acquire("key", "value2", 120)

    await lock_manager.release("key", "value")

    fake_client.eval.assert_awaited_once_with(
        RedisLockManager._RELEASE_SCRIPT, 1, "key", "value"
    )
