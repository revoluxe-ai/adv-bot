from __future__ import annotations

import pytest

from app.snapshot_data_updater.config import SnapshotUpdaterConfig
from app.snapshot_data_updater.factory import (
    build_snapshot_updater,
    build_snapshot_updater_live,
)
from app.snapshot_data_updater.providers import (
    PostgresSnapshotProviderLive,
    RedisSnapshotProviderLive,
    StubPostgresSnapshotProvider,
)
from app.snapshot_data_updater.providers.clickhouse_provider import (
    ClickHouseSnapshotProviderLive,
)
from app.snapshot_data_updater.updater import SnapshotUpdater


@pytest.mark.unit
def test_build_snapshot_updater_stub_by_default() -> None:
    cfg = SnapshotUpdaterConfig(use_live_updater=False)
    updater = build_snapshot_updater(config=cfg)
    assert isinstance(updater, SnapshotUpdater)
    assert isinstance(updater._collector._postgres, StubPostgresSnapshotProvider)


@pytest.mark.unit
def test_build_snapshot_updater_live_stack() -> None:
    cfg = SnapshotUpdaterConfig(use_live_updater=True)
    updater = build_snapshot_updater_live(shop_ids=["s1"], config=cfg)
    assert isinstance(updater._collector._postgres, PostgresSnapshotProviderLive)
    assert isinstance(updater._collector._clickhouse, ClickHouseSnapshotProviderLive)
    assert isinstance(updater._collector._redis, RedisSnapshotProviderLive)
    assert updater._collector._keywords_warmup is not None
