"""
Сервис для расчета новых ставок CPM.

Содержит логику расчета оптимальных ставок на основе текущих позиций
и целевых настроек.
"""

import logging
from dataclasses import dataclass
from typing import Optional

logger = logging.getLogger(__name__)


@dataclass
class BidCalculationParams:
    """Параметры для расчета ставки."""

    current_bid: int
    min_bid: int
    max_bid: int
    current_position: int
    target_position: int
    bidder_step: int = 2

    def __post_init__(self):
        """Валидация параметров."""
        if self.min_bid > self.max_bid:
            raise ValueError(f"min_bid ({self.min_bid}) > max_bid ({self.max_bid})")
        if self.current_bid < 0:
            raise ValueError(f"current_bid must be positive, got {self.current_bid}")
        if self.target_position < 1:
            raise ValueError(
                f"target_position must be >= 1, got {self.target_position}"
            )


class BidCalculator:
    """Калькулятор для расчета оптимальных ставок."""

    DEFAULT_BIDDER_STEP = 2

    def calculate_new_bid(self, params: BidCalculationParams) -> Optional[int]:
        """
        Рассчитывает новую ставку на основе текущей позиции.

        Args:
            params: Параметры для расчета

        Returns:
            Новая ставка или None, если изменение не требуется
        """
        # Если уже на целевой позиции или выше - снижаем ставку
        if (
            params.current_position <= params.target_position
            or params.current_position == 1
        ):
            new_bid = params.current_bid - params.bidder_step
            logger.debug(
                f"Position {params.current_position} <= target {params.target_position}, "
                f"decreasing bid: {params.current_bid} -> {new_bid}"
            )
        else:
            # Если ниже целевой позиции - повышаем ставку
            new_bid = params.current_bid + params.bidder_step
            logger.debug(
                f"Position {params.current_position} > target {params.target_position}, "
                f"increasing bid: {params.current_bid} -> {new_bid}"
            )

        # Ограничиваем ставку в допустимых пределах
        new_bid = max(params.min_bid, min(new_bid, params.max_bid))

        # Если ставка не изменилась - возвращаем None
        if new_bid == params.current_bid:
            logger.debug(f"Bid unchanged at {params.current_bid}")
            return None

        return new_bid

    def should_update_bid(
        self, current_bid: int, new_bid: int, min_change_percent: float = 0.05
    ) -> bool:
        """
        Проверяет, стоит ли обновлять ставку.

        Args:
            current_bid: Текущая ставка
            new_bid: Новая ставка
            min_change_percent: Минимальный процент изменения

        Returns:
            True, если ставку стоит обновить
        """
        if current_bid == 0:
            return True

        change_percent = abs(new_bid - current_bid) / current_bid
        return change_percent >= min_change_percent
