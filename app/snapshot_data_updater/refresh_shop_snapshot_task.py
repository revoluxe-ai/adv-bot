"""``RefreshShopSnapshotTask`` — атомарная единица работы на один ``shop_id``.

Один shop task = один полный проход сбора для магазина:
- batch Postgres (все active adv);
- batch Redis / ClickHouse / keyword warmup на уровне shop;
- сбор ``AdvDataSnapshotDTO`` по каждой adv из общих данных (см. ``collector``);
- сохранение ``ShopAdvSnapshotBatchDTO`` в store.

Не создавать вторую task для того же shop_id, пока предыдущая running
(контролирует ``SnapshotUpdater._start_shop_task_if_needed``).
"""

from __future__ import annotations

import asyncio
import logging
import time

from app.snapshot_data_updater.collector import AdvDataSnapshotCollector
from app.snapshot_data_updater.dto import ShopAdvSnapshotBatchDTO
from app.snapshot_data_updater.protocols import AdvDataSnapshotStore

logger = logging.getLogger(__name__)


class RefreshShopSnapshotTask:
    """Сбор и сохранение snapshot-пакета для одного магазина."""

    def __init__(
        self,
        shop_id: str,
        *,
        collector: AdvDataSnapshotCollector,
        store: AdvDataSnapshotStore,
    ) -> None:
        """Args:
            shop_id: идентификатор магазина WB.
            collector: batch-сборщик (shop-level pipeline).
            store: Redis snapshot store или no-op stub.
        """
        self.shop_id = shop_id
        self._collector = collector
        self._store = store
        self._asyncio_task: asyncio.Task[ShopAdvSnapshotBatchDTO] | None = None

    def start(self) -> asyncio.Task[ShopAdvSnapshotBatchDTO]:
        """Запускает фоновую asyncio.Task с ``run()``.

        Returns:
            Созданная задача.

        Raises:
            RuntimeError: если task уже выполняется.
        """
        if self.is_running:
            raise RuntimeError(
                f"RefreshShopSnapshotTask already running for shop_id={self.shop_id}"
            )
        self._asyncio_task = asyncio.create_task(
            self.run(),
            name=f"refresh_shop_snapshot:{self.shop_id}",
        )
        return self._asyncio_task

    @property
    def is_running(self) -> bool:
        """``True``, если asyncio.Task создана и ещё не завершена."""
        return self._asyncio_task is not None and not self._asyncio_task.done()

    @property
    def task(self) -> asyncio.Task[ShopAdvSnapshotBatchDTO] | None:
        """Ссылка на asyncio.Task (для cancel при shutdown)."""
        return self._asyncio_task

    async def run(self) -> ShopAdvSnapshotBatchDTO:
        """Выполняет collect_shop + store.save.

        Returns:
            Сохранённый пакет снимков.

        Side effects:
            Чтение через collector (PG/Redis/CH); запись в snapshot store.
        """
        logger.debug("RefreshShopSnapshotTask started shop_id=%s", self.shop_id)
        t0 = time.perf_counter()
        batch = await self._collector.collect_shop(self.shop_id)
        collect_ms = (time.perf_counter() - t0) * 1000
        t1 = time.perf_counter()
        await self._store.save(batch)
        save_ms = (time.perf_counter() - t1) * 1000
        partial = sum(1 for s in batch.snapshots if s.partial)
        logger.info(
            "RefreshShopSnapshotTask done shop_id=%s snapshots=%d partial=%d "
            "collect_ms=%.1f save_ms=%.1f",
            self.shop_id,
            len(batch.snapshots),
            partial,
            collect_ms,
            save_ms,
        )
        return batch
