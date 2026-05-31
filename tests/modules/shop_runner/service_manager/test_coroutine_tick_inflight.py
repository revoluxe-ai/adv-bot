"""Tests for non-blocking coroutine tick inflight guard."""

from __future__ import annotations

import asyncio
import time
from unittest.mock import patch

import pytest

from app.modules.shop_runner.service_manager.coroutine_tick_inflight import (
    ENDPOINT_NORMQUERY_STATS,
    CoroutineTickInflightGuard,
)

MODULE = "app.modules.shop_runner.service_manager.coroutine_tick_inflight"


@pytest.mark.unit
@pytest.mark.asyncio
async def test_second_call_skips_without_waiting_when_inflight() -> None:
    guard = CoroutineTickInflightGuard()
    entered = asyncio.Event()
    release = asyncio.Event()

    async def slow_body() -> str:
        entered.set()
        await release.wait()
        return "done"

    first = asyncio.create_task(
        guard.run_or_skip(
            shop_id="shop-1",
            coroutine="update_clusters_adv_stats_today",
            endpoint=ENDPOINT_NORMQUERY_STATS,
            body=slow_body,
        )
    )
    await entered.wait()

    started = time.perf_counter()
    second = await guard.run_or_skip(
        shop_id="shop-1",
        coroutine="update_clusters_adv_stats_today",
        endpoint=ENDPOINT_NORMQUERY_STATS,
        body=slow_body,
    )
    elapsed = time.perf_counter() - started

    assert second is None
    assert elapsed < 0.2

    release.set()
    assert await first == "done"


@pytest.mark.unit
@pytest.mark.asyncio
async def test_skip_logs_skipped_due_to_inflight() -> None:
    guard = CoroutineTickInflightGuard()
    hold = asyncio.Event()

    async def hold_body() -> None:
        await hold.wait()

    first = asyncio.create_task(
        guard.run_or_skip(
            shop_id="454ef6d9",
            coroutine="update_clusters_adv_stats_today",
            endpoint=ENDPOINT_NORMQUERY_STATS,
            body=hold_body,
        )
    )
    await asyncio.sleep(0)

    with patch(f"{MODULE}.logger") as mock_logger:
        _ = await guard.run_or_skip(
            shop_id="454ef6d9",
            coroutine="update_clusters_adv_stats_today",
            endpoint=ENDPOINT_NORMQUERY_STATS,
            body=hold_body,
        )
    hold.set()
    await first

    mock_logger.info.assert_called()
    skip_msg = mock_logger.info.call_args[0][0]
    assert "skipped_due_to_inflight=true" in skip_msg


@pytest.mark.unit
@pytest.mark.asyncio
async def test_success_path_has_no_extra_delay_between_sequential_ticks() -> None:
    guard = CoroutineTickInflightGuard()

    async def fast_body() -> int:
        return 1

    t0 = time.perf_counter()
    for _ in range(5):
        result = await guard.run_or_skip(
            shop_id="shop-1",
            coroutine="update_clusters_adv_stats_today",
            endpoint=ENDPOINT_NORMQUERY_STATS,
            body=fast_body,
        )
        assert result == 1
    elapsed = time.perf_counter() - t0
    assert elapsed < 0.5
