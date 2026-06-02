"""Unit-тесты распространения ContextVar через shared TasksManager.

Bug-fix: add_task() теперь захватывает copy_context() и handler выполняется
в контексте вызывающей стороны, а не в пустом контексте shared worker.
"""

from __future__ import annotations

import asyncio
from contextvars import ContextVar

import pytest

from app.modules.shop_runner.tasks_manager.tasks_manager import TasksManager, run_tasks

_VAR: ContextVar[str] = ContextVar("_test_shop_var", default="<unset>")


@pytest.mark.unit
@pytest.mark.asyncio
async def test_handler_sees_contextvar_set_before_add_task() -> None:
    """Handler, добавленный в shared TasksManager, видит ContextVar вызывающего."""
    seen: list[str] = []

    async def handler() -> None:
        seen.append(_VAR.get())

    token = _VAR.set("shop-42")
    try:
        manager = TasksManager(max_workers=2)
        future = await manager.add_task(handler)
        await manager.run()
        await future
    finally:
        _VAR.reset(token)

    assert seen == ["shop-42"], f"expected ['shop-42'], got {seen}"


@pytest.mark.unit
@pytest.mark.asyncio
async def test_handler_does_not_see_contextvar_set_after_add_task() -> None:
    """Изменение ContextVar после add_task не видно в handler (snapshot semantics)."""
    seen: list[str] = []

    async def handler() -> None:
        seen.append(_VAR.get())

    token = _VAR.set("before")
    try:
        manager = TasksManager(max_workers=1)
        future = await manager.add_task(handler)
        # Меняем значение ПОСЛЕ постановки задачи
        _VAR.set("after")
        await manager.run()
        await future
    finally:
        _VAR.reset(token)

    # Должен увидеть значение, которое было на момент add_task
    assert seen == ["before"], f"snapshot semantics violated: {seen}"


@pytest.mark.unit
@pytest.mark.asyncio
async def test_different_tasks_see_their_own_context() -> None:
    """Два task-а, добавленные с разными ContextVar, изолированы друг от друга."""
    seen: list[str] = []
    barrier = asyncio.Event()

    async def slow_handler() -> None:
        await barrier.wait()
        seen.append(_VAR.get())

    async def fast_handler() -> None:
        seen.append(_VAR.get())

    manager = TasksManager(max_workers=2)

    token_a = _VAR.set("shop-A")
    fut_slow = await manager.add_task(slow_handler)
    _VAR.reset(token_a)

    token_b = _VAR.set("shop-B")
    fut_fast = await manager.add_task(fast_handler)
    _VAR.reset(token_b)

    manager.start()
    await asyncio.sleep(0.05)   # fast_handler запустился
    barrier.set()               # slow_handler продолжает

    await asyncio.gather(fut_slow, fut_fast)
    await manager.stop()

    assert set(seen) == {"shop-A", "shop-B"}, f"context isolation failed: {seen}"


@pytest.mark.unit
@pytest.mark.asyncio
async def test_run_tasks_preserves_context_in_shared_manager() -> None:
    """run_tasks() с переданным shared tasks_manager сохраняет ContextVar."""
    seen: list[str] = []

    async def handler() -> None:
        seen.append(_VAR.get())

    shared = TasksManager(max_workers=4)
    shared.start()

    token = _VAR.set("shop-shared")
    try:
        await run_tasks(
            [handler, handler],
            max_workers=2,
            tasks_manager=shared,
        )
    finally:
        _VAR.reset(token)

    await shared.stop()

    assert seen == ["shop-shared", "shop-shared"], f"shared TM context failed: {seen}"


@pytest.mark.unit
@pytest.mark.asyncio
async def test_run_tasks_auto_starts_workers_when_shared_manager_idle() -> None:
    """Без run_queue/pytest: run_tasks не должен зависать на пустой очереди."""
    seen: list[int] = []

    async def handler() -> None:
        seen.append(1)

    shared = TasksManager(max_workers=2)
    assert not shared._workers

    await run_tasks([handler, handler], max_workers=2, tasks_manager=shared)

    assert seen == [1, 1]
    assert not shared._workers


@pytest.mark.unit
@pytest.mark.asyncio
async def test_wb_manager_hub_context_reached_inside_shared_worker() -> None:
    """get_wb_manager_from_context() внутри shared worker видит hub без fallback."""
    from contextvars import ContextVar
    from unittest.mock import MagicMock

    _hub_var: ContextVar[object | None] = ContextVar("_hub_test", default=None)

    def get_hub_from_context() -> object:
        hub = _hub_var.get()
        if hub is None:
            raise RuntimeError("WB manager hub not set — fallback would trigger")
        return hub

    fake_hub = MagicMock(name="FakeWBManagerHub")
    reached: list[object] = []

    async def handler() -> None:
        reached.append(get_hub_from_context())

    manager = TasksManager(max_workers=2)
    token = _hub_var.set(fake_hub)
    try:
        future = await manager.add_task(handler)
        await manager.run()
        await future
    finally:
        _hub_var.reset(token)

    assert reached == [fake_hub], "hub not visible in shared worker — fallback would fire"
