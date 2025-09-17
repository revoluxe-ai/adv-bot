import asyncio
from unittest.mock import AsyncMock, patch

import pytest

from app.arq_workers.workers import WorkerSettings


@pytest.mark.asyncio
async def test_worker_settings_startup_calls_all_functions():
    """
    Тест проверяет, что метод startup класса WorkerSettings вызывает все необходимые функции
    """
    # Создаем экземпляр WorkerSettings
    worker_settings = WorkerSettings()

    # Мокируем все методы, которые должны вызываться из startup
    # Замените эти методы на реальные функции, которые вызываются в startup
    worker_settings.startup_method1 = AsyncMock()
    worker_settings.startup_method2 = AsyncMock()
    worker_settings.startup_method3 = AsyncMock()

    # Вызываем тестируемый метод
    await worker_settings.startup()

    # Проверяем, что все ожидаемые методы были вызваны
    worker_settings.startup_method1.assert_called_once()
    worker_settings.startup_method2.assert_called_once()
    worker_settings.startup_method3.assert_called_once()


@pytest.mark.asyncio
async def test_worker_settings_shutdown_calls_all_functions():
    """
    Тест проверяет, что метод shutdown класса WorkerSettings вызывает все необходимые функции
    """
    # Создаем экземпляр WorkerSettings
    worker_settings = WorkerSettings()

    # Мокируем все методы, которые должны вызываться из shutdown
    # Замените эти методы на реальные функции, которые вызываются в shutdown
    worker_settings.shutdown_method1 = AsyncMock()
    worker_settings.shutdown_method2 = AsyncMock()

    # Вызываем тестируемый метод
    await worker_settings.shutdown()

    # Проверяем, что все ожидаемые методы были вызваны
    worker_settings.shutdown_method1.assert_called_once()
    worker_settings.shutdown_method2.assert_called_once()


@pytest.mark.asyncio
async def test_worker_functions_without_errors():
    """
    Тест проверяет, что все функции воркера запускаются без ошибок
    """
    # Создаем экземпляр WorkerSettings
    worker_settings = WorkerSettings()

    # Получаем список всех функций воркера
    worker_functions = worker_settings.functions()

    # Проверяем каждую функцию
    for func_name, func in worker_functions.items():
        # Мокируем функцию для тестирования
        async def mock_func(*args, **kwargs):
            # Имитируем работу функции
            await asyncio.sleep(0.1)
            return True

        with patch.object(worker_settings, func_name, side_effect=mock_func):
            # Создаем контекст для запуска функции
            ctx = {"job_id": "test_job", "job_try": 1}

            # Вызываем функцию и проверяем, что она работает без ошибок
            try:
                result = await func(ctx, "test_arg")
                assert result is True, (
                    f"Функция {func_name} вернула неожиданный результат"
                )
            except Exception as e:
                pytest.fail(f"Функция {func_name} вызвала исключение: {e}")
