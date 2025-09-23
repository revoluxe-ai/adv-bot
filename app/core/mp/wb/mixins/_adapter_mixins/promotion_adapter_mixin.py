"""Мета-миксин для подключения Promotion клиента."""

from typing import TYPE_CHECKING

from .base_adapter_mixin import BaseAdapterMixin

if TYPE_CHECKING:
    from ...base_wb_api import BaseWBApi


class PromotionAdapterMixin(BaseAdapterMixin):
    """Мета-миксин для подключения Promotion API клиента."""

    def _create_domain_adapter(self: "BaseWBApi", domain: str, version: str):
        """Создание адаптеров с поддержкой Promotion API."""
        if domain == "promotion":
            return self._create_promotion_adapter(version)

        # Делегируем другие домены родительскому классу
        return super()._create_domain_adapter(domain, version)

    def _create_promotion_adapter(
        self: "BaseWBApi", version: str
    ) -> "PromotionAdapterProtocol":
        """Создать адаптер для Promotion API."""
        from ...api_client.clients.promotion.adapters.factory import (
            build_promotion_adapter,
        )

        return build_promotion_adapter(
            version=version, wb_access=self.access, http_client=self.http_client
        )

    @property
    def promotion_adapter(self: "BaseWBApi") -> "PromotionAdapterProtocol":
        """Получить адаптер для Promotion API."""
        return self._get_domain_adapter("promotion")

    def set_promotion_version(self: "BaseWBApi", version: str) -> None:
        """Установить версию Promotion API."""
        self.set_domain_version("promotion", version)
