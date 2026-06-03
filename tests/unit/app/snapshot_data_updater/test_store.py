from __future__ import annotations

from datetime import UTC, datetime
from unittest.mock import AsyncMock, MagicMock

import pytest

from app.snapshot_data_updater.cache.redis_adv_data_snapshot_store import (
    RedisAdvDataSnapshotStore,
)
from app.snapshot_data_updater.dto import (
    AdvDataSnapshotDTO,
    AdvSettingsSnapshotDTO,
    ShopAdvSnapshotBatchDTO,
)
from app.snapshot_data_updater.keys import adv_snapshot_key, shop_batch_key


@pytest.mark.unit
@pytest.mark.asyncio
async def test_redis_store_save_and_load_roundtrip() -> None:
    storage: dict[str, str] = {}

    client = MagicMock()

    async def _set(key: str, value: str, ex: int | None = None) -> None:
        storage[key] = value

    async def _get(key: str) -> str | None:
        return storage.get(key)

    async def _delete(key: str) -> None:
        storage.pop(key, None)

    client.set = AsyncMock(side_effect=_set)
    client.get = AsyncMock(side_effect=_get)
    client.delete = AsyncMock(side_effect=_delete)

    store = RedisAdvDataSnapshotStore(redis_client=client, no_op=False, ttl_sec=60)
    ts = datetime(2026, 6, 2, 12, 0, 0, tzinfo=UTC)
    settings = AdvSettingsSnapshotDTO(adv_id=42, shop_id="shop-a")
    snap = AdvDataSnapshotDTO(
        adv_id=42,
        shop_id="shop-a",
        collected_at=ts,
        settings=settings,
    )
    batch = ShopAdvSnapshotBatchDTO(
        shop_id="shop-a",
        collected_at=ts,
        snapshots=[snap],
    )
    await store.save(batch)

    assert shop_batch_key("shop-a") in storage
    assert adv_snapshot_key("shop-a", 42) in storage

    loaded_batch = await store.load_shop_latest("shop-a")
    assert loaded_batch is not None
    assert loaded_batch.shop_id == "shop-a"
    assert len(loaded_batch.snapshots) == 1

    loaded_adv = await store.load_adv_snapshot("shop-a", 42)
    assert loaded_adv is not None
    assert loaded_adv.adv_id == 42


def _make_store_with_storage() -> tuple[RedisAdvDataSnapshotStore, dict[str, str]]:
    storage: dict[str, str] = {}
    client = MagicMock()

    async def _set(key: str, value: str, ex: int | None = None) -> None:
        storage[key] = value

    async def _get(key: str) -> str | None:
        return storage.get(key)

    async def _delete(key: str) -> None:
        storage.pop(key, None)

    client.set = AsyncMock(side_effect=_set)
    client.get = AsyncMock(side_effect=_get)
    client.delete = AsyncMock(side_effect=_delete)
    store = RedisAdvDataSnapshotStore(redis_client=client, no_op=False, ttl_sec=60)
    return store, storage


def _snap(adv_id: int, shop_id: str, ts: datetime) -> AdvDataSnapshotDTO:
    settings = AdvSettingsSnapshotDTO(adv_id=adv_id, shop_id=shop_id)
    return AdvDataSnapshotDTO(
        adv_id=adv_id,
        shop_id=shop_id,
        collected_at=ts,
        settings=settings,
    )


@pytest.mark.unit
@pytest.mark.asyncio
async def test_redis_store_save_removes_stale_per_adv_keys_on_empty_batch() -> None:
    store, storage = _make_store_with_storage()
    ts = datetime(2026, 6, 2, 12, 0, 0, tzinfo=UTC)
    shop_id = "shop-a"
    await store.save(
        ShopAdvSnapshotBatchDTO(
            shop_id=shop_id,
            collected_at=ts,
            snapshots=[_snap(42, shop_id, ts)],
        )
    )
    assert adv_snapshot_key(shop_id, 42) in storage

    await store.save(
        ShopAdvSnapshotBatchDTO(shop_id=shop_id, collected_at=ts, snapshots=[])
    )

    assert adv_snapshot_key(shop_id, 42) not in storage
    assert await store.load_adv_snapshot(shop_id, 42) is None
    loaded = await store.load_shop_latest(shop_id)
    assert loaded is not None
    assert loaded.snapshots == []


@pytest.mark.unit
@pytest.mark.asyncio
async def test_redis_store_save_removes_per_adv_keys_dropped_from_batch() -> None:
    store, storage = _make_store_with_storage()
    ts = datetime(2026, 6, 2, 12, 0, 0, tzinfo=UTC)
    shop_id = "shop-b"
    await store.save(
        ShopAdvSnapshotBatchDTO(
            shop_id=shop_id,
            collected_at=ts,
            snapshots=[_snap(1, shop_id, ts), _snap(2, shop_id, ts)],
        )
    )
    assert adv_snapshot_key(shop_id, 2) in storage

    await store.save(
        ShopAdvSnapshotBatchDTO(
            shop_id=shop_id,
            collected_at=ts,
            snapshots=[_snap(1, shop_id, ts)],
        )
    )

    assert adv_snapshot_key(shop_id, 1) in storage
    assert adv_snapshot_key(shop_id, 2) not in storage
    assert await store.load_adv_snapshot(shop_id, 2) is None


@pytest.mark.unit
@pytest.mark.asyncio
async def test_redis_store_invalid_json_returns_none() -> None:
    client = MagicMock()
    client.get = AsyncMock(return_value=b"{not valid json")

    store = RedisAdvDataSnapshotStore(redis_client=client, no_op=False)
    assert await store.load_shop_latest("shop-a") is None
    assert await store.load_adv_snapshot("shop-a", 1) is None


@pytest.mark.unit
@pytest.mark.asyncio
async def test_redis_store_validation_error_returns_none() -> None:
    """Невалидная схема snapshot → None, без исключения наружу."""
    client = MagicMock()
    client.get = AsyncMock(return_value='{"adv_id": "not-int"}')

    store = RedisAdvDataSnapshotStore(redis_client=client, no_op=False)
    assert await store.load_adv_snapshot("shop-a", 1) is None
