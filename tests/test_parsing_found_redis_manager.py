import pytest
from unittest.mock import AsyncMock, patch, MagicMock

from app.modules.wb_keywords_parser.parsing_found_redis_manager import ParsingFoundRedisManager


@pytest.fixture
def redis_manager():
    manager = ParsingFoundRedisManager()
    manager._client = AsyncMock()
    return manager


@pytest.mark.asyncio
async def test_add_last_found_page_for_text_nmid(redis_manager):
    """Тестирует сохранение страницы, где была найдена позиция"""
    # Подготовка данных
    text = "тестовый запрос"
    nmid = 12345678
    page = 3
    
    # Выполнение
    with patch('app.modules.wb_keywords_parser.parsing_found_redis_manager.time', return_value=1234567890.0):
        await redis_manager.add_last_found_page_for_text_nmid(text, nmid, page)
    
    # Проверка
    redis_manager._client.zadd.assert_called_once()
    args, kwargs = redis_manager._client.zadd.call_args
    assert args[0] == f"found_pages:{text}:{nmid}"
    assert page in args[1]
    assert args[1][page] == 1234567890.0


@pytest.mark.asyncio
async def test_add_last_not_found_page_for_text_nmid(redis_manager):
    """Тестирует сохранение страницы, где не была найдена позиция"""
    # Подготовка данных
    text = "тестовый запрос"
    nmid = 12345678
    page = 5
    
    # Выполнение
    with patch('app.modules.wb_keywords_parser.parsing_found_redis_manager.time', return_value=1234567890.0):
        await redis_manager.add_last_not_found_page_for_text_nmid(text, nmid, page)
    
    # Проверка
    redis_manager._client.zadd.assert_called_once()
    args, kwargs = redis_manager._client.zadd.call_args
    assert args[0] == f"not_found_pages:{text}:{nmid}"
    assert page in args[1]
    assert args[1][page] == 1234567890.0


@pytest.mark.asyncio
async def test_get_found_pages_for_text_nmid(redis_manager):
    """Тестирует получение страниц, где была найдена позиция"""
    # Подготовка данных
    text = "тестовый запрос"
    nmid = 12345678
    
    # Имитируем ответ от Redis
    redis_manager._client.zrange.return_value = ["1", "3", "5"]
    
    # Выполнение
    result = await redis_manager.get_found_pages_for_text_nmid(text, nmid)
    
    # Проверка
    redis_manager._client.zrange.assert_called_once_with(f"found_pages:{text}:{nmid}", 0, -1)
    assert result == [1, 3, 5]
    assert all(isinstance(page, int) for page in result)


@pytest.mark.asyncio
async def test_get_not_found_pages_for_text_nmid(redis_manager):
    """Тестирует получение страниц, где не была найдена позиция"""
    # Подготовка данных
    text = "тестовый запрос"
    nmid = 12345678
    
    # Имитируем ответ от Redis
    redis_manager._client.zrange.return_value = ["2", "4", "6"]
    
    # Выполнение
    result = await redis_manager.get_not_found_pages_for_text_nmid(text, nmid)
    
    # Проверка
    redis_manager._client.zrange.assert_called_once_with(f"not_found_pages:{text}:{nmid}", 0, -1)
    assert result == [2, 4, 6]
    assert all(isinstance(page, int) for page in result)


@pytest.mark.asyncio
async def test_get_empty_pages_for_text_nmid(redis_manager):
    """Тестирует получение пустого списка страниц"""
    # Подготовка данных
    text = "тестовый запрос"
    nmid = 12345678
    
    # Имитируем пустой ответ от Redis
    redis_manager._client.zrange.return_value = []
    
    # Выполнение
    result = await redis_manager.get_found_pages_for_text_nmid(text, nmid)
    
    # Проверка
    redis_manager._client.zrange.assert_called_once()
    assert result == [] 