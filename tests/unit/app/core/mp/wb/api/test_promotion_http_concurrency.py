"""Unit-тесты глобального semaphore для PROMOTION HTTP."""

from __future__ import annotations

import asyncio
from unittest.mock import AsyncMock, MagicMock, patch

import httpx
import pytest

from app.core.mp.wb.api.adapter.sections_enum import SectionsEnum
from app.core.mp.wb.api.api_client import _AuthAsyncProxy
from app.core.mp.wb.api.promotion_http_concurrency import (
    acquire_promotion_http,
    get_promotion_global_semaphore,
    reset_promotion_http_concurrency_state,
)


@pytest.fixture(autouse=True)
def _reset_concurrency_state() -> None:
    reset_promotion_http_concurrency_state()
    yield
    reset_promotion_http_concurrency_state()


@pytest.mark.unit
@pytest.mark.asyncio
async def test_global_semaphore_limits_concurrent_promotion_requests(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("PROMOTION_HTTP_CONCURRENCY_LIMIT", "2")
    reset_promotion_http_concurrency_state()

    in_flight = 0
    max_in_flight = 0
    lock = asyncio.Lock()
    release_gate = asyncio.Event()

    async def slow_request(*_args: object, **_kwargs: object) -> MagicMock:
        nonlocal in_flight, max_in_flight
        async with lock:
            in_flight += 1
            max_in_flight = max(max_in_flight, in_flight)
        await release_gate.wait()
        async with lock:
            in_flight -= 1
        return MagicMock()

    client = AsyncMock(spec=httpx.AsyncClient)
    client.request = slow_request
    proxy = _AuthAsyncProxy(
        client, "token", section=SectionsEnum.PROMOTION, shop_id="shop-a"
    )

    tasks = [asyncio.create_task(proxy.request("GET", "/adv/v3/fullstats")) for _ in range(5)]
    await asyncio.sleep(0.05)
    assert max_in_flight <= 2
    release_gate.set()
    _ = await asyncio.gather(*tasks)
    assert max_in_flight == 2


@pytest.mark.unit
@pytest.mark.asyncio
async def test_analytic_section_not_limited_by_promotion_semaphore(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("PROMOTION_HTTP_CONCURRENCY_LIMIT", "1")
    reset_promotion_http_concurrency_state()

    sem = get_promotion_global_semaphore()
    await sem.acquire()

    client = AsyncMock(spec=httpx.AsyncClient)
    client.request = AsyncMock(return_value=MagicMock())
    proxy = _AuthAsyncProxy(
        client,
        "token",
        section=SectionsEnum.ANALYTIC_AND_DATA,
        shop_id="shop-a",
    )
    _ = await proxy.request("GET", "/api/v2/nm-report/detail")
    client.request.assert_awaited_once()
    sem.release()


@pytest.mark.unit
@pytest.mark.asyncio
async def test_acquire_promotion_http_waits_when_limit_reached(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("PROMOTION_HTTP_CONCURRENCY_LIMIT", "1")
    reset_promotion_http_concurrency_state()

    entered = asyncio.Event()
    release_holder = asyncio.Event()
    waiter_started = asyncio.Event()

    async def holder() -> None:
        async with acquire_promotion_http(
            shop_id="shop-1",
            http_method="GET",
            endpoint="/adv/v0/normquery/bids",
        ):
            entered.set()
            await release_holder.wait()

    holder_task = asyncio.create_task(holder())
    await entered.wait()

    async def waiter() -> None:
        waiter_started.set()
        async with acquire_promotion_http(shop_id="shop-1"):
            return None

    waiter_task = asyncio.create_task(waiter())
    await waiter_started.wait()
    await asyncio.sleep(0.05)
    assert not waiter_task.done()
    release_holder.set()
    await holder_task
    await asyncio.wait_for(waiter_task, timeout=2.0)


@pytest.mark.unit
@pytest.mark.asyncio
async def test_acquire_returns_timing_snapshot(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("PROMOTION_HTTP_CONCURRENCY_LIMIT", "1")
    reset_promotion_http_concurrency_state()

    async def holder() -> None:
        sem = get_promotion_global_semaphore()
        await sem.acquire()
        await asyncio.sleep(1.2)
        sem.release()

    holder_task = asyncio.create_task(holder())
    await asyncio.sleep(0.02)
    async with acquire_promotion_http(
        shop_id="shop-warn",
        http_method="GET",
        endpoint="/adv/v3/fullstats",
    ) as timing:
        assert timing.wait_semaphore_sec >= 1.0
        assert timing.in_flight == 1
        assert timing.limit == 1
    await holder_task


@pytest.mark.unit
@pytest.mark.asyncio
async def test_slow_promotion_request_logs_structured_timing(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("PROMOTION_HTTP_CONCURRENCY_LIMIT", "1")
    reset_promotion_http_concurrency_state()

    async def holder() -> None:
        sem = get_promotion_global_semaphore()
        await sem.acquire()
        await asyncio.sleep(1.2)
        sem.release()

    async def request(*_args: object, **_kwargs: object) -> MagicMock:
        return MagicMock()

    client = AsyncMock(spec=httpx.AsyncClient)
    client.request = request
    proxy = _AuthAsyncProxy(
        client, "token", section=SectionsEnum.PROMOTION, shop_id="shop-warn"
    )

    with patch("app.core.mp.wb.api.api_client.logger.warning") as warn_mock:
        holder_task = asyncio.create_task(holder())
        await asyncio.sleep(0.02)
        _ = await proxy.request("GET", "/adv/v3/fullstats")
        await holder_task

        warn_mock.assert_called_once()
        msg = str(warn_mock.call_args)
        assert "wb_promotion_http_timing" in msg
        assert "section=%s" in msg
        assert "wait_semaphore_sec=%.3f" in msg
        assert "inside_request_duration_sec=%.3f" in msg
        assert "total_duration_sec=%.3f" in msg
        assert "in_flight=%s" in msg
        assert "limit=%s" in msg
        assert "shop-warn" in msg


@pytest.mark.unit
@pytest.mark.asyncio
async def test_pool_timeout_logs_pool_timeout_flag(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("PROMOTION_HTTP_CONCURRENCY_LIMIT", "1")
    reset_promotion_http_concurrency_state()

    client = AsyncMock(spec=httpx.AsyncClient)
    client.request = AsyncMock(side_effect=httpx.PoolTimeout("pool exhausted"))
    proxy = _AuthAsyncProxy(
        client, "token", section=SectionsEnum.PROMOTION, shop_id="shop-pool"
    )

    with patch("app.core.mp.wb.api.api_client.logger.warning") as warn_mock:
        with pytest.raises(httpx.PoolTimeout):
            await proxy.request("GET", "/adv/v0/normquery/stats")

        warn_mock.assert_called_once()
        args = warn_mock.call_args.args
        assert "pool_timeout=%s" in args[0]
        assert True in args
        assert "PoolTimeout" in args


async def _run_acquire_and_release(
    *,
    shop_id: str,
    http_method: str,
    endpoint: str,
) -> None:
    async with acquire_promotion_http(
        shop_id=shop_id,
        http_method=http_method,
        endpoint=endpoint,
    ):
        return None
