from datetime import datetime
from unittest.mock import AsyncMock

import pytest

from app.core.redis_manager_v2.redis_client import RedisClient
from app.modules.billing.redis_manager import RedisManager


pytestmark = pytest.mark.asyncio


async def test_set_and_get_last_charge_at_roundtrip():
    raw = AsyncMock()
    raw.get = AsyncMock(return_value=None)
    raw.set = AsyncMock(return_value=True)
    client = RedisClient(redis_client=raw)  # type: ignore[arg-type]
    mgr = RedisManager(redis_client=client)

    now = datetime(2025, 12, 16, 12, 0, 0)
    await mgr.set_last_charge_at("shop_1", now, ttl=None)

    # emulate stored value
    raw.get = AsyncMock(return_value=now.isoformat())
    got = await mgr.get_last_charge_at("shop_1")
    assert got == now

