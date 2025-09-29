"""Мета-миксин для подключения Media клиента."""

from typing import TYPE_CHECKING, Any

from .base_adapter_mixin import BaseAdapterMixin

if TYPE_CHECKING:
    from ...base_wb_api import BaseWBApi


class MediaAdapterMixin(BaseAdapterMixin):
    """Мета-миксин для подключения Media API клиента."""

    def _create_domain_adapter(self: "BaseWBApi", domain: str, version: str):
        """Создание адаптеров с поддержкой Media API."""
        if domain == "media":
            return self._create_media_adapter(version)

        # Делегируем другие домены родительскому классу
        return super()._create_domain_adapter(domain, version)

    def _create_media_adapter(self: "BaseWBApi", version: str) -> Any:
        """Создать адаптер для Media API."""
        # TODO: Реализовать когда появится Media API
        raise NotImplementedError("Media API adapter not implemented yet")

    @property
    def media_adapter(self: "BaseWBApi") -> Any:
        """Получить адаптер для Media API."""
        return self._get_domain_adapter("media")

    def set_media_version(self: "BaseWBApi", version: str) -> None:
        """Установить версию Media API."""
        self.set_domain_version("media", version)
