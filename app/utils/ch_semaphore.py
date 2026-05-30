"""Ограничение параллельных запросов к ClickHouse (защита от перегрузки).

Семафор привязывается к текущему event loop при входе в контекст: один глобальный
`asyncio.Semaphore` при импорте ломает pytest-asyncio и любые тесты с несколькими
циклами («Semaphore ... is bound to a different event loop»).

``run_ch_with_timeout`` — предпочтительный путь: acquire + operation timeout + release.
"""

from __future__ import annotations

import asyncio
import logging
import weakref
from collections.abc import Awaitable
from typing import Any, TypeVar

logger = logging.getLogger(__name__)

T = TypeVar("T")

CH_OPERATION_TIMEOUT_SECONDS = 900.0
CH_ACQUIRE_TIMEOUT_SECONDS = 120.0

_semaphores: weakref.WeakKeyDictionary[
    asyncio.AbstractEventLoop, asyncio.Semaphore
] = weakref.WeakKeyDictionary()


def _get_loop_semaphore(loop: asyncio.AbstractEventLoop) -> asyncio.Semaphore:
    sem = _semaphores.get(loop)
    if sem is None:
        sem = asyncio.Semaphore(1)
        _semaphores[loop] = sem
    return sem


async def run_ch_with_timeout(
    awaitable: Awaitable[T],
    *,
    timeout: float = CH_OPERATION_TIMEOUT_SECONDS,
    acquire_timeout: float = CH_ACQUIRE_TIMEOUT_SECONDS,
) -> T:
    """Выполнить CH-операцию под Semaphore(1) с таймаутом acquire и operation."""
    loop = asyncio.get_running_loop()
    sem = _get_loop_semaphore(loop)
    try:
        await asyncio.wait_for(sem.acquire(), timeout=acquire_timeout)
    except asyncio.TimeoutError:
        logger.error(
            "ClickHouse semaphore acquire timed out after %ss",
            acquire_timeout,
            exc_info=True,
        )
        raise
    try:
        return await asyncio.wait_for(awaitable, timeout=timeout)
    except asyncio.TimeoutError:
        logger.error(
            "ClickHouse operation timed out after %ss",
            timeout,
            exc_info=True,
        )
        raise
    finally:
        sem.release()


class _AntiCHCrashSemaphore:
    """Контекстный менеджер Semaphore(1); для operation timeout используйте ``run_ch_with_timeout``."""

    async def __aenter__(self) -> _AntiCHCrashSemaphore:
        loop = asyncio.get_running_loop()
        self._sem = _get_loop_semaphore(loop)
        try:
            await asyncio.wait_for(
                self._sem.acquire(), timeout=CH_ACQUIRE_TIMEOUT_SECONDS
            )
        except asyncio.TimeoutError:
            logger.error(
                "ClickHouse semaphore acquire timed out after %ss (async with)",
                CH_ACQUIRE_TIMEOUT_SECONDS,
                exc_info=True,
            )
            raise
        return self

    async def __aexit__(
        self,
        exc_type: type[BaseException] | None,
        exc: BaseException | None,
        tb: Any,
    ) -> None:
        self._sem.release()


anti_ch_crash_semaphore = _AntiCHCrashSemaphore()
