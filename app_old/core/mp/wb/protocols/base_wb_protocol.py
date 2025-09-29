"""Базовый протокол для WB API адаптеров."""

from typing import Protocol


class BaseWBAdapterProtocol(Protocol):
    """Общий протокол для всех адаптеров WB API."""

    async def set_next_token(self, method_name: str) -> None:  # pragma: no cover
        """Переключиться на следующий токен для указанного метода."""

    @property
    def shop_id(self) -> str:  # pragma: no cover
        """ID магазина, к которому привязан адаптер."""
