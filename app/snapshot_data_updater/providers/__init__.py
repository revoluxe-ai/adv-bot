"""Stub- и Live-провайдеры snapshot_data_updater."""

from app.snapshot_data_updater.providers.clickhouse_provider import (
    ClickHouseSnapshotProviderLive,
    StubClickHouseSnapshotProvider,
)
from app.snapshot_data_updater.providers.postgres_provider import (
    PostgresSnapshotProviderLive,
    StubPostgresSnapshotProvider,
)
from app.snapshot_data_updater.providers.redis_provider import (
    RedisSnapshotProviderLive,
    StubRedisSnapshotProvider,
)

__all__ = [
    "ClickHouseSnapshotProviderLive",
    "PostgresSnapshotProviderLive",
    "RedisSnapshotProviderLive",
    "StubClickHouseSnapshotProvider",
    "StubPostgresSnapshotProvider",
    "StubRedisSnapshotProvider",
]
