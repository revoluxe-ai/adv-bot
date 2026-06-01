"""Process-wide ограничение конкурентности HTTP к WB PROMOTION API.

Все PROMOTION-запросы проходят через ``acquire_promotion_http`` в ``_AuthAsyncProxy.request``.
"""

from __future__ import annotations

import asyncio
import time
from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager
from dataclasses import dataclass
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from app.settings.settings_master import Settings

WAIT_WARN_SEC = 1.0

_global_semaphore: asyncio.Semaphore | None = None


@dataclass(frozen=True)
class PromotionHttpTiming:
    """Диагностический snapshot захвата PROMOTION semaphore."""

    wait_semaphore_sec: float
    in_flight: int
    limit: int


def _get_settings() -> Settings:
    from app.settings import settings

    return settings


def _get_global_limit() -> int:
    limit = _get_settings().PROMOTION_HTTP_CONCURRENCY_LIMIT
    return max(1, limit)


def get_promotion_global_semaphore() -> asyncio.Semaphore:
    """Process-wide semaphore для всех PROMOTION HTTP calls."""
    global _global_semaphore
    if _global_semaphore is None:
        _global_semaphore = asyncio.Semaphore(_get_global_limit())
    return _global_semaphore


def reset_promotion_http_concurrency_state() -> None:
    """Сброс singleton state (только unit-тесты)."""
    global _global_semaphore
    _global_semaphore = None


@asynccontextmanager
async def acquire_promotion_http() -> AsyncGenerator[PromotionHttpTiming, None]:
    """Захват global semaphore перед PROMOTION HTTP request.

    shop_id/endpoint логируются в ``_AuthAsyncProxy.request`` после release sem.
    """
    sem = get_promotion_global_semaphore()
    limit = _get_global_limit()
    wait_started = time.monotonic()
    await sem.acquire()
    wait_sec = time.monotonic() - wait_started
    try:
        yield PromotionHttpTiming(
            wait_semaphore_sec=wait_sec,
            in_flight=_get_in_flight_count(sem, limit),
            limit=limit,
        )
    finally:
        sem.release()


def _get_in_flight_count(sem: asyncio.Semaphore, limit: int) -> int:
    """Вернуть примерное число in-flight PROMOTION requests для диагностики."""
    current_value = getattr(sem, "_value", None)
    if isinstance(current_value, int):
        return max(0, limit - current_value)
    return -1
