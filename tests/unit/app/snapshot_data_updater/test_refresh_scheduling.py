from __future__ import annotations

import asyncio

import pytest

from app.snapshot_data_updater.updater import build_snapshot_updater_stub


@pytest.mark.unit
@pytest.mark.asyncio
async def test_tick_wait_policy_serializes_ticks() -> None:
    """При tick_policy=wait второй tick ждёт lock, не выполняется параллельно."""
    updater = build_snapshot_updater_stub(shop_ids=["s1"])
    updater._tick_skip_if_busy = False
    order: list[str] = []

    async def slow_collect(shop_id: str) -> object:
        order.append("collect_start")
        await asyncio.sleep(0.05)
        order.append("collect_end")
        from app.snapshot_data_updater.dto import ShopAdvSnapshotBatchDTO
        from datetime import UTC, datetime

        return ShopAdvSnapshotBatchDTO(
            shop_id=shop_id,
            collected_at=datetime.now(tz=UTC),
            snapshots=[],
        )

    updater._collector.collect_shop = slow_collect  # type: ignore[method-assign]

    async def run_tick(label: str) -> None:
        order.append(f"{label}_before")
        await updater._run_global_tick()
        order.append(f"{label}_after")

    await asyncio.wait_for(
        asyncio.gather(run_tick("t1"), run_tick("t2")),
        timeout=5.0,
    )
    assert order.index("t1_before") < order.index("t1_after")
    assert order.index("t2_before") < order.index("t2_after")
    assert order.index("t1_after") < order.index("t2_before")
