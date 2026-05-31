"""Non-blocking inflight guard для shop-корутин (skip, не wait).

Используется, чтобы не запускать второй tick, пока предыдущий ещё держит lock
(в т.ч. orphan после timeout декоратора).
"""

from __future__ import annotations

import asyncio
import logging
from collections.abc import Awaitable, Callable
from typing import TypeVar

from app.modules.shop_runner.service_manager.while_coroutines_decorator import (
    is_pool_timeout_related,
)

logger = logging.getLogger(__name__)

T = TypeVar("T")

# Предупреждение о длинном tick (ниже timeout_sec=900 декоратора).
CLUSTERS_TODAY_TICK_SLOW_WARNING_SEC = 180

ENDPOINT_NORMQUERY_STATS = "_get_adv_v0_normquery_stats"


class CoroutineTickInflightGuard:
    """Per-coroutine ``asyncio.Lock``: второй вход skip без ожидания."""

    def __init__(self) -> None:
        self._lock = asyncio.Lock()

    def is_inflight(self) -> bool:
        return self._lock.locked()

    async def run_or_skip(
        self,
        *,
        shop_id: str,
        coroutine: str,
        endpoint: str,
        body: Callable[[], Awaitable[T]],
    ) -> T | None:
        """Выполнить ``body`` под lock или вернуть ``None`` при skip."""
        if self._lock.locked():
            logger.info(
                "shop_runner tick skipped "
                "(shop_id=%s coroutine=%s endpoint=%s skipped_due_to_inflight=true "
                "duration_sec=0 success=false pool_timeout=false)",
                shop_id,
                coroutine,
                endpoint,
            )
            return None

        loop = asyncio.get_running_loop()
        started_at = loop.time()
        success = False
        pool_timeout = False
        result: T | None = None

        async with self._lock:
            try:
                result = await body()
                success = True
            except BaseException as exc:
                pool_timeout = is_pool_timeout_related(exc)
                raise
            finally:
                duration_sec = loop.time() - started_at
                _log_tick_finished(
                    shop_id=shop_id,
                    coroutine=coroutine,
                    endpoint=endpoint,
                    duration_sec=duration_sec,
                    success=success,
                    pool_timeout=pool_timeout,
                    skipped_due_to_inflight=False,
                )
        return result


def _log_tick_finished(
    *,
    shop_id: str,
    coroutine: str,
    endpoint: str,
    duration_sec: float,
    success: bool,
    pool_timeout: bool,
    skipped_due_to_inflight: bool,
) -> None:
    message = (
        "shop_runner tick finished "
        "(shop_id=%s coroutine=%s endpoint=%s duration_sec=%.3f success=%s "
        "skipped_due_to_inflight=%s pool_timeout=%s)"
    )
    args = (
        shop_id,
        coroutine,
        endpoint,
        duration_sec,
        success,
        skipped_due_to_inflight,
        pool_timeout,
    )
    if duration_sec >= CLUSTERS_TODAY_TICK_SLOW_WARNING_SEC:
        logger.warning(message, *args)
    else:
        logger.info(message, *args)
