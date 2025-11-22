"""Тест для проверки инициализации DI контейнера."""

import pytest

from app.core.di.app_container import AppContainer


@pytest.mark.asyncio
async def test_di_container_init():
    """Проверяем, что DI контейнер инициализируется без ошибок."""
    container = AppContainer()
    
    try:
        await container.init_resources()
        print("✓ DI контейнер инициализирован успешно")
    except Exception as e:
        print(f"✗ Ошибка при инициализации DI контейнера: {e}")
        raise
    finally:
        await container.shutdown_resources()

