from __future__ import annotations

import asyncio

import pytest

from app.snapshot_data_updater.resource_queue import (
    ResourceKind,
    ResourceQueue,
    ResourceTask,
)


@pytest.mark.unit
@pytest.mark.asyncio
async def test_resource_queue_submit_returns_result() -> None:
    queue = ResourceQueue(ResourceKind.REDIS, concurrency=2, task_timeout_sec=5.0)

    async def _work() -> int:
        return 7

    future = queue.submit(
        ResourceTask(
            kind=ResourceKind.REDIS,
            name="test",
            coro_factory=_work,
        )
    )
    assert await future == 7
    await queue.stop()


@pytest.mark.unit
@pytest.mark.asyncio
async def test_resource_queue_timeout() -> None:
    queue = ResourceQueue(ResourceKind.POSTGRES, concurrency=1, task_timeout_sec=0.05)

    async def _slow() -> None:
        await asyncio.sleep(1.0)

    future = queue.submit(
        ResourceTask(
            kind=ResourceKind.POSTGRES,
            name="slow",
            coro_factory=_slow,
        )
    )
    with pytest.raises(TimeoutError):
        await future
    await queue.stop()


@pytest.mark.unit
@pytest.mark.asyncio
async def test_resource_queue_stop_rejects_submit() -> None:
    queue = ResourceQueue(ResourceKind.CLICKHOUSE, concurrency=1)
    await queue.stop()
    with pytest.raises(RuntimeError, match="stopped"):
        queue.submit(
            ResourceTask(
                kind=ResourceKind.CLICKHOUSE,
                name="x",
                coro_factory=lambda: asyncio.sleep(0),
            )
        )
