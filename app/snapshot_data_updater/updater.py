"""``SnapshotUpdater`` — планировщик global tick и shop-level задач.

Архитектура scheduling (см. roadmap)
------------------------------------
1. Процесс крутится в цикле с паузой ``refresh_interval_sec`` (env:
   ``SNAPSHOT_REFRESH_INTERVAL_SEC``, по умолчанию 300 с).
2. На каждом **global tick**:
   - ``ShopIdDiscovery.discover_shop_ids()``;
   - для каждого shop_id создаётся ``RefreshShopSnapshotTask`` (если ещё не running);
   - shop, выпавший из active list, отменяется.
3. **Не** запускается второй global tick параллельно:
   - ``tick_policy=skip`` — пропуск с warning;
   - ``tick_policy=wait`` — ожидание на ``asyncio.Lock``.
4. **Не** создаётся дубль shop task, если предыдущая по этому shop_id ещё выполняется.

Stub vs live задаётся на уровне фабрики (``build_snapshot_updater``), не в этом модуле.
"""

from __future__ import annotations

import asyncio
import logging
from collections.abc import Sequence

from app.snapshot_data_updater.assembler import AdvDataSnapshotAssembler
from app.snapshot_data_updater.cache.redis_adv_data_snapshot_store import (
    RedisAdvDataSnapshotStore,
)
from app.snapshot_data_updater.collector import AdvDataSnapshotCollector
from app.snapshot_data_updater.config import DEFAULT_CONFIG, SnapshotUpdaterConfig
from app.snapshot_data_updater.dto import ShopAdvSnapshotBatchDTO
from app.snapshot_data_updater.providers import (
    StubClickHouseSnapshotProvider,
    StubPostgresSnapshotProvider,
    StubRedisSnapshotProvider,
)
from app.snapshot_data_updater.protocols import (
    AdvDataSnapshotStore,
    ShopIdDiscovery,
)
from app.snapshot_data_updater.refresh_shop_snapshot_task import (
    RefreshShopSnapshotTask,
)
from app.snapshot_data_updater.resource_queue import (
    ResourceQueueManager,
    build_resource_queue_manager,
)

logger = logging.getLogger(__name__)


class StubShopIdDiscovery:
    """Фиксированный список shop_id (unit-тесты, smoke, ручной один магазин)."""

    def __init__(self, shop_ids: Sequence[str] | None = None) -> None:
        """Args:
            shop_ids: список магазинов; по умолчанию один ``stub-shop``.
        """
        self._shop_ids: tuple[str, ...] = tuple(shop_ids or ("stub-shop",))

    async def discover_shop_ids(self) -> Sequence[str]:
        """Возвращает заданный при создании список."""
        return self._shop_ids


class SnapshotUpdater:
    """Оркестратор фонового обновления snapshot по магазинам.

    Не выполняет I/O сам — делегирует ``AdvDataSnapshotCollector`` и
    ``AdvDataSnapshotStore`` внутри ``RefreshShopSnapshotTask``.
    """

    def __init__(
        self,
        *,
        collector: AdvDataSnapshotCollector,
        store: AdvDataSnapshotStore,
        shop_discovery: ShopIdDiscovery,
        resource_queues: ResourceQueueManager | None = None,
        config: SnapshotUpdaterConfig | None = None,
        refresh_interval_sec: float | None = None,
    ) -> None:
        """Args:
            collector: shop-level batch-сборщик снимков.
            store: сохранение ``ShopAdvSnapshotBatchDTO`` (Redis или no-op).
            shop_discovery: источник активных shop_id.
            resource_queues: общие очереди PG/CH/Redis/warmup; если None — из collector.
            config: флаги tick_policy, интервал и consumer adapters.
            refresh_interval_sec: переопределение интервала tick (сек).
        """
        self._collector = collector
        self._store = store
        self._shop_discovery = shop_discovery
        self._config = config or DEFAULT_CONFIG
        self._queues: ResourceQueueManager = (
            resource_queues or collector.resource_queues
        )
        self._refresh_interval_sec = (
            refresh_interval_sec
            if refresh_interval_sec is not None
            else self._config.refresh_interval_sec
        )
        # skip = не ждать предыдущий tick; wait = блокироваться на Lock
        self._tick_skip_if_busy = self._config.tick_policy != "wait"
        self._tick_lock = asyncio.Lock()
        # shop_id -> текущая RefreshShopSnapshotTask (не более одной running)
        self._shop_tasks: dict[str, RefreshShopSnapshotTask] = {}

    async def run(self, *, stop_event: asyncio.Event) -> None:
        """Главный цикл процесса до установки ``stop_event``.

        На каждой итерации: global tick, затем sleep до ``refresh_interval_sec``
        или до stop.

        Args:
            stop_event: внешний сигнал остановки (корневой ``updater.py``).
        """
        logger.info(
            "SnapshotUpdater started refresh_interval_sec=%.1f tick_policy=%s",
            self._refresh_interval_sec,
            "skip" if self._tick_skip_if_busy else "wait",
        )
        try:
            while not stop_event.is_set():
                await self._run_global_tick()
                try:
                    await asyncio.wait_for(
                        stop_event.wait(),
                        timeout=self._refresh_interval_sec,
                    )
                except TimeoutError:
                    pass
        finally:
            await self._shutdown_shop_tasks()
            await self._queues.stop_all()
            logger.info("SnapshotUpdater stopped")

    async def refresh_shop(self, shop_id: str) -> ShopAdvSnapshotBatchDTO:
        """Один синхронный проход collect+save (тесты, ручной smoke).

        Не регистрируется в ``_shop_tasks`` — не конфликтует с фоновым tick.

        Args:
            shop_id: идентификатор магазина WB.

        Returns:
            Собранный и сохранённый пакет снимков.
        """
        task = RefreshShopSnapshotTask(
            shop_id,
            collector=self._collector,
            store=self._store,
        )
        return await task.run()

    async def _run_global_tick(self) -> None:
        """Один global tick: discover + старт shop tasks + prune неактивных."""
        if self._tick_skip_if_busy and self._tick_lock.locked():
            logger.warning(
                "Snapshot global tick skipped: previous tick still running"
            )
            return

        async with self._tick_lock:
            shop_ids = list(await self._shop_discovery.discover_shop_ids())
            active = set(shop_ids)
            logger.debug(
                "Snapshot global tick shops=%d ids=%s",
                len(shop_ids),
                shop_ids[:10],
            )
            for shop_id in shop_ids:
                self._start_shop_task_if_needed(shop_id)
            self._prune_inactive_shop_tasks(active)

    def _start_shop_task_if_needed(self, shop_id: str) -> None:
        """Создаёт ``RefreshShopSnapshotTask``, если по shop нет running task."""
        existing = self._shop_tasks.get(shop_id)
        if existing is not None and existing.is_running:
            logger.debug(
                "Snapshot shop task skip duplicate shop_id=%s (still running)",
                shop_id,
            )
            return
        if existing is not None and not existing.is_running:
            self._shop_tasks.pop(shop_id, None)

        shop_task = RefreshShopSnapshotTask(
            shop_id,
            collector=self._collector,
            store=self._store,
        )
        asyncio_task = shop_task.start()
        asyncio_task.add_done_callback(
            self._make_shop_done_callback(shop_id, shop_task)
        )
        self._shop_tasks[shop_id] = shop_task
        logger.debug("Snapshot shop task started shop_id=%s", shop_id)

    def _prune_inactive_shop_tasks(self, active_shop_ids: set[str]) -> None:
        """Отменяет shop tasks для магазинов, пропавших из active discovery."""
        for shop_id in tuple(self._shop_tasks.keys()):
            if shop_id in active_shop_ids:
                continue
            handle = self._shop_tasks.pop(shop_id)
            if handle.is_running and handle.task is not None:
                handle.task.cancel()
                logger.debug(
                    "Snapshot shop task cancelled (shop inactive) shop_id=%s",
                    shop_id,
                )

    def _make_shop_done_callback(
        self, shop_id: str, shop_task: RefreshShopSnapshotTask
    ) -> object:
        """Callback очистки registry после завершения asyncio.Task."""

        def _on_done(task: asyncio.Task[ShopAdvSnapshotBatchDTO]) -> None:
            if task.cancelled():
                return
            exc = task.exception()
            if exc is not None:
                logger.exception(
                    "Snapshot shop task failed shop_id=%s",
                    shop_id,
                    exc_info=exc,
                )
            current = self._shop_tasks.get(shop_id)
            if current is shop_task:
                self._shop_tasks.pop(shop_id, None)

        return _on_done

    async def _shutdown_shop_tasks(self) -> None:
        """Отмена всех running shop tasks при остановке процесса."""
        tasks: list[asyncio.Task[ShopAdvSnapshotBatchDTO]] = []
        for handle in list(self._shop_tasks.values()):
            if handle.task is not None and not handle.task.done():
                handle.task.cancel()
                tasks.append(handle.task)
        if tasks:
            await asyncio.gather(*tasks, return_exceptions=True)
        self._shop_tasks.clear()


def _default_stub_config(refresh_interval_sec: float) -> SnapshotUpdaterConfig:
    """Конфиг stub-стека: не зависит от ``SNAPSHOT_TICK_POLICY`` в .env (тесты)."""
    return SnapshotUpdaterConfig(
        use_live_updater=False,
        tick_policy="skip",
        refresh_interval_sec=refresh_interval_sec,
    )


def build_snapshot_updater_stub(
    *,
    shop_ids: Sequence[str] | None = None,
    refresh_interval_sec: float = 0.05,
    config: SnapshotUpdaterConfig | None = None,
) -> SnapshotUpdater:
    """Stub-стек: фиктивные провайдеры, store no-op, короткий tick для тестов.

    Используется когда ``use_live_updater=False`` (режим по умолчанию).
    Не требует Postgres/Redis/ClickHouse.

    Args:
        shop_ids: магазины для ``StubShopIdDiscovery``.
        refresh_interval_sec: интервал tick в тестах (маленький).
        config: переопределение; по умолчанию stub с ``tick_policy=skip``.

    Returns:
        ``SnapshotUpdater`` без live I/O.
    """
    cfg = config or _default_stub_config(refresh_interval_sec)
    queues = build_resource_queue_manager(cfg)
    collector = AdvDataSnapshotCollector(
        postgres=StubPostgresSnapshotProvider(),
        clickhouse=StubClickHouseSnapshotProvider(),
        redis=StubRedisSnapshotProvider(default_cache_hit=True),
        assembler=AdvDataSnapshotAssembler(),
        resource_queues=queues,
    )
    return SnapshotUpdater(
        collector=collector,
        store=RedisAdvDataSnapshotStore(no_op=True),
        shop_discovery=StubShopIdDiscovery(shop_ids),
        resource_queues=queues,
        config=cfg,
        refresh_interval_sec=cfg.refresh_interval_sec,
    )
