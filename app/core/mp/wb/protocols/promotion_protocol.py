"""Протоколы (interfaces) для адаптеров WB Promotion API."""

from typing import Protocol, List, Dict, Any, runtime_checkable

from .base_wb_protocol import BaseWBAdapterProtocol


@runtime_checkable
class PromotionAdapterProtocol(BaseWBAdapterProtocol, Protocol):
    """Базовый протокол для адаптеров Promotion API.

    Определяет минимально необходимые методы, которые используеются
    в логике обновления ставок.
    """

    async def update_bids(
        self, advert_id: int, bids: List[Dict[str, int]]
    ) -> Any:  # pragma: no cover
        """Обновить ставки для конкретной рекламной кампании (advert_id).

        bids: список словарей с ключами, например: {"nmid": int, "new_bid": int}
        """

    async def get_min_bids(self, advert_id: int) -> Dict[str, Any]:  # pragma: no cover
        """Получить минимальные ставки/ограничения для advert_id."""
