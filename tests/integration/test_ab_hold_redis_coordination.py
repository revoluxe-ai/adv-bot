"""Integration (Redis): CardAbHold Signal / LastAbort / SetupBlock / EnterReset.

Закрывает разрыв: unit-тесты проверяли только Pydantic DTO / ключи, а
production caches пишут через ``RedisClient`` + TTL. Здесь — fakeredis
(тот же ``RedisClient``, что в проде); DI обходится через patch ``client``.

Spec ``card-ab-hold-mode`` / decision write-path ownership §4–5 / §14b / §19.
Класс: integration (Redis path). Live cluster Redis вне scope.
"""

from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import PropertyMock, patch

import pytest
from fakeredis.aioredis import FakeRedis

from app.core.redis_manager_v2.redis_client import RedisClient
from app.modules.shop_runner.service_manager.services.auto_updater_v3.card_ab_hold.mode import (
    CardAbHoldSetupBlockKind,
)
from app.modules.shop_runner.service_manager.services.auto_updater_v3.card_ab_hold.redis_coordination import (
    SETUP_LOCK_TTL_SEC,
    CardAbHoldCommonBidEnterResetRedisCache,
    CardAbHoldLastAbortRedisCache,
    CardAbHoldLastAbortSnapshot,
    CardAbHoldSetupBlockRedisCache,
    CardAbHoldSetupBlockSnapshot,
    CardAbHoldSignalKind,
    CardAbHoldSignalRedisCache,
    CardAbHoldSignalSnapshot,
    setup_lock_redis_key,
)
from app.modules.shop_runner.service_manager.services.increment_fact_data_manager.redis_lock_manager import (
    RedisLockManager,
)


def _adv(*, adv_id: int = 4242) -> SimpleNamespace:
    """Минимальный AdvSetting-shape: caches читают только ``adv_id``."""
    return SimpleNamespace(adv_id=adv_id)


@pytest.mark.integration
@pytest.mark.asyncio
async def test_signal_roundtrip_set_get_clear_over_fakeredis(
    fake_redis: FakeRedis,
) -> None:
    """ENTER signal переживает JSON+TTL roundtrip; clear удаляет ключ."""
    wrapper = RedisClient(redis_client=fake_redis)
    adv = _adv(adv_id=9001)
    cache = CardAbHoldSignalRedisCache(adv)
    snap = CardAbHoldSignalSnapshot(
        signal=CardAbHoldSignalKind.ENTER,
        requested_by="bot",
    )

    with patch.object(
        type(cache), "client", new_callable=PropertyMock
    ) as client_prop:
        client_prop.return_value = wrapper
        await cache.set_signal(snap)
        restored = await cache.get_signal()
        assert restored is not None
        assert restored.signal == CardAbHoldSignalKind.ENTER
        assert restored.requested_by == "bot"
        assert await fake_redis.exists("CardAbHoldSignal:9001") == 1
        ttl = await fake_redis.ttl("CardAbHoldSignal:9001")
        assert ttl > 0

        await cache.clear()
        assert await cache.get_signal() is None
        assert await fake_redis.exists("CardAbHoldSignal:9001") == 0


@pytest.mark.integration
@pytest.mark.asyncio
async def test_last_abort_roundtrip_over_fakeredis(
    fake_redis: FakeRedis,
) -> None:
    """LastAbort ack читается UI poll после safe abort shop-runner."""
    wrapper = RedisClient(redis_client=fake_redis)
    cache = CardAbHoldLastAbortRedisCache(_adv(adv_id=9002))
    snap = CardAbHoldLastAbortSnapshot(
        reason="enter_requested",
        safe=True,
        can_continue=True,
    )

    with patch.object(
        type(cache), "client", new_callable=PropertyMock
    ) as client_prop:
        client_prop.return_value = wrapper
        await cache.set_abort(snap)
        restored = await cache.get_abort()
        assert restored is not None
        assert restored.reason == "enter_requested"
        assert restored.safe is True
        assert restored.can_continue is True
        assert await fake_redis.exists("CardAbHoldLastAbort:9002") == 1


@pytest.mark.integration
@pytest.mark.asyncio
async def test_setup_block_roundtrip_and_clear_over_fakeredis(
    fake_redis: FakeRedis,
) -> None:
    """§14b: shop-runner пишет block; bot читает; EXIT/success clear."""
    wrapper = RedisClient(redis_client=fake_redis)
    cache = CardAbHoldSetupBlockRedisCache(_adv(adv_id=9003))
    snap = CardAbHoldSetupBlockSnapshot(
        kind=CardAbHoldSetupBlockKind.EMPTY_ALLOWED_SET,
    )

    with patch.object(
        type(cache), "client", new_callable=PropertyMock
    ) as client_prop:
        client_prop.return_value = wrapper
        await cache.set_block(snap)
        restored = await cache.get_block()
        assert restored is not None
        assert restored.kind == CardAbHoldSetupBlockKind.EMPTY_ALLOWED_SET

        await cache.clear()
        assert await cache.get_block() is None
        assert await fake_redis.exists("CardAbHoldSetupBlock:9003") == 0


@pytest.mark.integration
@pytest.mark.asyncio
async def test_common_bid_enter_reset_done_marker_roundtrip_over_fakeredis(
    fake_redis: FakeRedis,
) -> None:
    """§19: ENTER mark_done → is_done; EXIT clear снимает one-shot маркер.

    Unit mocks кэш целиком; здесь production get/set/delete через RedisClient.
    """
    wrapper = RedisClient(redis_client=fake_redis)
    cache = CardAbHoldCommonBidEnterResetRedisCache(_adv(adv_id=9005))
    key = "CardAbHoldCommonBidEnterReset:9005"

    with patch.object(
        type(cache), "client", new_callable=PropertyMock
    ) as client_prop:
        client_prop.return_value = wrapper
        assert await cache.is_done() is False

        await cache.mark_done()
        assert await cache.is_done() is True
        assert await fake_redis.get(key) == "done"
        ttl = await fake_redis.ttl(key)
        assert ttl > 0

        await cache.clear()
        assert await cache.is_done() is False
        assert await fake_redis.exists(key) == 0


@pytest.mark.integration
@pytest.mark.asyncio
async def test_common_bid_enter_reset_rejects_non_done_payload(
    fake_redis: FakeRedis,
) -> None:
    """Чужой payload под тем же ключом не считается done-маркером."""
    wrapper = RedisClient(redis_client=fake_redis)
    cache = CardAbHoldCommonBidEnterResetRedisCache(_adv(adv_id=9006))
    await fake_redis.set("CardAbHoldCommonBidEnterReset:9006", "other")

    with patch.object(
        type(cache), "client", new_callable=PropertyMock
    ) as client_prop:
        client_prop.return_value = wrapper
        assert await cache.is_done() is False


@pytest.mark.integration
@pytest.mark.asyncio
async def test_corrupt_redis_payloads_return_none(
    fake_redis: FakeRedis,
) -> None:
    """Битый JSON не роняет poll: get_* → None (fail-soft)."""
    wrapper = RedisClient(redis_client=fake_redis)
    signal = CardAbHoldSignalRedisCache(_adv(adv_id=9100))
    abort = CardAbHoldLastAbortRedisCache(_adv(adv_id=9100))
    block = CardAbHoldSetupBlockRedisCache(_adv(adv_id=9100))

    await fake_redis.set("CardAbHoldSignal:9100", "not-json")
    await fake_redis.set("CardAbHoldLastAbort:9100", "{")
    await fake_redis.set(
        "CardAbHoldSetupBlock:9100",
        '{"kind":"unknown_kind","detected_at":"2026-07-26T00:00:00+00:00"}',
    )

    with (
        patch.object(type(signal), "client", new_callable=PropertyMock) as sp,
        patch.object(type(abort), "client", new_callable=PropertyMock) as ap,
        patch.object(type(block), "client", new_callable=PropertyMock) as bp,
    ):
        sp.return_value = wrapper
        ap.return_value = wrapper
        bp.return_value = wrapper
        assert await signal.get_signal() is None
        assert await abort.get_abort() is None
        assert await block.get_block() is None


@pytest.mark.integration
def test_setup_lock_key_contract() -> None:
    """Setup single-flight key остаётся ``CardAbHoldSetupLock:{adv_id}``."""
    assert setup_lock_redis_key(77) == "CardAbHoldSetupLock:77"


@pytest.mark.integration
@pytest.mark.asyncio
async def test_setup_lock_nx_single_flight_over_fakeredis(
    fake_redis: FakeRedis,
) -> None:
    """``process_ab_setup`` single-flight: второй acquire на том же ключе — fail.

    Release через Lua ``EVAL`` не проверяем: fakeredis в этой среде не
    эмулирует ``eval``; production release остаётся unit/live Redis scope.
    """
    wrapper = RedisClient(redis_client=fake_redis)
    lock = RedisLockManager(wrapper)
    key = setup_lock_redis_key(9004)

    first = await lock.acquire(key, "owner-a", SETUP_LOCK_TTL_SEC)
    second = await lock.acquire(key, "owner-b", SETUP_LOCK_TTL_SEC)
    # redis-py SET NX: True при успехе, None при занятом ключе (не False).
    assert first is True
    assert not second
    assert await fake_redis.get(key) == "owner-a"
    ttl = await fake_redis.ttl(key)
    assert ttl > 0
