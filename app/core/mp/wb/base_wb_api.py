"""Базовый класс для WB API клиента."""

import logging
from abc import ABC
from typing import Any, Dict, Optional

import httpx

logger = logging.getLogger(__name__)


class BaseWBApi(ABC):
    """
    Базовый класс для WB API клиента.
    Управляет HTTP-сессией, доступом и адаптерами для разных версий API.
    """

    def __init__(
        self,
        wb_access: Any,
        http_client: httpx.AsyncClient,
        api_version: str = "v1",
        domain_versions: Optional[Dict[str, str]] = None,
    ):
        """
        Инициализация базового WB API клиента.

        Args:
            wb_access: Объект с доступами к WB API (токены, shop_id)
            http_client: HTTP клиент для запросов
            api_version: Версия API по умолчанию ("v1", "v2", etc.)
            domain_versions: Специфичные версии для доменов {"promotion": "v2", "media": "v1"}
        """
        self.access = wb_access
        self.http_client = http_client
        self.api_version = api_version

        # Версии для конкретных доменов (независимые от общей версии)
        self._domain_versions: Dict[str, str] = domain_versions or {}

        # Кеш для адаптеров (чтобы не создавать повторно)
        self._adapters_cache: Dict[str, Any] = {}

    @property
    def shop_id(self) -> int:
        """ID магазина из объекта доступа."""
        return self.access.shop_id

    def switch_api_version(self, new_version: str) -> None:
        """
        Переключить версию API для всех доменов.

        Args:
            new_version: Новая версия API
        """
        if new_version != self.api_version:
            self.api_version = new_version
            # Очищаем весь кеш адаптеров
            self._adapters_cache.clear()

    def _get_adapter(self, domain: str) -> Any:
        """
        Получить адаптер для указанного домена.

        Args:
            domain: Домен API ("promotion", "media", "statistics")

        Returns:
            Адаптер для работы с API
        """
        # Получаем версию для конкретного домена
        domain_version = self._domain_versions.get(domain, self.api_version)
        cache_key = f"{domain}_{domain_version}"

        # Проверяем кеш
        if cache_key in self._adapters_cache:
            return self._adapters_cache[cache_key]

        # Создаем новый адаптер
        adapter = self._create_domain_adapter(domain, domain_version)

        # Кешируем
        self._adapters_cache[cache_key] = adapter

        return adapter

    def _create_domain_adapter(self, domain: str, version: str) -> Any:
        """
        Создать адаптер для указанного домена и версии через DI.

        Args:
            domain: Домен API
            version: Версия API

        Returns:
            Экземпляр адаптера
        """
        if domain == "promotion":
            # Используем DI контейнер для создания адаптеров
            from .containers import WBApiContainer

            container = WBApiContainer()

            if version == "v1":
                return container.promotion_adapter_v1(wb_access=self.access)
            else:
                raise ValueError(f"Unsupported promotion API version: {version}")
        else:
            raise NotImplementedError(
                f"Domain adapter creation for '{domain}' not implemented"
            )

    def set_domain_version(self, domain: str, version: str) -> None:
        """
        Установить версию API для конкретного домена.

        Args:
            domain: Домен API
            version: Версия API
        """
        old_version = self._domain_versions.get(domain)
        if old_version != version:
            self._domain_versions[domain] = version
            # Очищаем кеш только для этого домена
            self._clear_domain_cache(domain)

    def _clear_domain_cache(self, domain: str) -> None:
        """Очистить кеш адаптеров для конкретного домена."""
        keys_to_remove = [
            key for key in self._adapters_cache.keys() if key.startswith(f"{domain}_")
        ]
        for key in keys_to_remove:
            del self._adapters_cache[key]

    def clear_adapters_cache(self) -> None:
        """Очистить весь кеш адаптеров."""
        self._adapters_cache.clear()
