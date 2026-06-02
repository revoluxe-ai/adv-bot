from __future__ import annotations

import asyncio

import pytest

from app.snapshot_data_updater.refresh_shop_snapshot_task import (
    RefreshShopSnapshotTask,
)
from app.snapshot_data_updater.updater import build_snapshot_updater_stub


@pytest.mark.unit
@pytest.mark.asyncio
async def test_refresh_shop_stub() -> None:
    updater = build_snapshot_updater_stub(shop_ids=["s1"])
    batch = await updater.refresh_shop("s1")
    assert batch.shop_id == "s1"
    assert len(batch.snapshots) >= 1


@pytest.mark.unit
@pytest.mark.asyncio
async def test_run_stops_on_event() -> None:
    updater = build_snapshot_updater_stub(shop_ids=["s1"])
    stop_event = asyncio.Event()
    stop_event.set()
    await updater.run(stop_event=stop_event)


@pytest.mark.unit
@pytest.mark.asyncio
async def test_global_tick_skips_duplicate_shop_task() -> None:
    updater = build_snapshot_updater_stub(shop_ids=["only-shop"])
    updater._shop_tasks["only-shop"] = RefreshShopSnapshotTask(
        "only-shop",
        collector=updater._collector,
        store=updater._store,
    )
    sleep_task = asyncio.create_task(asyncio.sleep(10))
    updater._shop_tasks["only-shop"]._asyncio_task = sleep_task
    await updater._run_global_tick()
    assert updater._shop_tasks["only-shop"].is_running
    sleep_task.cancel()
    await asyncio.gather(sleep_task, return_exceptions=True)


@pytest.mark.unit
@pytest.mark.asyncio
async def test_global_tick_skip_when_lock_busy() -> None:
    updater = build_snapshot_updater_stub(shop_ids=["s1"])
    await updater._tick_lock.acquire()
    try:
        await updater._run_global_tick()
        assert not updater._shop_tasks
    finally:
        updater._tick_lock.release()


@pytest.mark.unit
@pytest.mark.asyncio
async def test_refresh_shop_snapshot_task_run() -> None:
    updater = build_snapshot_updater_stub(shop_ids=["s1"])
    task = RefreshShopSnapshotTask(
        "s1",
        collector=updater._collector,
        store=updater._store,
    )
    batch = await task.run()
    assert batch.shop_id == "s1"
