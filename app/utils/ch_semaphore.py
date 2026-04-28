"""Ограничение параллельных запросов к ClickHouse (защита от перегрузки).

Семафор привязывается к текущему event loop при входе в контекст: один глобальный
`asyncio.Semaphore` при импорте ломает pytest-asyncio и любые тесты с несколькими
циклами («Semaphore ... is bound to a different event loop»).
"""

from __future__ import annotations

import asyncio
import weakref
from typing import Any


_semaphores: weakref.WeakKeyDictionary[
    asyncio.AbstractEventLoop, asyncio.Semaphore
] = weakref.WeakKeyDictionary()


class _AntiCHCrashSemaphore:
    async def __aenter__(self) -> None:
        loop = asyncio.get_running_loop()
        sem = _semaphores.get(loop)
        if sem is None:
            sem = asyncio.Semaphore(1)
            _semaphores[loop] = sem
        await sem.acquire()

    async def __aexit__(
        self,
        exc_type: type[BaseException] | None,
        exc: BaseException | None,
        tb: Any,
    ) -> None:
        loop = asyncio.get_running_loop()
        sem = _semaphores[loop]
        sem.release()


anti_ch_crash_semaphore = _AntiCHCrashSemaphore()
