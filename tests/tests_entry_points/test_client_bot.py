import asyncio
from unittest.mock import AsyncMock, MagicMock

import pytest
from aiogram import Bot, Dispatcher

# Предполагаем, что в client_bot_run.py есть функция setup_bot, которая настраивает бота
from client_bot_run import setup_bot


@pytest.mark.asyncio
async def test_client_bot_setup_registers_all_handlers():
    """
    Тест проверяет, что функция setup_bot регистрирует все необходимые обработчики
    """
    # Создаем мок для бота и диспетчера
    bot_mock = MagicMock(spec=Bot)
    dp_mock = MagicMock(spec=Dispatcher)

    # Мокируем регистрацию обработчиков в диспетчере
    dp_mock.message.register = MagicMock()
    dp_mock.callback_query.register = MagicMock()
    dp_mock.inline_query.register = MagicMock()

    # Вызываем тестируемую функцию
    setup_bot(bot_mock, dp_mock)

    # Проверяем, что регистрация обработчиков была вызвана ожидаемое количество раз
    # Замените эти числа на реальные, соответствующие количеству регистрируемых обработчиков
    assert dp_mock.message.register.call_count >= 1, (
        "Недостаточно обработчиков сообщений зарегистрировано"
    )
    assert dp_mock.callback_query.register.call_count >= 1, (
        "Недостаточно обработчиков callback-запросов зарегистрировано"
    )


@pytest.mark.asyncio
async def test_client_bot_middleware_setup():
    """
    Тест проверяет, что все middleware правильно настроены для бота
    """
    # Создаем мок для бота и диспетчера
    bot_mock = MagicMock(spec=Bot)
    dp_mock = MagicMock(spec=Dispatcher)

    # Мокируем методы для работы с middleware
    dp_mock.update.middleware = MagicMock()
    dp_mock.message.middleware = MagicMock()

    # Вызываем тестируемую функцию
    setup_bot(bot_mock, dp_mock)

    # Проверяем, что middleware были добавлены
    assert dp_mock.update.middleware.register.call_count >= 1, (
        "Недостаточно middleware зарегистрировано для update"
    )
    assert dp_mock.message.middleware.register.call_count >= 1, (
        "Недостаточно middleware зарегистрировано для message"
    )


@pytest.mark.asyncio
async def test_client_bot_startup_handlers():
    """
    Тест проверяет, что обработчики запуска бота корректно настроены
    """
    # Создаем мок для бота и диспетчера
    bot_mock = MagicMock(spec=Bot)
    dp_mock = MagicMock(spec=Dispatcher)

    # Мокируем методы для работы с обработчиками событий
    dp_mock.startup = AsyncMock()
    dp_mock.shutdown = AsyncMock()

    # Имитируем регистрацию обработчиков
    startup_handlers = []
    shutdown_handlers = []

    # Мокируем метод регистрации
    def register_startup_mock(handler):
        startup_handlers.append(handler)
        return handler

    def register_shutdown_mock(handler):
        shutdown_handlers.append(handler)
        return handler

    dp_mock.startup.register = register_startup_mock
    dp_mock.shutdown.register = register_shutdown_mock

    # Вызываем тестируемую функцию
    setup_bot(bot_mock, dp_mock)

    # Проверяем, что обработчики были зарегистрированы
    assert len(startup_handlers) > 0, "Не зарегистрированы обработчики запуска"
    assert len(shutdown_handlers) > 0, "Не зарегистрированы обработчики остановки"

    # Проверяем работу обработчиков запуска
    for handler in startup_handlers:
        try:
            if asyncio.iscoroutinefunction(handler):
                await handler()
            else:
                handler()
        except Exception as e:
            pytest.fail(f"Обработчик запуска вызвал исключение: {e}")

    # Проверяем работу обработчиков остановки
    for handler in shutdown_handlers:
        try:
            if asyncio.iscoroutinefunction(handler):
                await handler()
            else:
                handler()
        except Exception as e:
            pytest.fail(f"Обработчик остановки вызвал исключение: {e}")
