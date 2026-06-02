"""``ResourceQueue`` — ограничение параллелизма к Postgres / Redis / ClickHouse / warmup.

Зачем
-----
Snapshot updater на одном shop может дергать сотни adv; без лимитов это перегрузит
PG/CH/Redis. Каждый ``ResourceKind`` имеет свой семафор и таймаут задачи.

Отдельный kind ``CALCULATED_KEYWORDS_WARMUP`` (лимит 1–2) — тяжёлый пересчёт
``get_good_bad_phrases`` не должен идти неограниченно параллельно.

Без retry: при ошибке/таймауте исключение пробрасывается в collector (диагностика).
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
    """Тип внешнего ресурса для отдельной очереди с семафором."""

    POSTGRES = "postgres"
    CLICKHOUSE = "clickhouse"
    REDIS = "redis"
    CALCULATED_KEYWORDS_WARMUP = "calculated_keywords_warmup"


# Стартовые лимиты параллелизма на процесс (можно переопределить в конструкторе).
DEFAULT_CONCURRENCY: dict[ResourceKind, int] = {
    ResourceKind.POSTGRES: 4,
    ResourceKind.CLICKHOUSE: 2,
    ResourceKind.REDIS: 8,
    ResourceKind.CALCULATED_KEYWORDS_WARMUP: 2,
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
    """Набор очередей — по одной на каждый ``ResourceKind``."""

    def __init__(
        self,
        *,
        concurrency: dict[ResourceKind, int] | None = None,
        task_timeout_sec: float = DEFAULT_TASK_TIMEOUT_SEC,
        task_timeout_by_kind: dict[ResourceKind, float] | None = None,
    ) -> None:
        """Args:
            concurrency: переопределение лимитов; иначе ``DEFAULT_CONCURRENCY``.
            task_timeout_sec: таймаут по умолчанию для всех очередей.
            task_timeout_by_kind: переопределение таймаута (например PG отдельно).
        """
        limits = concurrency or DEFAULT_CONCURRENCY
        per_kind = task_timeout_by_kind or {}
        self._queues: dict[ResourceKind, ResourceQueue] = {
            kind: ResourceQueue(
                kind,
                concurrency=limits.get(kind, 4),
                task_timeout_sec=per_kind.get(kind, task_timeout_sec),
            )
            for kind in ResourceKind
        }

    def queue_for(self, kind: ResourceKind) -> ResourceQueue:
        """Доступ к очереди конкретного ресурса."""
        return self._queues[kind]

    def submit(self, task: ResourceTask[T]) -> asyncio.Future[T]:
        """Маршрутизация задачи в очередь по ``task.kind``."""
        return self._queues[task.kind].submit(task)

    async def stop_all(self) -> None:
        """Остановка всех очередей при shutdown ``SnapshotUpdater``."""
        for q in self._queues.values():
            await q.stop()


def build_resource_queue_manager(
    config: object | None = None,
) -> ResourceQueueManager:
    """Собирает очереди с таймаутами из ``SnapshotUpdaterConfig`` / env."""
    from app.snapshot_data_updater.config import (
        SnapshotUpdaterConfig,
        get_snapshot_config,
    )

    if isinstance(config, SnapshotUpdaterConfig):
        cfg = config
    else:
        cfg = get_snapshot_config()

    pg_timeout = (
        cfg.postgres_task_timeout_sec
        if cfg.postgres_task_timeout_sec is not None
        else cfg.resource_task_timeout_sec
    )
    return ResourceQueueManager(
        task_timeout_sec=cfg.resource_task_timeout_sec,
        task_timeout_by_kind={ResourceKind.POSTGRES: pg_timeout},
    )
