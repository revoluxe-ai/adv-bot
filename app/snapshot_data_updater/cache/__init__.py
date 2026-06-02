"""Кэш/хранилище готовых AdvDataSnapshot (PR1: no-op Redis store)."""

from app.snapshot_data_updater.cache.redis_adv_data_snapshot_store import (
    RedisAdvDataSnapshotStore,
)

__all__ = ["RedisAdvDataSnapshotStore"]
