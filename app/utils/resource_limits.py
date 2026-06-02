"""Единые лимиты параллельных **запросов** к Postgres и ClickHouse (env).

Используются во всех процессах (shop-runner, snapshot updater, warmup):
- PG: ``get_async_session_maker`` (семафор на сессию/запрос);
- CH: ``run_ch_with_timeout`` / ``anti_ch_crash_semaphore``.

Не путать с лимитами «задач» shop-runner (``TasksManager.max_workers``) и HTTP WB API.
"""

from __future__ import annotations

import asyncio
import os
import weakref

_postgres_semaphores: weakref.WeakKeyDictionary[
    asyncio.AbstractEventLoop, asyncio.Semaphore
] = weakref.WeakKeyDictionary()
_clickhouse_semaphores: weakref.WeakKeyDictionary[
    asyncio.AbstractEventLoop, asyncio.Semaphore
] = weakref.WeakKeyDictionary()


def _env_int(name: str, default: int) -> int:
    raw = os.getenv(name)
    if raw is None or not raw.strip():
        return default
    return int(raw)


def _env_float(name: str, default: float) -> float:
    raw = os.getenv(name)
    if raw is None or not raw.strip():
        return default
    return float(raw)


def postgres_query_concurrency() -> int:
    """Макс. одновременных PG-сессий/запросов на event loop."""
    if os.getenv("POSTGRES_QUERY_CONCURRENCY"):
        return _env_int("POSTGRES_QUERY_CONCURRENCY", 10)
    return _env_int("COUNT_SEMAPHORE_TO_POSTGRES", 10)


def clickhouse_query_concurrency() -> int:
    """Макс. одновременных CH-запросов на event loop."""
    return _env_int("CLICKHOUSE_QUERY_CONCURRENCY", 2)


def clickhouse_query_acquire_timeout_sec() -> float:
    """Сколько ждать свободный слот CH перед TimeoutError."""
    if os.getenv("CLICKHOUSE_QUERY_ACQUIRE_TIMEOUT_SEC"):
        return _env_float("CLICKHOUSE_QUERY_ACQUIRE_TIMEOUT_SEC", 120.0)
    return _env_float("CH_ACQUIRE_TIMEOUT_SECONDS", 120.0)


def clickhouse_query_timeout_sec() -> float:
    """Таймаут выполнения одного CH-запроса после acquire."""
    if os.getenv("CLICKHOUSE_QUERY_TIMEOUT_SEC"):
        return _env_float("CLICKHOUSE_QUERY_TIMEOUT_SEC", 900.0)
    return _env_float("CH_OPERATION_TIMEOUT_SECONDS", 900.0)


def redis_query_concurrency() -> int:
    """Макс. параллельных Redis-операций snapshot collector (на loop)."""
    if os.getenv("SNAPSHOT_REDIS_QUERY_CONCURRENCY"):
        return _env_int("SNAPSHOT_REDIS_QUERY_CONCURRENCY", 8)
    return _env_int("REDIS_QUERY_CONCURRENCY", 8)


def get_postgres_query_semaphore(
    loop: asyncio.AbstractEventLoop | None = None,
) -> asyncio.Semaphore:
    """Семафор PG-запросов для текущего event loop."""
    event_loop = loop or asyncio.get_running_loop()
    sem = _postgres_semaphores.get(event_loop)
    if sem is None:
        sem = asyncio.Semaphore(postgres_query_concurrency())
        _postgres_semaphores[event_loop] = sem
    return sem


def get_clickhouse_query_semaphore(
    loop: asyncio.AbstractEventLoop | None = None,
) -> asyncio.Semaphore:
    """Семафор CH-запросов для текущего event loop."""
    event_loop = loop or asyncio.get_running_loop()
    sem = _clickhouse_semaphores.get(event_loop)
    if sem is None:
        sem = asyncio.Semaphore(clickhouse_query_concurrency())
        _clickhouse_semaphores[event_loop] = sem
    return sem
