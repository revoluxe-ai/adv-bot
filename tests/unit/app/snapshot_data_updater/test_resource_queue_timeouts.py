"""Таймауты ResourceQueue (Redis) из конфига."""

from __future__ import annotations

import pytest

from app.snapshot_data_updater.config import SnapshotUpdaterConfig
from app.snapshot_data_updater.resource_queue import (
    ResourceKind,
    ResourceQueueManager,
    build_resource_queue_manager,
)


@pytest.mark.unit
def test_build_resource_queue_manager_redis_timeout() -> None:
    cfg = SnapshotUpdaterConfig(resource_task_timeout_sec=360.0)
    mgr = build_resource_queue_manager(cfg)
    redis_queue = mgr.queue_for(ResourceKind.REDIS)
    assert redis_queue._task_timeout_sec == 360.0


@pytest.mark.unit
def test_resource_queue_manager_task_timeout_by_kind_overrides_default() -> None:
    mgr = ResourceQueueManager(
        concurrency={ResourceKind.REDIS: 2},
        task_timeout_sec=30.0,
        task_timeout_by_kind={ResourceKind.REDIS: 120.0},
    )
    assert mgr.queue_for(ResourceKind.REDIS)._task_timeout_sec == 120.0


@pytest.mark.unit
def test_build_resource_queue_manager_ignores_postgres_timeout_field() -> None:
    """postgres_task_timeout_sec не влияет на Redis-очередь (PG не через ResourceQueue)."""
    cfg = SnapshotUpdaterConfig(
        resource_task_timeout_sec=30.0,
        postgres_task_timeout_sec=180.0,
    )
    mgr = build_resource_queue_manager(cfg)
    assert mgr.queue_for(ResourceKind.REDIS)._task_timeout_sec == 30.0
