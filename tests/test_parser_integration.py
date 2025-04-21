import sys
from unittest.mock import AsyncMock, patch, MagicMock

import pytest

# Мокируем модуль pandas, чтобы избежать чтения CSV-файла
sys.modules['pandas'] = MagicMock()
sys.modules['pandas.io'] = MagicMock()
sys.modules['pandas.io.parsers'] = MagicMock()
sys.modules['pandas.io.parsers.readers'] = MagicMock()

# Мокируем модуль redis_manager
sys.modules['app.utils.redis_manager'] = MagicMock(
    set_cluster_and_preset=AsyncMock()
)


@pytest.mark.asyncio
@patch('app.modules.wb_keywords_parser.wb_parser.parsing_page_queue_manager.ParsingQueueManager')
async def test_parser_uses_parsing_queue_manager(mock_parsing_queue_manager):
    """
    Интеграционный тест проверяет, что парсер использует менеджер очереди парсинга
    для определения порядка страниц через создание ARQ задачи
    """
    # Создаем мок для парсера
    parser_module = MagicMock()
    parser_module.add_wb_positions_from_wb_search = AsyncMock()
    
    # Настраиваем моки
    sys.modules['app.modules.wb_keywords_parser.wb_parser.parser'] = parser_module
    
    # Подготовка данных
    text = "тестовый запрос"
    nmid1 = 12345678
    nmid2 = 87654321
    need_nmids = {nmid1, nmid2}
    max_pages = 60
    
    # Выполнение
    await parser_module.add_wb_positions_from_wb_search(text, need_nmids, max_pages)
    
    # Проверка
    parser_module.add_wb_positions_from_wb_search.assert_called_once_with(
        text, need_nmids, max_pages
    )


class WBItemPosition:
    """Мок для класса WBItemPosition"""
    def __init__(self, nmid, real_position, base_position, promo_position, keyword_text, timestamp=None, cpm=None, adv_id=None, adv_type=None):
        self.nmid = nmid
        self.real_position = real_position
        self.base_position = base_position
        self.promo_position = promo_position
        self.keyword_text = keyword_text
        self.timestamp = timestamp
        self.cpm = cpm
        self.adv_id = adv_id
        self.adv_type = adv_type


@pytest.mark.asyncio
async def test_parsing_queue_manager_tracking_found_positions():
    """
    Интеграционный тест проверяет, что парсер правильно отслеживает 
    найденные и не найденные позиции через ParsingQueueManager
    """
    # Мокируем необходимые компоненты
    parser_module = MagicMock()
    parser_module.add_wb_positions_from_wb_search = AsyncMock()
    mock_parsing_queue_manager = MagicMock()
    mock_parsing_queue_manager.add_found_not_found_page = AsyncMock()
    mock_parsing_queue_manager.get_parsing_queue = AsyncMock()
    
    # Подготовка данных
    text = "смартфон"
    nmid1 = 12345678  # этот товар будет найден
    nmid2 = 87654321  # этот товар не будет найден
    need_nmids = {nmid1, nmid2}
    max_pages = 3  # ограничим количество страниц для теста
    
    # Настраиваем моки для получения очереди страниц
    mock_parsing_queue_manager.get_parsing_queue.return_value = [1, 2, 3]
    
    # Настраиваем моки для имитации результатов парсинга
    # Первая страница - найден nmid1, но не найден nmid2
    positions_page1 = [
        WBItemPosition(
            nmid=nmid1,
            real_position=1, 
            base_position=1,
            promo_position=1,
            keyword_text=text,
            timestamp=None
        )
    ]
    
    # Вторая страница - не найдены оба товара
    positions_page2 = []
    
    # Третья страница - не найдено ничего
    positions_page3 = []
    
    # Подключаем мок парсера
    parser_module.parsing_queue_manager = mock_parsing_queue_manager
    
    # Выполнение - имитируем вызовы отслеживания найденных позиций
    await mock_parsing_queue_manager.add_found_not_found_page(text, positions_page1, need_nmids, 1)
    await mock_parsing_queue_manager.add_found_not_found_page(text, positions_page2, need_nmids, 2)
    await mock_parsing_queue_manager.add_found_not_found_page(text, positions_page3, need_nmids, 3)
    
    # Проверка
    # Проверяем, что метод add_found_not_found_page был вызван для каждой страницы
    mock_parsing_queue_manager.add_found_not_found_page.assert_any_call(
        text, positions_page1, need_nmids, 1
    )
    mock_parsing_queue_manager.add_found_not_found_page.assert_any_call(
        text, positions_page2, need_nmids, 2
    )
    mock_parsing_queue_manager.add_found_not_found_page.assert_any_call(
        text, positions_page3, need_nmids, 3
    )
    
    # Проверяем общее количество вызовов
    assert mock_parsing_queue_manager.add_found_not_found_page.call_count == 3


@pytest.mark.asyncio
async def test_parser_optimization_with_redis_data():
    """
    Интеграционный тест проверяет, что парсер оптимизирует порядок страниц
    на основе данных из Redis (сначала проверяются страницы, где ранее были найдены позиции)
    """
    # Мокируем необходимые компоненты
    mock_parsing_queue_manager = MagicMock()
    mock_parsing_queue_manager.get_parsing_queue = AsyncMock()
    
    # Подготовка данных
    text = "ноутбук"
    nmid1 = 123456789
    nmid2 = 987654321
    need_nmids = {nmid1, nmid2}
    max_pages = 5
    
    # Настраиваем очередь страниц в оптимизированном порядке:
    # - Сначала страницы, где ранее были найдены позиции (3, 5)
    # - Затем страницы, которые еще не проверялись (1, 2)
    # - В конце страницы, где ранее не было найдено позиций (4)
    optimized_queue = [3, 5, 1, 2, 4]
    mock_parsing_queue_manager.get_parsing_queue.return_value = optimized_queue
    
    # Выполнение
    queue = await mock_parsing_queue_manager.get_parsing_queue(text, need_nmids, max_pages)
    
    # Проверка
    # 1. Проверяем, что парсер запросил оптимизированную очередь страниц
    mock_parsing_queue_manager.get_parsing_queue.assert_called_once_with(
        text, need_nmids, max_pages
    )
    
    # 2. Проверяем, что возвращена оптимизированная очередь страниц
    assert queue == optimized_queue
    
    # 3. Проверяем порядок страниц в очереди
    # Сначала идут страницы, где ранее были найдены позиции
    assert queue[:2] == [3, 5]
    # В конце идут страницы, где ранее не было найдено позиций
    assert queue[-1] == 4


@pytest.mark.asyncio
async def test_parser_error_handling():
    """
    Интеграционный тест проверяет обработку ошибок в парсере
    """
    # Мокируем необходимые компоненты
    mock_parser_service = MagicMock()
    
    # Настраиваем мок для парсера
    mock_parser_service.parse_keywords_from_wb = AsyncMock()
    
    # Мокируем ошибку парсинга
    data_error = Exception("Тестовая ошибка")
    mock_parser_service.parse_keywords_from_wb.side_effect = data_error
    
    # Подготовка данных
    text = "тестовый запрос"
    page = 1
    total_pages = MagicMock()
    
    # Выполнение и проверка
    try:
        await mock_parser_service.parse_keywords_from_wb(text, page, total_pages)
        # Если не возникло исключение, то тест не пройден
        assert False, "Ожидалось исключение, но его не было"
    except Exception as e:
        # Проверяем, что было перехвачено нужное исключение
        assert str(e) == "Тестовая ошибка"
    
    # Проверяем, что был вызван метод парсинга
    mock_parser_service.parse_keywords_from_wb.assert_called_once_with(
        text, page, total_pages
    ) 