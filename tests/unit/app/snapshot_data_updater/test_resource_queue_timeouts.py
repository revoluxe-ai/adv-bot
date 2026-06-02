"""Таймауты ResourceQueue (Redis) из конфига."""

from __future__ import annotations

import pytest

from app.snapshot_data_updater.config import SnapshotUpdaterConfig
from app.snapshot_data_updater.resource_queue import (
    ResourceKind,
    build_resource_queue_manager,
)


@pytest.mark.unit
def test_build_resource_queue_manager_redis_timeout() -> None:
    cfg = SnapshotUpdaterConfig(resource_task_timeout_sec=360.0)
    mgr = build_resource_queue_manager(cfg)
    redis_queue = mgr.queue_for(ResourceKind.REDIS)
    assert redis_queue._task_timeout_sec == 360.0
