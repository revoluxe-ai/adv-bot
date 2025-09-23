import asyncio
import logging
from dataclasses import dataclass
from typing import List, Optional, Dict

from app.shared.application.dto.update_bids_in_advs.update_bids_search_adv_ids_batch import (
    UpdateBidsSearchAdvInShopBatch,
    UpdateBidForNmidTask,
)

logger = logging.getLogger(__name__)


@dataclass
class BidUpdateResult:
    adv_id: int
    nmid: int
    new_bid: Optional[int] = None


class BidUpdateOrchestrator:
    """Producer-Consumer orchestrator for CPM bid updates (per TЗ).

    - One producer per task computes new_bid and enqueues non-None results.
    - Single consumer batches results by timeout/size and delegates PATCH to WBApiCpmUpdater.
    """

    def __init__(self, shop_id: str, cpm_updater, max_batch_size: int = 50, queue_size: int = 200) -> None:
        self._shop_id = shop_id
        self._cpm_updater = cpm_updater
        self._max_batch_size = max_batch_size
        self._queue: asyncio.Queue[BidUpdateResult] = asyncio.Queue(maxsize=queue_size)
        self._logger = logger

    async def _process_bid_task(self, task: UpdateBidForNmidTask) -> Optional[BidUpdateResult]:
        try:
            new_bid = await task.new_bid_coro
        except Exception:
            # Логические ошибки должен обработать верхний TaskGroup
            raise
        if new_bid is None:
            self._logger.debug("skip: new_bid is None", extra={"adv_id": task.adv_id, "nmid": task.nmid})
            return None
        return BidUpdateResult(adv_id=task.adv_id, nmid=task.nmid, new_bid=int(new_bid))

    async def _producer(self, task: UpdateBidForNmidTask) -> None:
        result = await self._process_bid_task(task)
        if result is None:
            return
        await self._queue.put(result)

    async def _consumer(self, producers_done: asyncio.Event) -> None:
        batch: List[BidUpdateResult] = []
        try:
            while True:
                # gather with 1s timeout
                try:
                    item = await asyncio.wait_for(self._queue.get(), timeout=1.0)
                    batch.append(item)
                    self._queue.task_done()
                except asyncio.TimeoutError:
                    if batch:
                        await self._send_batch(batch)
                        batch = []
                # flush on full
                if len(batch) >= self._max_batch_size:
                    await self._send_batch(batch)
                    batch = []
                # finish when producer done and queue empty
                if producers_done.is_set() and self._queue.empty():
                    if batch:
                        await self._send_batch(batch)
                    break
        except asyncio.CancelledError:
            # Корректно выходим при отмене TaskGroup
            return

    async def _send_batch(self, batch: List[BidUpdateResult]) -> None:
        # group by adv_id
        grouped: Dict[int, List[Dict[str, int]]] = {}
        for r in batch:
            if r.new_bid is None:
                continue
            grouped.setdefault(r.adv_id, []).append({"nm": int(r.nmid), "cpm": int(r.new_bid)})
        # send per adv in chunks up to max_batch_size
        for adv_id, nm_bids in grouped.items():
            for i in range(0, len(nm_bids), self._max_batch_size):
                chunk = nm_bids[i: i + self._max_batch_size]
                await self._cpm_updater.update_bids(self._shop_id, adv_id=adv_id, nm_bids=chunk)

    async def process_updates(self, update_batch: UpdateBidsSearchAdvInShopBatch) -> None:
        if not getattr(update_batch, "tasks", []):
            return
        producers_done = asyncio.Event()
        consumer_task = asyncio.create_task(self._consumer(producers_done))
        async with asyncio.TaskGroup() as tg:
            for t in update_batch.tasks:
                tg.create_task(self._producer(t))
        producers_done.set()
        await consumer_task
