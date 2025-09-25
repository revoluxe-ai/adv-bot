import asyncio
import logging
from collections import defaultdict
from typing import Dict, List

from app.modules.shop_runner.service_manager.services.update_cpm.new_cpm_bid_manager import NewCpmBidManager
from app.shared.application.commands.search_adv_bid_update.send_to_queue_for_update_nmid_bid_command import (
    SendToQueueForUpdateNmidBidCommand,
)
from app.shared.application.commands.search_adv_bid_update.update_bid_command import BidUpdateForNmidCommand
from .wb_api_managers import WBApiCpmUpdater

logger = logging.getLogger(__name__)


class UpdateBidOrchestrator:
    MAX_ADV_IDS_PER_BATCH: int = 50
    QUEUE_GET_TIMEOUT_SEC: float = 1.0
    BATCH_IDLE_SLEEP_SEC: float = 0.05

    def __init__(
            self,
            queue: asyncio.Queue[BidUpdateForNmidCommand],
            stop_event: asyncio.Event,
            shop_id: str,
            wb_api_cpm_updater: WBApiCpmUpdater,
            max_adv_ids_per_batch: int | None = None,
    ) -> None:
        self._queue: asyncio.Queue[BidUpdateForNmidCommand] = queue
        self._stop_event: asyncio.Event = stop_event
        self._shop_id: str = shop_id
        if max_adv_ids_per_batch is not None:
            self.MAX_ADV_IDS_PER_BATCH = max_adv_ids_per_batch

        self._new_cpm_manager: NewCpmBidManager = NewCpmBidManager()
        self._update_batch: Dict[int, List[BidUpdateForNmidCommand]] = defaultdict(list)
        self._wb_api_cpm_updater: WBApiCpmUpdater = wb_api_cpm_updater
        self._batch_lock: asyncio.Lock = asyncio.Lock()

    async def send_update_command_to_queue(self, command: SendToQueueForUpdateNmidBidCommand) -> None:
        new_bid: int = await self._new_cpm_manager.get_new_cpm_bid(command)
        bid_update_for_nmid_command = BidUpdateForNmidCommand(
            adv_id=command.adv_id,
            nmid=command.nmid,
            new_bid=new_bid,
        )
        await self._queue.put(bid_update_for_nmid_command)

    async def update_batch(self) -> None:
        """
        Читает команды из очереди и группирует их по adv_id в внутренний батч.
        Ack (task_done) выполняется только в update_bids_for_batch().
        """
        while not self._stop_event.is_set() or not self._queue.empty():
            try:
                command: BidUpdateForNmidCommand = await asyncio.wait_for(
                    self._queue.get(), timeout=self.QUEUE_GET_TIMEOUT_SEC
                )
            except asyncio.TimeoutError:
                continue

            async with self._batch_lock:
                self._update_batch[command.adv_id].append(command)

    async def update_bids_for_batch(self) -> None:
        """
        Берёт снимок накопленного батча и отправляет обновления по каждому adv_id.
        - На успех и на ошибку: выполняется ack (task_done) на каждую команду снимка.
        - Локального requeue/ретраев нет.
        """
        while self._update_batch or not self._stop_event.is_set():
            snapshot: Dict[int, List[BidUpdateForNmidCommand]] = {}

            async with self._batch_lock:
                if not self._update_batch:
                    await asyncio.sleep(self.BATCH_IDLE_SLEEP_SEC)
                    continue

                adv_ids_to_process: List[int] = list(self._update_batch.keys())[: self.MAX_ADV_IDS_PER_BATCH]
                for adv_id in adv_ids_to_process:
                    snapshot[adv_id] = self._update_batch.pop(adv_id)

            if not snapshot:
                await asyncio.sleep(0)
                continue

            try:
                # Отправляем по adv_id: WB API ожидает adv_id и список {nm, cpm}
                for adv_id, cmds in snapshot.items():
                    nm_bids: List[dict[str, int]] = [
                        {"nm": int(cmd.nmid), "cpm": int(cmd.new_bid)} for cmd in cmds
                    ]
                    await self._wb_api_cpm_updater.update_bids(self._shop_id, adv_id=adv_id, nm_bids=nm_bids)
            except asyncio.CancelledError:
                # Ack всех уже извлечённых элементов, затем пробрасываем отмену
                for cmds in snapshot.values():
                    for _ in cmds:
                        self._queue.task_done()
                raise
            except Exception as exc:
                logger.exception("Failed to update bids for batch: %s", exc)
                # Логика ретраев снаружи. Тут просто ack всех команд снимка.
                for cmds in snapshot.values():
                    for _ in cmds:
                        self._queue.task_done()
                await asyncio.sleep(self.BATCH_IDLE_SLEEP_SEC)
                continue

            # Успех — ack всех команд снимка
            for cmds in snapshot.values():
                for _ in cmds:
                    self._queue.task_done()

            await asyncio.sleep(0)
