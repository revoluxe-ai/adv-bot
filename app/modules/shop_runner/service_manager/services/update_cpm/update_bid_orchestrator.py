import asyncio
import logging
from collections import defaultdict
from typing import Dict, List, Optional

from app.modules.shop_runner.service_manager.services.update_cpm.new_cpm_bid_manager import NewCpmBidManager
from app.shared.application.commands.search_adv_bid_update.send_to_queue_for_update_nmid_bid_command import (
    SendToQueueForUpdateNmidBidCommand,
)
from app.shared.application.commands.search_adv_bid_update.update_bid_command import BidUpdateForNmidCommand
from .wb_api_cpm_updater import WBApiCpmUpdater

logger = logging.getLogger(__name__)


class UpdateBatch:
    """Класс для управления батчами обновлений ставок."""

    def __init__(self, commands: Optional[Dict[int, List[BidUpdateForNmidCommand]]] = None):
        self.commands = commands or {}

    def add_command(self, command: BidUpdateForNmidCommand) -> None:
        """Добавляет команду в батч."""
        self.commands.setdefault(command.adv_id, []).append(command)

    def get_nmids_bids_for_adv(self, adv_id: int) -> List[dict[str, int]]:
        """Возвращает nmids_bids для указанного adv_id."""
        return [
            {"nmid": int(cmd.nmid), "bid": int(cmd.new_bid)}
            for cmd in self.commands.get(adv_id, [])
        ]

    def is_empty(self) -> bool:
        """Проверяет, пуст ли батч."""
        return not self.commands

    def get_adv_ids(self) -> List[int]:
        """Возвращает список всех adv_id в батче."""
        return list(self.commands.keys())

    def pop_adv_commands(self, adv_ids: List[int]) -> Dict[int, List[BidUpdateForNmidCommand]]:
        """Извлекает команды для указанных adv_id из батча."""
        result = {}
        for adv_id in adv_ids:
            if adv_id in self.commands:
                result[adv_id] = self.commands.pop(adv_id)
        return result

    def clear(self) -> None:
        """Очищает батч."""
        self.commands.clear()


class UpdateBidOrchestrator:
    MAX_ADV_IDS_PER_BATCH: int = 50
    QUEUE_GET_TIMEOUT_SEC: float = 1.0
    BATCH_IDLE_SLEEP_SEC: float = 0.05

    def __init__(
            self,
            queue: asyncio.Queue[BidUpdateForNmidCommand],
            stop_event: asyncio.Event,
            shop_id: str,
    ) -> None:
        self._queue: asyncio.Queue[BidUpdateForNmidCommand] = queue
        self._stop_event: asyncio.Event = stop_event
        self._shop_id: str = shop_id
        self._new_cpm_manager: NewCpmBidManager = NewCpmBidManager()
        self._update_batch: UpdateBatch = UpdateBatch()
        self._wb_api_cpm_updater: WBApiCpmUpdater = WBApiCpmUpdater(self._shop_id)
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
                self._update_batch.add_command(command)

    async def update_bids_for_batch(self) -> None:
        """
        Берёт снимок накопленного батча и отправляет обновления по каждому adv_id.
        - На успех и на ошибку: выполняется ack (task_done) на каждую команду снимка.
        - Локального requeue/ретраев нет.
        """
        while not self._stop_event.is_set():
            snapshot: Dict[int, List[BidUpdateForNmidCommand]] = {}

            async with self._batch_lock:
                if self._update_batch.is_empty():
                    await asyncio.sleep(self.BATCH_IDLE_SLEEP_SEC)
                    continue

                # Берем только первые MAX_ADV_IDS_PER_BATCH adv_id для обработки
                adv_ids_to_process = self._update_batch.get_adv_ids()[:self.MAX_ADV_IDS_PER_BATCH]
                snapshot = self._update_batch.pop_adv_commands(adv_ids_to_process)

            if not snapshot:
                await asyncio.sleep(0)
                continue

            try:
                # Отправляем обновления по adv_id
                for adv_id, cmds in snapshot.items():
                    nm_bids = self._update_batch.get_nm_bids_for_adv(adv_id)
                    await self._wb_api_cpm_updater.update_bids_for_shop(dv_id=adv_id, nm_bids=nm_bids)

                # Ack всех команд при успехе
                self._ack_commands(snapshot)

            except asyncio.CancelledError:
                # Ack всех уже извлечённых элементов, затем пробрасываем отмену
                self._ack_commands(snapshot)
                raise
            except Exception as exc:
                logger.exception("Failed to update bids for batch: %s", exc)
                # Логика ретраев снаружи. Тут просто ack всех команд снимка.
                self._ack_commands(snapshot)
                await asyncio.sleep(self.BATCH_IDLE_SLEEP_SEC)

    def _ack_commands(self, snapshot: Dict[int, List[BidUpdateForNmidCommand]]) -> None:
        """Выполняет ack для всех команд в snapshot."""
        for cmds in snapshot.values():
            for _ in cmds:
                self._queue.task_done()
