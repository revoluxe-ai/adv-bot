import asyncio
import logging
from datetime import datetime, timedelta
from typing import List, Dict, Any, Protocol

from app.shared.dto.bidder import (
    ProcessingStats,
    BidUpdateResult,
    UpdateBidForNmidTask,
    UpdateBidsSearchAdvInShopBatch,
)


# --- API Adapter Protocol ---
class BidApiAdapter(Protocol):
    async def update_bids(self, advert_id: int, bids: List[Dict[str, Any]]) -> bool:
        ...


# --- Orchestrator ---
class BidUpdateOrchestrator:
    """
    Оркестратор обновления ставок с Producer-Consumer логикой (bidder_v2).
    """

    def __init__(
            self,
            api_adapter: BidApiAdapter,
            max_batch_size: int = 50,
            queue_size: int = 200,
    ):
        self.api_adapter = api_adapter
        self.max_batch_size = max_batch_size
        self.queue = asyncio.Queue(maxsize=queue_size)
        self.stats = ProcessingStats()
        self.logger = logging.getLogger(__name__)

    async def _process_bid_task(self, task: UpdateBidForNmidTask) -> BidUpdateResult:
        try:
            new_bid = await task.new_bid_coro
            return BidUpdateResult(adv_id=task.adv_id, nmid=task.nmid, new_bid=new_bid)
        except Exception as e:
            self.logger.error(f"Ошибка расчета ставки для nmid {task.nmid}: {e}")
            return BidUpdateResult(adv_id=task.adv_id, nmid=task.nmid, error=str(e))

    async def _producer(self, update_batch: UpdateBidsSearchAdvInShopBatch) -> None:
        try:
            async with asyncio.TaskGroup() as tg:
                bid_tasks = [tg.create_task(self._process_bid_task(task)) for task in update_batch.tasks]
            for task in bid_tasks:
                result = task.result()
                if result.error:
                    self.stats.calculation_errors += 1
                    continue
                if result.new_bid is None:
                    self.stats.skipped_updates += 1
                    continue
                await self.queue.put(result)
                self.stats.total_processed += 1
        except Exception as e:
            self.logger.error(f"Ошибка в producer: {e}")
            raise

    async def _consumer(self) -> None:
        batch: List[BidUpdateResult] = []
        last_process_time = datetime.now()
        while True:
            try:
                try:
                    result = await asyncio.wait_for(self.queue.get(), timeout=1.0)
                    batch.append(result)
                    self.queue.task_done()
                except asyncio.TimeoutError:
                    if not batch:
                        continue
                should_process = len(batch) >= self.max_batch_size or datetime.now() - last_process_time >= timedelta(
                    seconds=1)
                if should_process:
                    grouped_batch: Dict[int, List[Dict[str, Any]]] = {}
                    for result in batch:
                        grouped_batch.setdefault(result.adv_id, []).append(
                            {"nmid": result.nmid, "new_bid": result.new_bid})
                    for adv_id, bids in grouped_batch.items():
                        try:
                            success = await self.api_adapter.update_bids(advert_id=adv_id, bids=bids)
                            if success:
                                self.stats.successful_updates += len(bids)
                            else:
                                self.stats.api_errors += len(bids)
                        except Exception as e:
                            self.logger.error(f"Ошибка API для adv_id {adv_id}: {e}")
                            self.stats.api_errors += len(bids)
                    self.stats.batches_sent += 1
                    batch = []
                    last_process_time = datetime.now()
            except asyncio.CancelledError:
                break
            except Exception as e:
                self.logger.error(f"Ошибка в consumer: {e}")
                if batch:
                    self.stats.api_errors += len(batch)
                batch = []

    async def process_updates(self, update_batch: UpdateBidsSearchAdvInShopBatch) -> ProcessingStats:
        try:
            async with asyncio.TaskGroup() as tg:
                producer_task = tg.create_task(self._producer(update_batch))
                consumer_task = tg.create_task(self._consumer())
            return self.stats
        except Exception as e:
            self.logger.error(f"Ошибка процесса обновления: {e}")
            raise
