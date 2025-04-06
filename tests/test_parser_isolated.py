import sys
import asyncio
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

# Мокируем другие модули, которые могут вызывать проблемы
sys.modules['app.modules.keywords_query'] = MagicMock()
sys.modules['app.modules.keywords_query.keywords_query'] = MagicMock(
    queries_dict={},
    min_query=50,
    get_query_freq=lambda x: 100
)

# Мокируем SQLAlchemy
sys.modules['sqlalchemy'] = MagicMock()
sys.modules['sqlalchemy.select'] = MagicMock()

# Мокируем модуль arq
sys.modules['arq'] = MagicMock()
sys.modules['arq.Retry'] = MagicMock()
sys.modules['arq.create_pool'] = MagicMock()

# Мокируем aiohttp
sys.modules['aiohttp'] = MagicMock()
sys.modules['aiohttp.ClientSession'] = AsyncMock()
sys.modules['aiohttp.ServerDisconnectedError'] = Exception
sys.modules['aiohttp.ClientOSError'] = Exception

# Мокируем loggers
logging_mock = MagicMock()
sys.modules['logging'] = logging_mock
logging_mock.getLogger.return_value = MagicMock(
    debug=MagicMock(),
    info=MagicMock(),
    warning=MagicMock(),
    error=MagicMock(),
    critical=MagicMock()
)

# Импортируем необходимые классы для тестов
# Мок для класса WBItemPosition
class WBItemPosition:
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


# Определяем классы исключений, которые используются в парсере
class DataError(Exception):
    def __init__(self, message, text=None):
        self.message = message
        self.text = text
        super().__init__(message)


class TotalPages:
    def __init__(self):
        self._total_pages = 60

    @property
    def total_pages(self):
        return self._total_pages

    @total_pages.setter
    def total_pages(self, value):
        if value > 60:
            value = 60
        self._total_pages = value


# Фикстура для event_loop
@pytest.fixture(scope="session")
def event_loop():
    """Create an instance of the default event loop for each test case."""
    try:
        loop = asyncio.get_event_loop()
    except RuntimeError:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
    yield loop
    if not loop.is_closed():
        loop.close()


# Тесты
@pytest.mark.asyncio
@patch('app.modules.wb_keywords_parser.parsing_queue_manager.ParsingQueueManager')
async def test_parsing_queue_manager_add_found_not_found_page():
    """
    Тест проверяет функциональность метода add_found_not_found_page класса ParsingQueueManager
    """
    # Импортируем здесь для избежания проблем с импортами
    from app.modules.wb_keywords_parser.parsing_queue_manager import ParsingQueueManager
    
    # Создаем экземпляр ParsingQueueManager
    manager = ParsingQueueManager()
    manager.redis_manager = AsyncMock()
    
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
    await manager.add_found_not_found_page(text, positions, need_nmids, page)
    
    # Проверка
    manager.redis_manager.add_last_found_page_for_text_nmid.assert_called_once_with(
        text, nmid1, page
    )
    manager.redis_manager.add_last_not_found_page_for_text_nmid.assert_called_once_with(
        text, nmid2, page
    )


@pytest.mark.asyncio
@patch('app.modules.wb_keywords_parser.parsing_found_redis_manager.BaseRedis', new_callable=AsyncMock)
async def test_parsing_found_redis_manager():
    """
    Тест проверяет функциональность методов класса ParsingFoundRedisManager
    """
    # Импортируем здесь для избежания проблем с импортами
    from app.modules.wb_keywords_parser.parsing_found_redis_manager import ParsingFoundRedisManager
    
    # Создаем экземпляр ParsingFoundRedisManager
    manager = ParsingFoundRedisManager()
    manager._client = AsyncMock()
    
    # Подготовка данных
    text = "тестовый запрос"
    nmid = 12345678
    page = 3
    
    # Для имитации текущего времени
    with patch('app.modules.wb_keywords_parser.parsing_found_redis_manager.time', return_value=1234567890.0):
        # Выполнение - добавление найденной страницы
        await manager.add_last_found_page_for_text_nmid(text, nmid, page)
        
        # Проверка
        manager._client.zadd.assert_called_once()
        args, kwargs = manager._client.zadd.call_args
        assert args[0] == f"found_pages:{text}:{nmid}"
        assert page in args[1]
        assert args[1][page] == 1234567890.0
        
        # Сбрасываем счетчик вызовов
        manager._client.zadd.reset_mock()
        
        # Выполнение - добавление не найденной страницы
        await manager.add_last_not_found_page_for_text_nmid(text, nmid, page)
        
        # Проверка
        manager._client.zadd.assert_called_once()
        args, kwargs = manager._client.zadd.call_args
        assert args[0] == f"not_found_pages:{text}:{nmid}"
        assert page in args[1]
        assert args[1][page] == 1234567890.0
    
    # Настраиваем ответ от Redis для метода получения найденных страниц
    manager._client.zrange.return_value = ["1", "3", "5"]
    
    # Выполнение - получение найденных страниц
    found_pages = await manager.get_found_pages_for_text_nmid(text, nmid)
    
    # Проверка
    manager._client.zrange.assert_called_once_with(f"found_pages:{text}:{nmid}", 0, -1)
    assert found_pages == [1, 3, 5]
    assert all(isinstance(page, int) for page in found_pages)
    
    # Сбрасываем счетчик вызовов
    manager._client.zrange.reset_mock()
    
    # Настраиваем ответ от Redis для метода получения не найденных страниц
    manager._client.zrange.return_value = ["2", "4", "6"]
    
    # Выполнение - получение не найденных страниц
    not_found_pages = await manager.get_not_found_pages_for_text_nmid(text, nmid)
    
    # Проверка
    manager._client.zrange.assert_called_once_with(f"not_found_pages:{text}:{nmid}", 0, -1)
    assert not_found_pages == [2, 4, 6]
    assert all(isinstance(page, int) for page in not_found_pages)


@pytest.mark.asyncio
@patch('app.modules.wb_keywords_parser.parsing_queue_manager.ParsingQueueManager')
async def test_parsing_queue_manager_get_parsing_queue():
    """
    Тест проверяет метод get_parsing_queue класса ParsingQueueManager
    """
    # Импортируем здесь для избежания проблем с импортами
    from app.modules.wb_keywords_parser.parsing_queue_manager import ParsingQueueManager
    
    # Создаем экземпляр ParsingQueueManager
    manager = ParsingQueueManager()
    manager.redis_manager = AsyncMock()
    
    # Подготовка данных
    text = "тестовый запрос"
    nmid1 = 12345678
    nmid2 = 87654321
    need_nmids = {nmid1, nmid2}
    max_pages = 5
    
    # Настраиваем ответы от redis_manager
    manager.redis_manager.get_found_pages_for_text_nmid.side_effect = [
        [3, 5],  # Для nmid1
        [1]      # Для nmid2
    ]
    
    manager.redis_manager.get_not_found_pages_for_text_nmid.side_effect = [
        [2],     # Для nmid1
        [4]      # Для nmid2
    ]
    
    # Чтобы тест был детерминированным, мокируем функцию random.shuffle
    with patch('random.shuffle', lambda x: None):
        # Выполнение
        result = await manager.get_parsing_queue(text, need_nmids, max_pages)
        
        # Проверка
        # Ожидаем, что сначала будут страницы, где находили позиции (1, 3, 5)
        # Затем оставшиеся страницы (2, 4)
        # Проверяем, что все страницы присутствуют и нет дубликатов
        assert len(result) == max_pages
        assert set(result) == set(range(1, max_pages + 1)) 