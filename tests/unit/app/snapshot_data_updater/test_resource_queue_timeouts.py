"""Таймауты ResourceQueue из конфига."""

from __future__ import annotations

import pytest

from app.snapshot_data_updater.config import SnapshotUpdaterConfig
from app.snapshot_data_updater.resource_queue import (
    ResourceKind,
    build_resource_queue_manager,
)


@pytest.mark.unit
def test_build_resource_queue_manager_pg_timeout_override() -> None:
    cfg = SnapshotUpdaterConfig(
        resource_task_timeout_sec=30.0,
        postgres_task_timeout_sec=120.0,
    )
    mgr = build_resource_queue_manager(cfg)
    pg_queue = mgr.queue_for(ResourceKind.POSTGRES)
    redis_queue = mgr.queue_for(ResourceKind.REDIS)
    assert pg_queue._task_timeout_sec == 120.0
    assert redis_queue._task_timeout_sec == 30.0
