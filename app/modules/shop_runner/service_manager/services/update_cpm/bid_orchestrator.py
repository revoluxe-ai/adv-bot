import asyncio
import logging
from dataclasses import dataclass
from typing import List, Optional

from app.shared.application.dto.update_bids_in_advs.update_bids_search_adv_ids_batch import (
    UpdateBidsSearchAdvInShopBatch,
    UpdateBidForNmidTask,
)
from .wb_api import WBApi

logger = logging.getLogger(__name__)


@dataclass
class BidUpdateResult:
    adv_id: int
    nmid: int
    new_bid: Optional[int] = None
    error: Optional[str] = None


class BidUpdateOrchestrator:
    """Producer-Consumer orchestrator for CPM bid updates.

    Producers compute bids concurrently and push results to a queue.
    Single consumer batches by size or timeout and sends to WB API.
    """

    def __init__(
        self, wb_api: WBApi, max_batch_size: int = 50, queue_size: int = 200
    ) -> None:
        self._wb_api = wb_api
        self._max_batch_size = max_batch_size
        self._queue_size = queue_size
        self._logger = logger

    async def _process_bid_task(self, task: UpdateBidForNmidTask) -> BidUpdateResult:
        try:
            new_bid = await task.new_bid_coro
            return BidUpdateResult(adv_id=task.adv_id, nmid=task.nmid, new_bid=new_bid)
        except Exception as e:
            self._logger.exception("Error processing bid task")
            return BidUpdateResult(adv_id=task.adv_id, nmid=task.nmid, error=str(e))

    async def _producer(
        self, task: UpdateBidForNmidTask, queue: asyncio.Queue[BidUpdateResult]
    ) -> None:
        result = await self._process_bid_task(task)
        if result.error:
            self._logger.debug(
                "producer: skipped result with error",
                extra={
                    "adv_id": result.adv_id,
                    "nmid": result.nmid,
                    "error": result.error,
                },
            )
            return
        if result.new_bid is None:
            self._logger.debug(
                "producer: skipped None bid",
                extra={"adv_id": result.adv_id, "nmid": result.nmid},
            )
            return
        await queue.put(result)

    async def _batch_consumer(
        self, queue: asyncio.Queue[BidUpdateResult], producers_done: asyncio.Event
    ) -> None:
        batch: List[BidUpdateResult] = []
        while True:
            try:
                item = await asyncio.wait_for(queue.get(), timeout=1.0)
                batch.append(item)
                queue.task_done()
            except asyncio.TimeoutError:
                if batch:
                    await self._send_batch(batch)
                    batch = []
            # send if full
            if len(batch) >= self._max_batch_size:
                await self._send_batch(batch)
                batch = []
            # finish condition
            if producers_done.is_set() and queue.empty():
                if batch:
                    await self._send_batch(batch)
                break

    async def _send_batch(self, batch: List[BidUpdateResult]) -> None:
        """Делегируем отправку в локальный WBApi-менеджер (миксины).

        Собираем временный UpdateBidsSearchAdvInShopBatch с уже готовыми ставками,
        оборачивая значения в корутины (ожидается new_bid_coro).
        """
        from app.shared.application.dto.update_bids_in_advs.update_bids_search_adv_ids_batch import (
            UpdateBidsResolvedBatch,
            UpdateBidResolvedTask,
        )

        resolved_batch = UpdateBidsResolvedBatch(self._wb_api.shop_id)

        # Добавляем готовые задачи в батч
        for r in batch:
            if r.new_bid is None:
                continue
            resolved_batch.add_task(
                UpdateBidResolvedTask(r.adv_id, r.nmid, int(r.new_bid))
            )

        # Делегируем миксину. Внутри миксина реализованы правила батчинга/лимитов.
        await self._wb_api.update_bids_in_search_advs_resolved(resolved_batch)

    async def process_updates(
        self, update_batch: UpdateBidsSearchAdvInShopBatch
    ) -> None:
        if not getattr(update_batch, "tasks", []):
            return

        queue: asyncio.Queue[BidUpdateResult] = asyncio.Queue(maxsize=self._queue_size)
        producers_done = asyncio.Event()
        consumer_task = asyncio.create_task(self._batch_consumer(queue, producers_done))

        async with asyncio.TaskGroup() as tg:
            for task in update_batch.tasks:
                tg.create_task(self._producer(task, queue))

        producers_done.set()
        await consumer_task
