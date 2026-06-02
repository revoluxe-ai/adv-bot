"""Очередь с семафором + таймаутом для тяжёлых фаз snapshot collector.

Зачем
-----
При сборке снимка магазина параллельно читаются min_bids и keywords из Redis.
Без лимита десятки одновременных ``redis.get`` могут забить connection pool.

Что делает ``ResourceQueue``
----------------------------
- ``concurrency`` — макс. параллельных задач (env ``REDIS_QUERY_CONCURRENCY``);
- ``task_timeout_sec`` — ``asyncio.wait_for`` на одну задачу (env
  ``SNAPSHOT_RESOURCE_TASK_TIMEOUT_SEC``), иначе фаза висит в tick.

Что **не** идёт через этот модуль (лимиты в другом месте)
---------------------------------------------------------
- **Postgres** (``pg:shop_load``) — прямой ``await`` в collector,
  слоты ``POSTGRES_QUERY_CONCURRENCY`` + таймаут сессии в ``session_maker``;
- **ClickHouse** (plan_fact, cluster_texts) — ``run_ch_with_timeout`` /
  ``CLICKHOUSE_QUERY_*``;
- **Warmup keywords** — ``get_good_bad_phrases`` + глобальный CH semaphore.

Активная очередь одна: ``ResourceKind.REDIS`` (batch min_bids, fallback keywords).

``task_timeout_by_kind``
----------------------
Переопределение таймаута по виду ресурса при **создании** очереди в
``ResourceQueueManager``. Сейчас в manager только Redis — на практике важен
``task_timeout_sec`` (или ``task_timeout_by_kind[REDIS]`` в тестах).
Значения для ``POSTGRES`` / ``CLICKHOUSE`` в dict не создают очередей (legacy enum).
"""

from __future__ import annotations

import asyncio
import logging
from collections.abc import Awaitable, Callable
from dataclasses import dataclass
from enum import StrEnum
from typing import Generic, TypeVar

logger = logging.getLogger(__name__)

T = TypeVar("T")


class ResourceKind(StrEnum):
    """Метка задачи для ``ResourceQueueManager.submit`` (очередь есть только у REDIS)."""

    REDIS = "redis"
    # Не создают очередь в ResourceQueueManager — оставлены для имён задач / совместимости.
    POSTGRES = "postgres"
    CLICKHOUSE = "clickhouse"
    CALCULATED_KEYWORDS_WARMUP = "calculated_keywords_warmup"


def _default_redis_concurrency() -> int:
    from app.utils.resource_limits import redis_query_concurrency

    return redis_query_concurrency()


DEFAULT_CONCURRENCY: dict[ResourceKind, int] = {
    ResourceKind.REDIS: 8,
}

DEFAULT_TASK_TIMEOUT_SEC: float = 30.0


@dataclass(frozen=True)
class ResourceTask(Generic[T]):
    """Описание одной задачи чтения/прогрева для очереди.

    Attributes:
        kind: какую очередь использовать.
        name: имя для логов/asyncio task (например ``pg:shop_load:shop123``).
        coro_factory: фабрика корутины без аргументов (захват через lambda снаружи).
    """

    kind: ResourceKind
    name: str
    coro_factory: Callable[[], Awaitable[T]]


class ResourceQueue:
    """Очередь с семафором на один ``ResourceKind``."""

    def __init__(
        self,
        kind: ResourceKind,
        *,
        concurrency: int,
        task_timeout_sec: float = DEFAULT_TASK_TIMEOUT_SEC,
    ) -> None:
        """Args:
            kind: тип ресурса (для логов).
            concurrency: макс. одновременных задач.
            task_timeout_sec: таймаут одной задачи (``asyncio.wait_for``).
        """
        self._kind = kind
        self._semaphore = asyncio.Semaphore(concurrency)
        self._task_timeout_sec = task_timeout_sec
        self._stopped = False
        self._pending: set[asyncio.Task[None]] = set()

    @property
    def kind(self) -> ResourceKind:
        return self._kind

    def submit(self, task: ResourceTask[T]) -> asyncio.Future[T]:
        """Ставит задачу в очередь; возвращает Future с результатом или исключением."""
        if self._stopped:
            raise RuntimeError(f"ResourceQueue {self._kind.value} is stopped")
        if task.kind != self._kind:
            raise ValueError(
                f"Task kind {task.kind} does not match queue {self._kind}"
            )
        loop = asyncio.get_running_loop()
        future: asyncio.Future[T] = loop.create_future()

        async def _runner() -> None:
            async with self._semaphore:
                try:
                    result = await asyncio.wait_for(
                        task.coro_factory(),
                        timeout=self._task_timeout_sec,
                    )
                except TimeoutError:
                    if not future.done():
                        future.set_exception(
                            TimeoutError(
                                f"{task.name} timed out after "
                                f"{self._task_timeout_sec}s"
                            )
                        )
                    return
                except Exception as exc:
                    if not future.done():
                        future.set_exception(exc)
                    return
                if not future.done():
                    future.set_result(result)

        runner = asyncio.create_task(_runner(), name=f"rq:{task.name}")
        self._pending.add(runner)
        runner.add_done_callback(self._pending.discard)
        return future

    async def stop(self) -> None:
        """Запрет новых submit и отмена pending runners (shutdown процесса)."""
        self._stopped = True
        pending = list(self._pending)
        for t in pending:
            t.cancel()
        if pending:
            await asyncio.gather(*pending, return_exceptions=True)


class ResourceQueueManager:
    """Маршрутизатор ``ResourceTask`` → очередь с семафором.

    В production создаётся только очередь **Redis** (см. ``build_resource_queue_manager``).
    """

    def __init__(
        self,
        *,
        concurrency: dict[ResourceKind, int] | None = None,
        task_timeout_sec: float = DEFAULT_TASK_TIMEOUT_SEC,
        task_timeout_by_kind: dict[ResourceKind, float] | None = None,
    ) -> None:
        """Args:
            concurrency: лимит параллелизма; для Redis — ``REDIS_QUERY_CONCURRENCY``.
            task_timeout_sec: таймаут задач Redis, если нет переопределения в ``task_timeout_by_kind``.
            task_timeout_by_kind: опционально ``{ResourceKind.REDIS: сек}``; ключи PG/CH
                без очереди в ``_queues`` не используются (не ошибка, просто запас API).
        """
        by_kind = dict(task_timeout_by_kind or {})

        def _timeout_for(kind: ResourceKind) -> float:
            # Для единственной Redis-очереди: SNAPSHOT_RESOURCE_TASK_TIMEOUT_SEC или override.
            return by_kind.get(kind, task_timeout_sec)

        redis_limit = (concurrency or {}).get(
            ResourceKind.REDIS, _default_redis_concurrency()
        )
        self._queues: dict[ResourceKind, ResourceQueue] = {
            ResourceKind.REDIS: ResourceQueue(
                ResourceKind.REDIS,
                concurrency=redis_limit,
                task_timeout_sec=_timeout_for(ResourceKind.REDIS),
            )
        }

    def queue_for(self, kind: ResourceKind) -> ResourceQueue:
        """Доступ к очереди конкретного ресурса."""
        return self._queues[kind]

    def submit(self, task: ResourceTask[T]) -> asyncio.Future[T]:
        """Маршрутизация задачи в очередь по ``task.kind`` (только Redis)."""
        try:
            queue = self._queues[task.kind]
        except KeyError as exc:
            raise ValueError(
                f"ResourceQueueManager has no queue for {task.kind!r}; "
                "PG/CH use global query semaphores (POSTGRES_QUERY_CONCURRENCY, "
                "CLICKHOUSE_QUERY_CONCURRENCY)."
            ) from exc
        return queue.submit(task)

    async def stop_all(self) -> None:
        """Остановка всех очередей при shutdown ``SnapshotUpdater``."""
        for q in self._queues.values():
            await q.stop()


def build_resource_queue_manager(
    config: object | None = None,
) -> ResourceQueueManager:
    """Фабрика для ``AdvDataSnapshotCollector``: одна Redis-очередь из env.

    Используется ``cfg.resource_task_timeout_sec`` → ``SNAPSHOT_RESOURCE_TASK_TIMEOUT_SEC``.
    ``postgres_task_timeout_sec`` / ``SNAPSHOT_PG_TASK_TIMEOUT_SEC`` сюда **не** подключаются:
    загрузка PG в collector не идёт через ResourceQueue (см. module docstring).
    """
    from app.snapshot_data_updater.config import (
        SnapshotUpdaterConfig,
        get_snapshot_config,
    )

    if isinstance(config, SnapshotUpdaterConfig):
        cfg = config
    else:
        cfg = get_snapshot_config()

    return ResourceQueueManager(
        concurrency={ResourceKind.REDIS: _default_redis_concurrency()},
        task_timeout_sec=cfg.resource_task_timeout_sec,
    )
