"""Tests for single_run decorator and make_key (hashable kwargs)."""

import asyncio
from unittest.mock import patch

import pytest

from app.modules.shop_runner.service_manager.wb_shop_data_manager.single_run_decorator import (
    make_key,
    single_run,
)


def test_make_key_with_dict_kwargs_does_not_raise() -> None:
    """Passing dict kwargs (e.g. search_adv_bids_override) must not raise unhashable type."""
    # search_adv_bids_override: dict[int, dict[int, int]]
    kwargs = {"search_adv_bids_override": {1: {100: 50, 200: 60}, 2: {100: 70}}}
    key = make_key("get_wb_advs_dto", ([],), kwargs)
    assert "get_wb_advs_dto" in key
    assert isinstance(key, str)


def test_make_key_same_dict_kwargs_same_key() -> None:
    """Same dict content produces same key for deduplication."""
    kwargs = {"search_adv_bids_override": {1: {100: 50}, 2: {100: 70}}}
    key1 = make_key("get_wb_advs_dto", ([],), kwargs)
    key2 = make_key("get_wb_advs_dto", ([],), {"search_adv_bids_override": {2: {100: 70}, 1: {100: 50}}})
    assert key1 == key2


def test_make_key_different_dict_kwargs_different_key() -> None:
    """Different dict content produces different key."""
    key1 = make_key("get_wb_advs_dto", ([],), {"search_adv_bids_override": {1: {100: 50}}})
    key2 = make_key("get_wb_advs_dto", ([],), {"search_adv_bids_override": {1: {100: 60}}})
    assert key1 != key2


def test_make_key_none_override() -> None:
    """None as kwargs value is hashable."""
    key = make_key("get_wb_advs_dto", ([],), {"search_adv_bids_override": None})
    assert "get_wb_advs_dto" in key


class _SingleRunHost:
    """Minimal self for @single_run methods."""

    pass


@pytest.mark.unit
@pytest.mark.asyncio
async def test_waiter_timeout_does_not_break_exclusivity() -> None:
    """Waiter timeout must not remove key while first caller is still running."""
    host = _SingleRunHost()
    execution_count = 0
    first_entered = asyncio.Event()
    release_first = asyncio.Event()

    @single_run()
    async def slow_method(self: _SingleRunHost) -> str:
        nonlocal execution_count
        execution_count += 1
        first_entered.set()
        await release_first.wait()
        return "done"

    wrapped = slow_method

    short_timeout = 0.05

    async def first_caller() -> str:
        return await wrapped(host)

    first_task = asyncio.create_task(first_caller())
    await asyncio.wait_for(first_entered.wait(), timeout=1.0)

    with patch(
        "app.modules.shop_runner.service_manager.wb_shop_data_manager.single_run_decorator.SINGLE_RUN_WAIT_TIMEOUT_SECONDS",
        short_timeout,
    ):
        with pytest.raises(asyncio.TimeoutError):
            await wrapped(host)

    assert key_present(host), "key must remain while first caller runs"
    assert execution_count == 1, "waiter timeout must not start second execution"

    # Новый caller без укороченного timeout — должен ждать first, не дублировать.
    third_task = asyncio.create_task(wrapped(host))
    await asyncio.sleep(0.02)
    assert execution_count == 1, "third caller must wait, not duplicate"

    release_first.set()
    assert await asyncio.wait_for(first_task, timeout=1.0) == "done"
    assert await asyncio.wait_for(third_task, timeout=1.0) == "done"

    assert execution_count == 1
    assert not key_present(host), "key cleaned up after first caller finishes"


def key_present(host: _SingleRunHost) -> bool:
    events = getattr(host, "_single_run_events", {})
    return any(k.startswith("slow_method:") for k in events)


@pytest.mark.unit
@pytest.mark.asyncio
async def test_waiter_receives_exception_from_first_caller() -> None:
    """Waiter must propagate exception stored by first caller."""
    host = _SingleRunHost()
    started = asyncio.Event()

    @single_run()
    async def failing_method(self: _SingleRunHost) -> None:
        started.set()
        raise ValueError("boom")

    wrapped = failing_method

    async def first_caller() -> None:
        with pytest.raises(ValueError, match="boom"):
            await wrapped(host)

    first_task = asyncio.create_task(first_caller())
    await asyncio.wait_for(started.wait(), timeout=1.0)

    with pytest.raises(ValueError, match="boom"):
        await wrapped(host)

    await asyncio.wait_for(first_task, timeout=1.0)
    assert not key_present(host)


@pytest.mark.unit
@pytest.mark.asyncio
async def test_waiter_receives_cancellation_from_first_caller() -> None:
    """Waiter must receive CancelledError when first caller is cancelled."""
    host = _SingleRunHost()
    started = asyncio.Event()
    release = asyncio.Event()

    @single_run()
    async def cancellable_method(self: _SingleRunHost) -> str:
        started.set()
        await release.wait()
        return "done"

    wrapped = cancellable_method

    first_task = asyncio.create_task(wrapped(host))
    await asyncio.wait_for(started.wait(), timeout=1.0)

    waiter_task = asyncio.create_task(wrapped(host))
    await asyncio.sleep(0)

    first_task.cancel()

    with pytest.raises(asyncio.CancelledError):
        await first_task
    with pytest.raises(asyncio.CancelledError):
        await asyncio.wait_for(waiter_task, timeout=1.0)

    assert not key_present(host)
