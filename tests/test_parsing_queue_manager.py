import pytest
import random
from unittest.mock import AsyncMock, patch, MagicMock

from app.modules.wb_keywords_parser.wb_parser.parsing_page_queue_manager import ParsingQueueManager
from app.modules.common_slaves.wildberries.models import WBItemPosition


@pytest.fixture
def parsing_queue_manager():
    manager = ParsingQueueManager()
    manager.redis_manager = AsyncMock()
    return manager


@pytest.mark.asyncio
async def test_add_found_not_found_page(parsing_queue_manager):
    """Тестирует сохранение информации о найденных и не найденных позициях на странице"""
    # Подготовка данных
    text = "тестовый запрос"
    nmid1 = 12345678
    nmid2 = 87654321
    need_nmids = {nmid1, nmid2}
    page = 3
    
    # Создаем позицию только для первого nmid (второй будет считаться не найденным)
    positions = [
        WBItemPosition(
            nmid=nmid1,
            real_position=100, 
            base_position=100,
            promo_position=2,
            keyword_text=text,
            cpm=120
        )
    ]
    
    # Выполнение
    await parsing_queue_manager.add_found_not_found_page(text, positions, need_nmids, page)
    
    # Проверка
    parsing_queue_manager.redis_manager.add_last_found_page_for_text_nmid.assert_called_once_with(
        text, nmid1, page
    )
    parsing_queue_manager.redis_manager.add_last_not_found_page_for_text_nmid.assert_called_once_with(
        text, nmid2, page
    )


@pytest.mark.asyncio
async def test_get_parsing_queue_smart_order(parsing_queue_manager):
    """Тестирует получение умной очереди для парсинга страниц"""
    # Подготовка данных
    text = "тестовый запрос"
    nmid1 = 12345678
    nmid2 = 87654321
    need_nmids = {nmid1, nmid2}
    max_pages = 10
    
    # Моки для возвращаемых значений
    # nmid1 был найден на страницах 3, 5
    parsing_queue_manager.redis_manager.get_found_pages_for_text_nmid.side_effect = [
        [3, 5],  # для nmid1
        [7],     # для nmid2
    ]
    
    # nmid1 не был найден на странице 8
    # nmid2 не был найден на страницах 2, 4
    parsing_queue_manager.redis_manager.get_not_found_pages_for_text_nmid.side_effect = [
        [8],       # для nmid1
        [2, 4],    # для nmid2
    ]
    
    # Мокируем random.shuffle, чтобы тест был детерминированным
    with patch('random.shuffle', lambda x: None):
        # Выполнение
        result = await parsing_queue_manager.get_parsing_queue(text, need_nmids, max_pages)
    
    # Проверка
    # Ожидаем, что сначала будут страницы, где находили позиции (3, 5, 7)
    # Затем страницы, где никогда не искали (1, 6, 9, 10)
    # И в конце страницы, где не находили позиции (2, 4, 8)
    
    # Проверяем вызовы методов Redis
    assert parsing_queue_manager.redis_manager.get_found_pages_for_text_nmid.call_count == 2
    assert parsing_queue_manager.redis_manager.get_not_found_pages_for_text_nmid.call_count == 2
    
    # Проверяем, что в результате есть все страницы от 1 до max_pages
    assert len(result) == max_pages
    assert set(result) == set(range(1, max_pages + 1))
    
    # Проверяем, что страницы, где находили позиции, идут первыми
    found_pages = {3, 5, 7}
    first_pages = set(result[:len(found_pages)])
    assert found_pages.issubset(first_pages)
    
    # Проверяем, что страницы, где не находили позиции, идут последними
    not_found_pages = {2, 4, 8}
    last_pages = set(result[-len(not_found_pages):])
    assert not_found_pages.issubset(last_pages)
    
    # Проверяем, что результат не содержит дубликатов
    assert len(result) == len(set(result))


@pytest.mark.asyncio
async def test_get_parsing_queue_with_empty_history(parsing_queue_manager):
    """Тестирует получение очереди для парсинга страниц при пустой истории"""
    # Подготовка данных
    text = "новый запрос"
    nmid1 = 12345678
    need_nmids = {nmid1}
    max_pages = 5
    
    # Имитируем отсутствие истории поиска
    parsing_queue_manager.redis_manager.get_found_pages_for_text_nmid.return_value = []
    parsing_queue_manager.redis_manager.get_not_found_pages_for_text_nmid.return_value = []
    
    # Мокируем random.shuffle, чтобы тест был детерминированным
    with patch('random.shuffle', lambda x: None):
        # Выполнение
        result = await parsing_queue_manager.get_parsing_queue(text, need_nmids, max_pages)
    
    # Проверка
    # При отсутствии истории должны получить все страницы от 1 до max_pages
    assert set(result) == set(range(1, max_pages + 1))
    assert len(result) == max_pages
    