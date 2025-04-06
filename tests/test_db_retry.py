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
import time
from functools import wraps

# Импортируем необходимые функции из проекта
from app.utils.db.session_maker import get_async_session_maker
from app.utils.db.models import User

# Настраиваем логирование
logger = logging.getLogger(__name__)

# Тип для асинхронной функции
T = TypeVar('T')

# Декоратор для повторных попыток при работе с базой данных
async def retry_async_db_operation(
    func: Callable[..., Awaitable[T]],
    *args: Any,
    max_retries: int = 3,
    retry_delay: float = 0.5,
    exponential_backoff: bool = True,
    retry_exceptions: tuple = (ConnectionError, TimeoutError, Exception),
    **kwargs: Any
) -> T:
    """
    Асинхронная функция-обертка для повторных попыток операций с базой данных.
    
    Args:
        func: Асинхронная функция для выполнения
        max_retries: Максимальное количество попыток
        retry_delay: Задержка между попытками в секундах
        exponential_backoff: Использовать экспоненциальную задержку между попытками
        retry_exceptions: Исключения, при которых нужно повторять попытки
        
    Returns:
        Результат выполнения функции
    """
    attempt = 0
    last_exception = None
    
    while attempt < max_retries:
        try:
            return await func(*args, **kwargs)
        except retry_exceptions as e:
            attempt += 1
            last_exception = e
            
            # Логируем ошибку и информацию о повторных попытках
            logger.warning(
                f"Database operation failed: {e.__class__.__name__}: {str(e)}. "
                f"Retrying {attempt}/{max_retries}..."
            )
            
            # Если это последняя попытка, то пробрасываем исключение
            if attempt >= max_retries:
                logger.error(f"Maximum retries reached. Last error: {e}")
                raise
            
            # Вычисляем задержку перед следующей попыткой
            if exponential_backoff:
                delay = retry_delay * (2 ** (attempt - 1))
            else:
                delay = retry_delay
                
            logger.info(f"Waiting {delay:.2f}s before next attempt...")
            await asyncio.sleep(delay)
    
    # Этот код не должен выполниться, но для безопасности
    if last_exception:
        raise last_exception
    raise RuntimeError("Unexpected error in retry_async_db_operation")

# Функция-декоратор для асинхронных функций
def with_db_retry(
    max_retries: int = 3,
    retry_delay: float = 0.5,
    exponential_backoff: bool = True,
    retry_exceptions: tuple = (ConnectionError, TimeoutError, Exception)
):
    """
    Декоратор для асинхронных функций, который добавляет логику повторных попыток.
    
    Args:
        max_retries: Максимальное количество попыток
        retry_delay: Задержка между попытками в секундах
        exponential_backoff: Использовать экспоненциальную задержку между попытками
        retry_exceptions: Исключения, при которых нужно повторять попытки
        
    Returns:
        Декорированная функция
    """
    def decorator(func):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            return await retry_async_db_operation(
                func,
                *args,
                max_retries=max_retries,
                retry_delay=retry_delay,
                exponential_backoff=exponential_backoff,
                retry_exceptions=retry_exceptions,
                **kwargs
            )
        return wrapper
    return decorator

# Пример использования декоратора с реальной функцией из проекта
@with_db_retry(max_retries=3, retry_delay=0.5)
async def get_user_by_telegram_id(telegram_id: int, read_only: bool = True) -> Optional[User]:
    """
    Получение пользователя по Telegram ID с повторными попытками при ошибках соединения.
    
    Args:
        telegram_id: ID пользователя в Telegram
        read_only: Флаг для использования только read-only соединения
        
    Returns:
        Объект пользователя или None, если пользователь не найден
    """
    async with get_async_session_maker(read_only=read_only) as session:
        stmt = select(User).where(User.user_telegram_id == telegram_id)
        result = await session.execute(stmt)
        return result.scalar_one_or_none()

# Тесты для функции повторных попыток
@pytest.mark.asyncio
async def test_retry_success_after_failure():
    """Тест успешного выполнения функции после временной ошибки"""
    # Создаем асинхронную мок-функцию, которая сначала вызывает ошибку, а потом возвращает результат
    mock_func = AsyncMock()
    mock_func.side_effect = [ConnectionError("Test connection error"), "success"]
    
    # Применяем функцию повторных попыток
    result = await retry_async_db_operation(
        mock_func,
        max_retries=3,
        retry_delay=0.1,
        exponential_backoff=False
    )
    
    # Проверяем, что функция была вызвана дважды и вернула правильный результат
    assert mock_func.call_count == 2
    assert result == "success"

@pytest.mark.asyncio
async def test_retry_max_attempts_reached():
    """Тест достижения максимального количества попыток"""
    # Создаем асинхронную мок-функцию, которая всегда вызывает ошибку
    error_message = "Test persistent error"
    mock_func = AsyncMock(side_effect=ConnectionError(error_message))
    
    # Применяем функцию повторных попыток и ожидаем, что она выбросит исключение
    with pytest.raises(ConnectionError) as excinfo:
        await retry_async_db_operation(
            mock_func,
            max_retries=3,
            retry_delay=0.1,
            exponential_backoff=False
        )
    
    # Проверяем, что функция была вызвана максимальное количество раз
    assert mock_func.call_count == 3
    # Проверяем сообщение об ошибке
    assert error_message in str(excinfo.value)

@pytest.mark.asyncio
async def test_with_db_retry_decorator():
    """Тест работы декоратора with_db_retry"""
    # Создаем асинхронную мок-функцию для декорирования
    mock_func = AsyncMock()
    mock_func.side_effect = [ConnectionError("Test connection error"), "success"]
    
    # Применяем декоратор к мок-функции
    decorated_func = with_db_retry(max_retries=3, retry_delay=0.1, exponential_backoff=False)(mock_func)
    
    # Вызываем декорированную функцию
    result = await decorated_func("test_arg", kwarg="test_kwarg")
    
    # Проверяем результаты
    assert mock_func.call_count == 2
    assert result == "success"
    # Проверяем, что аргументы были переданы правильно
    mock_func.assert_called_with("test_arg", kwarg="test_kwarg")

@pytest.mark.asyncio
async def test_get_user_with_retry():
    """Тест функции получения пользователя с повторными попытками"""
    # Мокируем пользователя
    mock_user = MagicMock(spec=User)
    mock_user.user_telegram_id = 123456789
    
    # Мокируем сессию и результат запроса
    mock_session = AsyncMock(spec=AsyncSession)
    mock_result = MagicMock()
    mock_result.scalar_one_or_none.return_value = mock_user
    mock_session.execute.return_value = mock_result
    
    # Мокируем функцию создания сессии
    mock_context_manager = MagicMock()
    mock_context_manager.__aenter__.return_value = mock_session
    mock_context_manager.__aexit__.return_value = None
    
    # Создаем отдельную функцию для тестирования, которая имитирует временные ошибки
    @with_db_retry(max_retries=3, retry_delay=0.1)
    async def test_get_user_func(telegram_id: int):
        nonlocal mock_session, mock_result
        # Ошибка соединения на первой попытке
        if test_get_user_func.call_count == 0:
            test_get_user_func.call_count += 1
            raise ConnectionError("Test connection error")
        test_get_user_func.call_count += 1
        # Для второй попытки возвращаем пользователя
        async with get_async_session_maker() as session:
            stmt = select(User).where(User.user_telegram_id == telegram_id)
            result = await session.execute(stmt)
            return result.scalar_one_or_none()
    
    # Инициализируем счетчик вызовов
    test_get_user_func.call_count = 0
    
    # Патчим функцию get_async_session_maker
    with patch('app.utils.db.session_maker.get_async_session_maker', return_value=mock_context_manager):
        # Вызываем тестируемую функцию
        user = await test_get_user_func(123456789)
        
        # Проверяем результат
        assert user == mock_user
        assert test_get_user_func.call_count == 2  # Функция должна быть вызвана дважды

@pytest.mark.asyncio
async def test_exponential_backoff():
    """Тест экспоненциального увеличения задержки"""
    # Создаем асинхронную мок-функцию, которая всегда вызывает ошибку
    mock_func = AsyncMock(side_effect=ConnectionError("Test error"))
    
    # Мокируем asyncio.sleep для отслеживания значений задержки
    sleep_values = []
    
    async def mock_sleep(delay):
        sleep_values.append(delay)
    
    # Патчим asyncio.sleep
    with patch('asyncio.sleep', mock_sleep):
        # Применяем функцию повторных попыток с экспоненциальной задержкой
        with pytest.raises(ConnectionError):
            await retry_async_db_operation(
                mock_func,
                max_retries=4,
                retry_delay=0.5,
                exponential_backoff=True
            )
    
    # Проверяем, что задержки увеличиваются экспоненциально
    assert len(sleep_values) == 3  # 3 задержки для 4 попыток
    assert sleep_values[0] == 0.5  # Начальная задержка
    assert sleep_values[1] == 1.0  # Вторая задержка (0.5 * 2^1)
    assert sleep_values[2] == 2.0  # Третья задержка (0.5 * 2^2) 