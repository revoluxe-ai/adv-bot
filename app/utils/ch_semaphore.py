"""Ограничение параллельных запросов к ClickHouse.

Лимиты и таймауты — из env через ``app.utils.resource_limits`` (см. env.sample).
"""

from __future__ import annotations

import asyncio
import logging
from collections.abc import Awaitable
from typing import Any, TypeVar

from app.utils.resource_limits import (
    clickhouse_query_acquire_timeout_sec,
    clickhouse_query_concurrency,
    clickhouse_query_timeout_sec,
    get_clickhouse_query_semaphore,
)

logger = logging.getLogger(__name__)

T = TypeVar("T")

# Обратная совместимость импортов и тестов
CH_OPERATION_TIMEOUT_SECONDS = 900.0
CH_ACQUIRE_TIMEOUT_SECONDS = 120.0


async def run_ch_with_timeout(
    awaitable: Awaitable[T],
    *,
    timeout: float | None = None,
    acquire_timeout: float | None = None,
) -> T:
    """Выполнить CH-операцию под семафором запросов с таймаутами acquire и operation."""
    op_timeout = (
        clickhouse_query_timeout_sec()
        if timeout is None
        else timeout
    )
    acq_timeout = (
        clickhouse_query_acquire_timeout_sec()
        if acquire_timeout is None
        else acquire_timeout
    )
    loop = asyncio.get_running_loop()
    sem = get_clickhouse_query_semaphore(loop)
    try:
        await asyncio.wait_for(sem.acquire(), timeout=acq_timeout)
    except asyncio.TimeoutError:
        logger.error(
            "ClickHouse query semaphore acquire timed out after %ss "
            "(CLICKHOUSE_QUERY_CONCURRENCY=%s)",
            acq_timeout,
            clickhouse_query_concurrency(),
            exc_info=True,
        )
        raise
    try:
        return await asyncio.wait_for(awaitable, timeout=op_timeout)
    except asyncio.TimeoutError:
        logger.error(
            "ClickHouse query timed out after %ss",
            op_timeout,
            exc_info=True,
        )
        raise
    finally:
        sem.release()


class _AntiCHCrashSemaphore:
    """Контекстный менеджер CH-запроса; для operation timeout — ``run_ch_with_timeout``."""

    async def __aenter__(self) -> _AntiCHCrashSemaphore:
        loop = asyncio.get_running_loop()
        self._sem = get_clickhouse_query_semaphore(loop)
        acq_timeout = clickhouse_query_acquire_timeout_sec()
        try:
            await asyncio.wait_for(self._sem.acquire(), timeout=acq_timeout)
        except asyncio.TimeoutError:
            logger.error(
                "ClickHouse query semaphore acquire timed out after %ss (async with)",
                acq_timeout,
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
