"""Пример инициализации и использования WBApiContainer.

Демонстрирует настройку DI контейнера и override конфигурации.
"""

import asyncio
from dependency_injector import containers, providers
from dependency_injector.wiring import Provide, inject

from .containers import WBApiContainer


async def example_container_usage():
    """Пример использования контейнера с DI."""
    
    # Создаем экземпляр контейнера
    container = WBApiContainer()
    
    # Пример 1: Override base_url для promotion API
    container.config.promotion.base_url.override("https://advert-api.wildberries.ru/")
    
    # Пример 2: Можно переопределить и другие параметры
    container.config.promotion.timeout.override(45.0)  # Увеличиваем таймаут
    
    # Получаем HTTP клиент (Singleton)
    http_client = container.http_client()
    print(f"HTTP Client base URL: {http_client.base_url}")
    print(f"HTTP Client timeout: {http_client.timeout}")
    
    # Получаем другие сервисы
    rate_limit_storage = container.rate_limit_storage()
    token_manager_factory = container.token_manager_factory()
    wb_api_adapter_factory = container.wb_api_adapter_factory()
    
    print(f"Rate Limit Storage: {type(rate_limit_storage).__name__}")
    print(f"Token Manager Factory: {type(token_manager_factory).__name__}")
    print(f"WB API Adapter Factory: {type(wb_api_adapter_factory).__name__}")
    
    # Закрываем HTTP клиент после использования
    await http_client.aclose()


def example_multiple_overrides():
    """Пример множественных переопределений конфигурации."""
    
    container = WBApiContainer()
    
    # Настройка для разных доменов API
    container.config.promotion.base_url.override("https://advert-api.wildberries.ru/")
    container.config.media.base_url.override("https://media-api.wildberries.ru/")
    container.config.statistics.base_url.override("https://statistics-api.wildberries.ru/")
    
    # Настройка таймаутов
    container.config.promotion.timeout.override(30.0)
    container.config.media.timeout.override(60.0)  # Медиа файлы требуют больше времени
    container.config.statistics.timeout.override(15.0)  # Статистика быстрая
    
    print("✅ Конфигурация успешно применена:")
    print(f"  Promotion API: {container.config.promotion.base_url()}")
    print(f"  Media API: {container.config.media.base_url()}")
    print(f"  Statistics API: {container.config.statistics.base_url()}")


def example_container_wiring():
    """Пример подключения контейнера для автоматической инжекции зависимостей."""
    
    # Создаем контейнер
    container = WBApiContainer()
    
    # Настраиваем базовые URL
    container.config.promotion.base_url.override("https://advert-api.wildberries.ru/")
    
    # Настраиваем wiring для автоматической инжекции
    container.wire(modules=[__name__])
    
    print("✅ Контейнер настроен для автоматической инжекции зависимостей")
    
    return container


# Пример функции с автоматической инжекцией зависимостей
@inject
async def example_injected_function(
    http_client=Provide[WBApiContainer.http_client],
    token_manager=Provide[WBApiContainer.token_manager_factory]
):
    """Пример функции с автоматически инжектируемыми зависимостями."""
    
    print(f"Injected HTTP Client: {type(http_client).__name__}")
    print(f"Injected Token Manager: {type(token_manager).__name__}")
    
    # Используем инжектированные зависимости
    print(f"HTTP Client URL: {http_client.base_url}")
    
    await http_client.aclose()


if __name__ == "__main__":
    print("🚀 Пример инициализации WBApiContainer")
    print("=" * 50)
    
    # Запускаем основной пример
    asyncio.run(example_container_usage())
    
    print("\n" + "=" * 50)
    print("🔧 Пример множественных переопределений")
    print("=" * 50)
    
    example_multiple_overrides()
    
    print("\n" + "=" * 50)
    print("💉 Пример настройки автоматической инжекции")
    print("=" * 50)
    
    container = example_container_wiring()
    
    # Запускаем функцию с инжекцией (требует настроенный wiring)
    # asyncio.run(example_injected_function())