"""Process-wide ограничение конкурентности HTTP к WB PROMOTION API.

Все PROMOTION-запросы проходят через ``acquire_promotion_http`` в ``_AuthAsyncProxy.request``.
"""

from __future__ import annotations

import asyncio
import logging
import time
from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from app.settings.settings_master import Settings

logger = logging.getLogger(__name__)

WAIT_WARN_SEC = 1.0

_global_semaphore: asyncio.Semaphore | None = None


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
async def acquire_promotion_http(
    *,
    shop_id: str | None,
    http_method: str | None = None,
    endpoint: str | None = None,
) -> AsyncGenerator[None, None]:
    """Захват global semaphore перед PROMOTION HTTP request."""
    sem = get_promotion_global_semaphore()
    wait_started = time.monotonic()
    await sem.acquire()
    wait_sec = time.monotonic() - wait_started
    try:
        if wait_sec >= WAIT_WARN_SEC:
            logger.warning(
                "section=PROMOTION wait_sec=%.3f limit=%s endpoint=%s shop_id=%s",
                wait_sec,
                _get_global_limit(),
                _format_endpoint(http_method, endpoint),
                shop_id or "—",
            )
        yield
    finally:
        sem.release()


def _format_endpoint(http_method: str | None, endpoint: str | None) -> str:
    if http_method and endpoint:
        return f"{http_method} {endpoint}"
    if endpoint:
        return endpoint
    return "—"
