"""Базовый класс для мета-миксинов адаптеров."""

from typing import TYPE_CHECKING, Any, Dict, Optional

if TYPE_CHECKING:
    from ...base_wb_api import BaseWBApi


class BaseAdapterMixin:
    """
    Базовый класс для всех мета-миксинов адаптеров.
    Содержит общую логику получения и кеширования адаптеров.
    """

    def _get_adapter(
        self: "BaseWBApi", domain: str, version: Optional[str] = None
    ) -> Any:
        """
        Получить адаптер для указанного домена.

        Args:
            domain: Домен API ("promotion", "media", "statistics")
            version: Версия API (если не указана, используется версия по умолчанию для домена)

        Returns:
            Адаптер для работы с API
        """
        # Получаем версию для конкретного домена
        domain_version = version or self._get_domain_version(domain)
        cache_key = f"{domain}_{domain_version}"

        # Проверяем кеш
        if cache_key in self._adapters_cache:
            return self._adapters_cache[cache_key]

        # Создаем новый адаптер
        adapter = self._create_domain_adapter(domain, domain_version)

        # Кешируем
        self._adapters_cache[cache_key] = adapter

        return adapter

    def _get_domain_version(self: "BaseWBApi", domain: str) -> str:
        """
        Получить версию API для конкретного домена.
        Каждый домен может иметь свою версию независимо от других.

        Args:
            domain: Домен API

        Returns:
            Версия API для этого домена
        """
        # Проверяем есть ли специфичная версия для домена
        domain_versions = getattr(self, "_domain_versions", {})
        return domain_versions.get(domain, self.api_version)

    def _create_domain_adapter(self: "BaseWBApi", domain: str, version: str) -> Any:
        """
        Создать адаптер для указанного домена и версии.
        Должен быть переопределен в конкретных мета-миксинах.

        Args:
            domain: Домен API
            version: Версия API

        Returns:
            Экземпляр адаптера
        """
        raise NotImplementedError(
            f"Domain adapter creation for '{domain}' not implemented in {self.__class__.__name__}"
        )

    def set_domain_version(self: "BaseWBApi", domain: str, version: str) -> None:
        """
        Установить версию API для конкретного домена.

        Args:
            domain: Домен API
            version: Версия API
        """
        if not hasattr(self, "_domain_versions"):
            self._domain_versions: Dict[str, str] = {}

        old_version = self._domain_versions.get(domain)
        if old_version != version:
            self._domain_versions[domain] = version
            # Очищаем кеш только для этого домена
            self._clear_domain_cache(domain)

    def get_domain_version(self: "BaseWBApi", domain: str) -> str:
        """Получить текущую версию API для домена."""
        return self._get_domain_version(domain)

    def _clear_domain_cache(self: "BaseWBApi", domain: str) -> None:
        """Очистить кеш адаптеров для конкретного домена."""
        keys_to_remove = [
            key for key in self._adapters_cache.keys() if key.startswith(f"{domain}_")
        ]
        for key in keys_to_remove:
            del self._adapters_cache[key]
