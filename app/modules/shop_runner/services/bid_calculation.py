from dataclasses import dataclass
from typing import Optional, List, Dict

import logging

logger = logging.getLogger(__name__)


@dataclass
class UpdateBidsInSearchAdvDTO:
    """DTO для обновления ставок в поисковой рекламе"""

    adv_id: int
    nmids: List[int]
    shop_id: int
    current_bids: Dict[int, int]  # nmid -> current_bid
    min_bids: Dict[int, int]  # nmid -> min_bid
    max_bids: Dict[int, int]  # nmid -> max_bid


@dataclass
class BidUpdateTask:
    """Задача на обновление ставки для одного товара"""

    adv_id: int
    nmid: int
    new_bid: Optional[int] = None
    error: Optional[str] = None


class BidCalculationService:
    """Сервис для расчета новых ставок"""

    def __init__(self):
        self.logger = logging.getLogger(__name__)

    async def calculate_bid(
        self,
        nmid: int,
        current_bid: int,
        min_bid: int,
        max_bid: int,
    ) -> Optional[int]:
        """
        Рассчитывает новую ставку для товара.
        Пока используем простую логику - увеличиваем текущую ставку на 10%.
        """
        try:
            # Временная простая логика для прототипа
            new_bid = int(current_bid * 1.1)

            # Проверяем ограничения
            if new_bid < min_bid:
                new_bid = min_bid
            elif new_bid > max_bid:
                new_bid = max_bid

            # Не обновляем если ставка не изменилась
            if new_bid == current_bid:
                return None

            return new_bid

        except Exception as e:
            self.logger.error(f"Ошибка расчета ставки для nmid {nmid}: {e}")
            return None

    async def prepare_tasks(self, dto: UpdateBidsInSearchAdvDTO) -> List[BidUpdateTask]:
        """
        Подготавливает список задач на обновление ставок.
        """
        tasks = []

        for nmid in dto.nmids:
            try:
                current_bid = dto.current_bids.get(nmid)
                min_bid = dto.min_bids.get(nmid)
                max_bid = dto.max_bids.get(nmid)

                if not all([current_bid, min_bid, max_bid]):
                    self.logger.warning(f"Пропущен nmid {nmid}: нет необходимых данных")
                    continue

                new_bid = await self.calculate_bid(
                    nmid=nmid, current_bid=current_bid, min_bid=min_bid, max_bid=max_bid
                )

                tasks.append(
                    BidUpdateTask(adv_id=dto.adv_id, nmid=nmid, new_bid=new_bid)
                )

            except Exception as e:
                self.logger.error(f"Ошибка подготовки задачи для nmid {nmid}: {e}")
                tasks.append(BidUpdateTask(adv_id=dto.adv_id, nmid=nmid, error=str(e)))

        return tasks
