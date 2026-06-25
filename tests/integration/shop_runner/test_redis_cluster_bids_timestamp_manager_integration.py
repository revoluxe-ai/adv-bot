"""Интеграционные тесты RedisClusterBidsTimestampManager против локального Redis.

Проверяют batch-запись ``set_many`` через ``write_pipeline`` на реальном инстансе
(``REDIS_MASTER_HOST`` / ``REDIS_PORT`` из окружения тестов, по умолчанию localhost:6379).
"""

from __future__ import annotations

import datetime
from dataclasses import dataclass

import pytest

from app.configs import AppConfig
from app.core.di.databases.redis import create_redis_client
from app.core.redis_manager_v2.redis_client import RedisClient
from app.modules.cluster_bids_redis import RedisClusterBidsTimestampManager

# Изолированный диапазон search_adv_id, чтобы не пересекаться с продовыми ключами.
_TEST_SEARCH_ADV_ID_BASE = 9_990_000_000


@dataclass(frozen=True)
class _AdvStub:
    """Минимальная реализация AdvProtocol для тестов."""

    search_adv_id: int


@pytest.fixture
async def local_redis_client() -> RedisClient:
    """RedisClient, подключённый к локальному Redis; пропускает тест при недоступности."""
    config = AppConfig.create()
    raw = create_redis_client(config)
    try:
        await raw.ping()  # pyright: ignore[reportGeneralTypeIssues]
    except Exception as exc:
        await raw.aclose()  # type: ignore[attr-defined]
        pytest.skip(f"Local Redis unavailable: {exc}")
    wrapper = RedisClient(redis_client=raw)
    try:
        yield wrapper
    finally:
        await raw.aclose()  # type: ignore[attr-defined]


@pytest.fixture
async def timestamp_manager(
    local_redis_client: RedisClient,
) -> RedisClusterBidsTimestampManager:
    """Менеджер timestamp с очисткой тестовых ключей после каждого кейса."""
    manager = RedisClusterBidsTimestampManager(redis_client=local_redis_client)
    adv_ids = [
        _TEST_SEARCH_ADV_ID_BASE + 1,
        _TEST_SEARCH_ADV_ID_BASE + 2,
        _TEST_SEARCH_ADV_ID_BASE + 3,
    ]
    yield manager
    for search_adv_id in adv_ids:
        await local_redis_client.delete(manager._get_key(search_adv_id))


@pytest.mark.integration
@pytest.mark.asyncio
async def test_set_many_persists_timestamps_for_all_advs(
    timestamp_manager: RedisClusterBidsTimestampManager,
    local_redis_client: RedisClient,
) -> None:
    """Batch SET через pipeline: все search_adv_id читаются обратно через get()."""
    advs = [
        _AdvStub(_TEST_SEARCH_ADV_ID_BASE + 1),
        _AdvStub(_TEST_SEARCH_ADV_ID_BASE + 2),
        _AdvStub(_TEST_SEARCH_ADV_ID_BASE + 3),
    ]

    await timestamp_manager.set_many(advs)

    for adv in advs:
        stored = await timestamp_manager.get(adv)
        assert stored is not None
        assert isinstance(stored, datetime.datetime)
        raw = await local_redis_client.get(timestamp_manager._get_key(adv.search_adv_id))
        assert raw is not None
        assert datetime.datetime.fromisoformat(raw) == stored


@pytest.mark.integration
@pytest.mark.asyncio
async def test_set_many_uses_single_iso_timestamp_for_whole_batch(
    timestamp_manager: RedisClusterBidsTimestampManager,
    local_redis_client: RedisClient,
) -> None:
    """Один вызов set_many — одно значение timestamp на все ключи batch."""
    advs = [
        _AdvStub(_TEST_SEARCH_ADV_ID_BASE + 1),
        _AdvStub(_TEST_SEARCH_ADV_ID_BASE + 2),
    ]

    await timestamp_manager.set_many(advs)

    raw_values = [
        await local_redis_client.get(timestamp_manager._get_key(adv.search_adv_id)) for adv in advs
    ]
    assert len(set(raw_values)) == 1


@pytest.mark.integration
@pytest.mark.asyncio
async def test_set_many_deduplicates_repeated_adv_id(
    timestamp_manager: RedisClusterBidsTimestampManager,
    local_redis_client: RedisClient,
) -> None:
    """Повтор search_adv_id в списке не создаёт лишних ключей и не ломает чтение."""
    search_adv_id = _TEST_SEARCH_ADV_ID_BASE + 1
    adv = _AdvStub(search_adv_id)

    await timestamp_manager.set_many([adv, adv, adv])

    assert await local_redis_client.exists(timestamp_manager._get_key(search_adv_id)) == 1
    assert await timestamp_manager.get(adv) is not None


@pytest.mark.integration
@pytest.mark.asyncio
async def test_set_many_empty_list_is_noop(
    timestamp_manager: RedisClusterBidsTimestampManager,
) -> None:
    """Пустой batch не падает и не создаёт ключи."""
    await timestamp_manager.set_many([])

    assert await timestamp_manager.get(_AdvStub(_TEST_SEARCH_ADV_ID_BASE + 1)) is None


@pytest.mark.integration
@pytest.mark.asyncio
async def test_set_single_adv_via_pipeline(
    timestamp_manager: RedisClusterBidsTimestampManager,
) -> None:
    """set() для одной РК делегирует в set_many и сохраняет timestamp."""
    adv = _AdvStub(_TEST_SEARCH_ADV_ID_BASE + 2)

    await timestamp_manager.set(adv)

    stored = await timestamp_manager.get(adv)
    assert stored is not None
    assert isinstance(stored, datetime.datetime)
