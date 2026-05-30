import asyncio
import logging
from collections import deque
from dataclasses import dataclass
from collections.abc import Awaitable, Callable, Sequence
from typing import Any, Optional

logger = logging.getLogger(__name__)

# Опциональный таймаут handler в worker; None — прежнее поведение без ограничения.
DEFAULT_TASK_HANDLER_TIMEOUT_SECONDS: float | None = None


@dataclass
class _TaskEntry:
    handler: Callable[[], Awaitable[Any]]
    future: asyncio.Future[Any]


def _handler_label(handler: Callable[[], Awaitable[Any]]) -> str:
    return getattr(handler, "__name__", repr(handler))


class TasksManager:
    def __init__(
        self,
        max_workers: int,
        *,
        handler_timeout_sec: float | None = DEFAULT_TASK_HANDLER_TIMEOUT_SECONDS,
    ):
        self._queue: asyncio.Queue[_TaskEntry] = asyncio.Queue()
        self._max_workers = max_workers
        self._workers: list[asyncio.Task[None]] = []
        self._handler_timeout_sec = handler_timeout_sec

    def start(self) -> None:
        self._start_workers()

    async def stop(self) -> None:
        await self._stop_workers()

    async def run_queue(self, stop_event: asyncio.Event) -> None:
        logger.debug(f"Starting task queue with {self._max_workers} workers")
        self._start_workers()
        try:
            _ = await stop_event.wait()
        finally:
            logger.debug("Stopping task queue")
            await self._stop_workers()

    async def add_task(self, handler: Callable[[], Awaitable[Any]]) -> asyncio.Future[Any]:
        future: asyncio.Future[Any] = asyncio.get_running_loop().create_future()
        await self._queue.put(_TaskEntry(handler=handler, future=future))
        return future

    async def run(self) -> None:
        self._start_workers()
        try:
            await self._queue.join()
        finally:
            await self._stop_workers()

    def _start_workers(self) -> None:
        if self._workers:
            return
        for index in range(self._max_workers):
            worker = asyncio.create_task(self._worker(), name=f"tasks-manager-{index}")
            self._workers.append(worker)

    async def _stop_workers(self) -> None:
        for worker in self._workers:
            _ = worker.cancel()
        if self._workers:
            _ = await asyncio.gather(*self._workers, return_exceptions=True)
        self._workers = []

    async def _run_handler(self, handler: Callable[[], Awaitable[Any]]) -> Any:
        if self._handler_timeout_sec is None:
            return await handler()
        return await asyncio.wait_for(handler(), timeout=self._handler_timeout_sec)

    async def _worker(self) -> None:
        while True:
            try:
                entry = await self._queue.get()
            except asyncio.CancelledError:
                break

            handler_name = _handler_label(entry.handler)
            loop = asyncio.get_running_loop()
            started_at = loop.time()
            try:
                result = await self._run_handler(entry.handler)
            except asyncio.CancelledError:
                _ = entry.future.cancel()
                raise
            except asyncio.TimeoutError:
                elapsed = loop.time() - started_at
                timeout_exc = asyncio.TimeoutError(
                    f"TasksManager handler timed out after {self._handler_timeout_sec}s: "
                    f"{handler_name}"
                )
                if not entry.future.done():
                    entry.future.set_exception(timeout_exc)
                logger.error(
                    "Таймаут задачи TasksManager "
                    "(handler=%s, timeout_sec=%s, elapsed=%.3f)",
                    handler_name,
                    self._handler_timeout_sec,
                    elapsed,
                    exc_info=True,
                )
            except Exception as exc:
                if not entry.future.done():
                    entry.future.set_exception(exc)
                logger.exception("Ошибка задачи: %s", exc, exc_info=True)
            else:
                if not entry.future.done():
                    entry.future.set_result(result)
            finally:
                self._queue.task_done()


async def run_tasks(
    handlers: Sequence[Callable[[], Awaitable[Any]]],
    *,
    max_workers: int,
    return_exceptions: bool = True,
    tasks_manager: Optional["TasksManager"] = None,
) -> list[Any]:
    owns_manager = tasks_manager is None
    manager = tasks_manager or TasksManager(max_workers=max_workers)
    semaphore = None
    wrapped_handlers: Sequence[Callable[[], Awaitable[Any]]] = handlers
    if tasks_manager is not None:
        semaphore = asyncio.Semaphore(max_workers)

        async def _bounded(handler: Callable[[], Awaitable[Any]]) -> Any:
            async with semaphore:
                return await handler()

        wrapped_handlers = [lambda handler_=handler: _bounded(handler_) for handler in handlers]
    futures: deque[asyncio.Future[Any]] = deque()
    for handler in wrapped_handlers:
        future = await manager.add_task(handler)
        futures.append(future)

    if owns_manager:
        await manager.run()
    else:
        _ = await asyncio.gather(*futures, return_exceptions=True)

    results: list[Any] = []
    for future in futures:
        if future.cancelled():
            exc = asyncio.CancelledError()
            if return_exceptions:
                results.append(exc)
                continue
            raise exc
        try:
            results.append(future.result())
        except Exception as exc:
            if return_exceptions:
                results.append(exc)
            else:
                raise
    return results
