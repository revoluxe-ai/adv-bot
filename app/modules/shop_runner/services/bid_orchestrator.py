import asyncio
import logging
from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import List, Dict, Optional

from app.shared.application.dto.update_bids_in_advs.update_bids_search_adv_ids_batch import (
    UpdateBidsSearchAdvInShopBatch,
    UpdateBidForNmidCommand,
)

logger = logging.getLogger(__name__)


@dataclass
class ProcessingStats:
    """Статистика обработки обновлений ставок"""

    total_processed: int = 0
    successful_updates: int = 0
    skipped_updates: int = 0
    api_errors: int = 0
    calculation_errors: int = 0
    batches_sent: int = 0


@dataclass
class BidUpdateResult:
    """Результат расчета ставки для отправки в очередь"""

    adv_id: int
    nmid: int
    new_bid: Optional[int] = None
    error: Optional[str] = None


class BidUpdateOrchestrator:
    """Оркестратор обновления ставок с Producer-Consumer логикой"""

    def __init__(
            self,
            api_adapter,
            max_batch_size: int = 50,
            queue_size: int = 200,
    ):
        self.api_adapter = api_adapter
        self.max_batch_size = max_batch_size
        self.queue = asyncio.Queue(maxsize=queue_size)
        self.stats = ProcessingStats()
        self.logger = logging.getLogger(__name__)

    async def _process_bid_task(self, task: UpdateBidForNmidCommand) -> BidUpdateResult:
        """Обрабатывает одну задачу на обновление ставки"""
        try:
            new_bid = await task.new_bid_coro
            return BidUpdateResult(adv_id=task.adv_id, nmid=task.nmid, new_bid=new_bid)
        except Exception as e:
            self.logger.error(f"Ошибка расчета ставки для nmid {task.nmid}: {e}")
            return BidUpdateResult(adv_id=task.adv_id, nmid=task.nmid, error=str(e))

    async def _producer(self, update_batch: UpdateBidsSearchAdvInShopBatch) -> None:
        """Producer: параллельно вычисляет ставки и отправляет в очередь"""
        try:
            async with asyncio.TaskGroup() as tg:
                # Создаем задачи для параллельного выполнения
                bid_tasks = [
                    tg.create_task(self._process_bid_task(task))
                    for task in update_batch.tasks
                ]

            # Обрабатываем результаты
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
        """Consumer: обрабатывает задачи из очереди батчами"""
        batch: List[BidUpdateResult] = []
        last_process_time = datetime.now()

        while True:
            try:
                # Получаем задачу или ждем timeout
                try:
                    result = await asyncio.wait_for(self.queue.get(), timeout=1.0)
                    batch.append(result)
                    self.queue.task_done()
                except asyncio.TimeoutError:
                    if not batch:  # Если батч пустой, продолжаем ждать
                        continue

                # Проверяем условия для отправки батча
                should_process = len(
                    batch
                ) >= self.max_batch_size or datetime.now() - last_process_time >= timedelta(
                    seconds=1
                )

                if should_process:
                    # Группируем по adv_id для API
                    grouped_batch: Dict[int, List[Dict[str, any]]] = {}
                    for result in batch:
                        if result.adv_id not in grouped_batch:
                            grouped_batch[result.adv_id] = []
                        grouped_batch[result.adv_id].append(
                            {"nmid": result.nmid, "new_bid": result.new_bid}
                        )

                    # Отправляем батч в API
                    for adv_id, bids in grouped_batch.items():
                        try:
                            success = await self.api_adapter.update_bids(
                                advert_id=adv_id, bids=bids
                            )
                            if success:
                                self.stats.successful_updates += len(bids)
                            else:
                                self.stats.api_errors += len(bids)
                        except Exception as e:
                            self.logger.error(f"Ошибка API для adv_id {adv_id}: {e}")
                            self.stats.api_errors += len(bids)

                    self.stats.batches_sent += 1
                    batch = []  # Очищаем батч
                    last_process_time = datetime.now()

            except asyncio.CancelledError:
                break
            except Exception as e:
                self.logger.error(f"Ошибка в consumer: {e}")
                if batch:
                    self.stats.api_errors += len(batch)
                batch = []

    async def process_updates(
            self, update_batch: UpdateBidsSearchAdvInShopBatch
    ) -> ProcessingStats:
        """Запускает процесс обновления ставок"""
        try:
            async with asyncio.TaskGroup() as tg:
                # Запускаем producer и consumer параллельно
                producer_task = tg.create_task(self._producer(update_batch))
                consumer_task = tg.create_task(self._consumer())

                # TaskGroup дождется завершения producer
                # Когда producer завершится, очередь будет пуста и consumer завершится

            return self.stats

        except Exception as e:
            self.logger.error(f"Ошибка процесса обновления: {e}")
            raise
