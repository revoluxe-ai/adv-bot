#!/usr/bin/env python
"""
Скрипт для тестирования механизма повторных попыток соединения с базой данных.
Этот скрипт можно запустить отдельно для проверки работы механизма повторных попыток.
"""
import asyncio
import logging
import sys
import os
import traceback
import random
from datetime import datetime

# Добавляем родительскую директорию в путь импорта
sys.path.append(os.path.abspath(os.path.dirname(__file__) + "/.."))

# Импортируем механизм повторных попыток
from tests.test_db_retry import retry_async_db_operation, with_db_retry

# Импортируем необходимые функции из проекта
from app.utils.db.session_maker import get_async_session_maker
from sqlalchemy import select, text

# Настраиваем логирование
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger("retry_test")

# Функция для тестирования простого запроса к базе данных
async def test_simple_query():
    """
    Тестирование простого запроса к базе данных с механизмом повторных попыток.
    """
    logger.info("Тестирование простого запроса с повторными попытками...")
    
    # Функция запроса с искусственным вызовом ошибки
    async def query_with_random_error():
        # С вероятностью 70% вызываем ошибку в первые две попытки
        if random.random() < 0.7 and getattr(query_with_random_error, 'attempts', 0) < 2:
            setattr(query_with_random_error, 'attempts', 
                    getattr(query_with_random_error, 'attempts', 0) + 1)
            logger.warning(f"Симуляция ошибки соединения (попытка {getattr(query_with_random_error, 'attempts', 0)})")
            raise ConnectionError("Simulated connection error")
        
        # Иначе выполняем запрос
        async with get_async_session_maker(read_only=True) as session:
            # Простой запрос для проверки соединения
            result = await session.execute(text("SELECT 1 as test"))
            return result.scalar_one()
    
    try:
        # Применяем механизм повторных попыток
        result = await retry_async_db_operation(
            query_with_random_error,
            max_retries=5,
            retry_delay=0.5,
            exponential_backoff=True
        )
        logger.info(f"Результат запроса: {result}")
        return True
    except Exception as e:
        logger.error(f"Ошибка при выполнении запроса: {e}")
        traceback.print_exc()
        return False

# Функция с декоратором повторных попыток
@with_db_retry(max_retries=3, retry_delay=0.5)
async def decorated_query(fail_count=2):
    """
    Функция запроса с декоратором повторных попыток.
    
    Args:
        fail_count: Количество первых попыток, которые должны завершиться ошибкой
    """
    # Сохраняем счетчик попыток как атрибут функции
    if not hasattr(decorated_query, 'attempts'):
        decorated_query.attempts = 0
    
    decorated_query.attempts += 1
    
    # Симулируем ошибки в первых нескольких попытках
    if decorated_query.attempts <= fail_count:
        logger.warning(f"Симуляция ошибки в decorated_query (попытка {decorated_query.attempts})")
        raise ConnectionError(f"Simulated error in decorated_query (attempt {decorated_query.attempts})")
    
    # Выполняем запрос
    async with get_async_session_maker(read_only=True) as session:
        result = await session.execute(text("SELECT 2 as test"))
        return result.scalar_one()

# Тестирование декорированной функции
async def test_decorated_function():
    """
    Тестирование декорированной функции с механизмом повторных попыток.
    """
    logger.info("Тестирование функции с декоратором повторных попыток...")
    
    try:
        # Сбрасываем счетчик попыток
        if hasattr(decorated_query, 'attempts'):
            decorated_query.attempts = 0
        
        # Вызываем декорированную функцию
        result = await decorated_query(fail_count=2)
        logger.info(f"Результат декорированной функции: {result}")
        return True
    except Exception as e:
        logger.error(f"Ошибка при вызове декорированной функции: {e}")
        traceback.print_exc()
        return False

# Функция для тестирования случая с превышением максимального количества попыток
async def test_max_retries_exceeded():
    """
    Тестирование случая, когда все попытки завершаются ошибкой.
    """
    logger.info("Тестирование превышения максимального количества попыток...")
    
    # Функция, которая всегда вызывает ошибку
    async def always_fail():
        raise ConnectionError("Always failing function")
    
    try:
        # Применяем механизм повторных попыток с малым количеством попыток
        result = await retry_async_db_operation(
            always_fail,
            max_retries=2,
            retry_delay=0.1,
            exponential_backoff=False
        )
        logger.error("Тест провален: функция должна была выбросить исключение")
        return False
    except ConnectionError:
        logger.info("Тест пройден: получено ожидаемое исключение после исчерпания попыток")
        return True
    except Exception as e:
        logger.error(f"Тест провален: получено неожиданное исключение: {e}")
        traceback.print_exc()
        return False

# Главная функция
async def main():
    """
    Главная функция скрипта тестирования.
    """
    logger.info(f"Начало тестирования механизма повторных попыток {datetime.now().isoformat()}")
    
    # Тестируем все функции
    tests = [
        ("Простой запрос с повторными попытками", test_simple_query),
        ("Функция с декоратором повторных попыток", test_decorated_function),
        ("Превышение максимального количества попыток", test_max_retries_exceeded)
    ]
    
    results = []
    
    for test_name, test_func in tests:
        logger.info(f"\n=== Запуск теста: {test_name} ===")
        try:
            success = await test_func()
            results.append((test_name, success))
            logger.info(f"=== Тест '{test_name}': {'УСПЕХ' if success else 'ПРОВАЛ'} ===\n")
        except Exception as e:
            logger.error(f"Неожиданная ошибка при выполнении теста '{test_name}': {e}")
            traceback.print_exc()
            results.append((test_name, False))
    
    # Выводим итоговые результаты
    logger.info("\n=== Результаты тестирования ===")
    all_success = True
    for test_name, success in results:
        logger.info(f"{test_name}: {'УСПЕХ' if success else 'ПРОВАЛ'}")
        all_success = all_success and success
    
    logger.info(f"\n=== Общий результат тестирования: {'УСПЕХ' if all_success else 'ПРОВАЛ'} ===")
    logger.info(f"Тестирование завершено {datetime.now().isoformat()}")
    
    return 0 if all_success else 1

# Точка входа
if __name__ == "__main__":
    try:
        exit_code = asyncio.run(main())
        sys.exit(exit_code)
    except KeyboardInterrupt:
        logger.info("Тестирование прервано пользователем")
        sys.exit(1)
    except Exception as e:
        logger.error(f"Неожиданная ошибка: {e}")
        traceback.print_exc()
        sys.exit(1) 