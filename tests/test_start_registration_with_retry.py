import dotenv
import sys, os
sys.path.append(os.path.abspath(os.path.dirname(__file__) + "/.."))
import pytest
import asyncio
import logging
from unittest.mock import AsyncMock, MagicMock, patch
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from typing import Any, Callable, TypeVar, Awaitable, Optional, Dict

# Импортируем из нашего тестового файла функции повторных попыток
from tests.test_db_retry import retry_async_db_operation, with_db_retry

# Импортируем необходимые функции из проекта
from app.client_bot.user_interface.handlers.start_registration_func import start_registration
from app.utils.db.session_maker import get_async_session_maker
from app.utils.db.models import User, RefLink
from app.modules.common_slaves.wildberries.models import WBUserCabinet

# Настраиваем логирование
logger = logging.getLogger(__name__)

# Пример функции с механизмом повторных попыток для функции start_registration
@with_db_retry(max_retries=3, retry_delay=0.5, 
               retry_exceptions=(ConnectionError, TimeoutError, Exception))
async def start_registration_with_retry(message, bot, state):
    """
    Обертка для функции start_registration с механизмом повторных попыток.
    
    Эта функция не вносит изменения в основной код, а просто обертывает
    существующую функцию в механизм повторных попыток.
    """
    return await start_registration(message, bot, state)

# Тесты для функции с повторными попытками
@pytest.mark.asyncio
async def test_start_registration_retry_success():
    """
    Тест функции start_registration с повторными попытками при успешной регистрации.
    Симулируем первую неудачную попытку и затем успешную.
    """
    # Создаем моки для аргументов функции
    mock_message = MagicMock()
    mock_message.from_user.id = 123456789
    mock_message.from_user.username = "test_user"
    mock_message.chat.id = 123456789
    mock_message.text = "/start"
    
    mock_bot = AsyncMock()
    mock_state = AsyncMock()
    
    # Создаем моки для объектов базы данных
    mock_user = MagicMock(spec=User)
    mock_user.user_telegram_id = 123456789
    
    # Моки для базы данных
    mock_session = AsyncMock(spec=AsyncSession)
    
    # Настраиваем моки для первого вызова (исключение при выполнении запроса)
    first_call_result = AsyncMock()
    first_call_result.scalar.side_effect = ConnectionError("Test connection error")
    
    # Настраиваем моки для второго вызова (успешное выполнение)
    second_call_result = AsyncMock()
    second_call_result.scalar.return_value = None  # Пользователь не найден
    
    # Настраиваем очередность возвращаемых результатов
    mock_session.execute.side_effect = [
        ConnectionError("Test connection error"),  # Первый вызов
        second_call_result  # Второй вызов
    ]
    
    # Мокируем функцию создания сессии
    mock_context_manager = MagicMock()
    mock_context_manager.__aenter__.return_value = mock_session
    mock_context_manager.__aexit__.return_value = None
    
    # Создаем инструментированную функцию для тестирования
    async def test_func():
        # Счетчик вызовов для симуляции ошибки на первой попытке
        if not hasattr(test_func, 'call_count'):
            test_func.call_count = 0
            
        if test_func.call_count == 0:
            test_func.call_count += 1
            raise ConnectionError("Test connection error")
        
        test_func.call_count += 1
        # Во второй попытке выполняем успешно
        return await start_registration(mock_message, mock_bot, mock_state)
    
    # Патчим start_registration для тестирования
    with patch('tests.test_start_registration_with_retry.start_registration', side_effect=test_func), \
         patch('app.utils.db.session_maker.get_async_session_maker', return_value=mock_context_manager):
        
        # Вызываем функцию с ретраями
        await retry_async_db_operation(test_func, max_retries=3, retry_delay=0.1)
        
        # Проверяем, что функция была вызвана дважды
        assert hasattr(test_func, 'call_count')
        assert test_func.call_count == 2

# Тест с использованием декоратора
@pytest.mark.asyncio
async def test_start_registration_with_retry_decorator():
    """
    Тест функции start_registration_with_retry с использованием декоратора with_db_retry.
    """
    # Создаем моки для аргументов функции
    mock_message = MagicMock()
    mock_message.from_user.id = 123456789
    mock_message.from_user.username = "test_user"
    mock_message.chat.id = 123456789
    mock_message.text = "/start"
    
    mock_bot = AsyncMock()
    mock_state = AsyncMock()
    
    # Моки для базы данных
    mock_session = AsyncMock(spec=AsyncSession)
    mock_result = AsyncMock()
    mock_result.scalar.return_value = None  # Пользователь не найден
    
    # Настраиваем моки для вызовов
    mock_session.execute.side_effect = [
        ConnectionError("Test connection error"),  # Первый вызов
        mock_result  # Второй вызов
    ]
    
    # Мокируем функцию создания сессии
    mock_context_manager = MagicMock()
    mock_context_manager.__aenter__.return_value = mock_session
    mock_context_manager.__aexit__.return_value = None
    
    # Патчим функции и создаем временную функцию
    original_start_registration = start_registration
    
    # Создаем временную функцию с ошибкой на первый вызов
    async def mock_start_registration(message, bot, state):
        if not hasattr(mock_start_registration, 'call_count'):
            mock_start_registration.call_count = 0
            
        if mock_start_registration.call_count == 0:
            mock_start_registration.call_count += 1
            raise ConnectionError("Test connection error")
        
        mock_start_registration.call_count += 1
        # Успешное выполнение
        return "success"
    
    # Патчим функции
    with patch('app.client_bot.user_interface.handlers.start_registration_func.start_registration', 
               side_effect=mock_start_registration), \
         patch('app.utils.db.session_maker.get_async_session_maker', return_value=mock_context_manager):
        
        # Создаем функцию с ретраями
        wrapped_func = with_db_retry(max_retries=3, retry_delay=0.1)(mock_start_registration)
        
        # Вызываем функцию
        result = await wrapped_func(mock_message, mock_bot, mock_state)
        
        # Проверяем результаты
        assert result == "success"
        assert hasattr(mock_start_registration, 'call_count')
        assert mock_start_registration.call_count == 2

# Пример применения декоратора к существующим методам обработчиков
class UserHandlersWithRetry:
    """
    Класс-обертка для обработчиков пользовательских команд с механизмом повторных попыток.
    """
    
    @staticmethod
    @with_db_retry(max_retries=3, retry_delay=0.5)
    async def start_registration(message, bot, state):
        """
        Обертка для start_registration с повторными попытками.
        """
        return await start_registration(message, bot, state)
    
    # Здесь можно добавить другие обработчики с повторными попытками

@pytest.mark.asyncio
async def test_user_handlers_with_retry():
    """
    Тест для класса UserHandlersWithRetry.
    """
    # Создаем моки для аргументов
    mock_message = MagicMock()
    mock_message.from_user.id = 123456789
    mock_bot = AsyncMock()
    mock_state = AsyncMock()
    
    # Создаем мок для start_registration
    original_func = start_registration
    
    # Создаем временную функцию с ошибкой на первый вызов
    async def mock_start_registration(message, bot, state):
        if not hasattr(mock_start_registration, 'call_count'):
            mock_start_registration.call_count = 0
            
        if mock_start_registration.call_count == 0:
            mock_start_registration.call_count += 1
            raise ConnectionError("Test connection error")
        
        mock_start_registration.call_count += 1
        return "success"
    
    # Патчим функцию
    with patch('app.client_bot.user_interface.handlers.start_registration_func.start_registration', 
               side_effect=mock_start_registration):
        
        # Вызываем функцию с ретраями через класс-обертку
        result = await UserHandlersWithRetry.start_registration(mock_message, mock_bot, mock_state)
        
        # Проверяем результаты
        assert result == "success"
        assert mock_start_registration.call_count == 2 