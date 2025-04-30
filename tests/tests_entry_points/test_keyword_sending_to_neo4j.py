import asyncio
from unittest.mock import AsyncMock, patch, MagicMock

import pytest

# Предполагаем, что в keyword_sending_to_neo4j.py есть функция main или класс KeywordSender
# Адаптируйте импорт под реальную структуру модуля
try:
    from keyword_sending_to_neo4j import KeywordSender
    class_based = True
except ImportError:
    from keyword_sending_to_neo4j import main
    class_based = False


@pytest.mark.asyncio
async def test_keyword_sender_initialization():
    """
    Тест проверяет, что класс или функция KeywordSender инициализируется корректно
    """
    if class_based:
        # Для класса KeywordSender
        
        # Мокируем зависимости
        with patch("keyword_sending_to_neo4j.get_config") as mock_get_config, \
             patch("keyword_sending_to_neo4j.setup_logging") as mock_setup_logging, \
             patch("keyword_sending_to_neo4j.init_neo4j") as mock_init_neo4j, \
             patch("keyword_sending_to_neo4j.init_db_connection") as mock_init_db:
            
            # Настраиваем мок-конфиг
            mock_get_config.return_value = {
                "db_connection": "test_connection_string",
                "neo4j_uri": "bolt://localhost:7687",
                "neo4j_user": "neo4j",
                "neo4j_password": "password",
                "log_level": "INFO"
            }
            
            # Создаем экземпляр KeywordSender
            sender = KeywordSender()
            
            # Проверяем, что зависимости были вызваны
            mock_get_config.assert_called_once()
            mock_setup_logging.assert_called_once()
            mock_init_neo4j.assert_called_once()
            mock_init_db.assert_called_once()
            
            # Проверяем, что атрибуты настроены правильно
            assert hasattr(sender, "config"), "У объекта KeywordSender должен быть атрибут config"
    else:
        # Для функции main
        
        # Мокируем функции инициализации
        with patch("keyword_sending_to_neo4j.setup_logging") as mock_setup_logging, \
             patch("keyword_sending_to_neo4j.load_config") as mock_load_config, \
             patch("keyword_sending_to_neo4j.init_neo4j") as mock_init_neo4j, \
             patch("keyword_sending_to_neo4j.init_db") as mock_init_db:
             
            # Настраиваем мок-функции
            mock_load_config.return_value = {
                "db_connection": "test_connection_string",
                "neo4j_uri": "bolt://localhost:7687",
                "neo4j_user": "neo4j",
                "neo4j_password": "password",
                "log_level": "INFO"
            }
            mock_init_neo4j.return_value = MagicMock()
            mock_init_db.return_value = MagicMock()
            
            # Блокируем реальное выполнение
            with patch("asyncio.run"):
                # Импортируем модуль
                import keyword_sending_to_neo4j
                
                # Проверяем, что функции инициализации были вызваны
                mock_setup_logging.assert_called_once()
                mock_load_config.assert_called_once()
                mock_init_neo4j.assert_called_once()
                mock_init_db.assert_called_once()


@pytest.mark.asyncio
async def test_keyword_sender_fetches_keywords():
    """
    Тест проверяет, что метод run получает ключевые слова из базы данных
    """
    if class_based:
        # Для класса KeywordSender
        
        # Создаем экземпляр KeywordSender
        sender = KeywordSender()
        
        # Мокируем методы, которые должны вызываться из run
        test_keywords = [
            {"keyword": "keyword1", "frequency": 100},
            {"keyword": "keyword2", "frequency": 200}
        ]
        sender.fetch_keywords_from_db = AsyncMock(return_value=test_keywords)
        sender.send_keywords_to_neo4j = AsyncMock()
        
        # Вызываем тестируемый метод
        await sender.run()
        
        # Проверяем, что метод получения ключевых слов был вызван
        sender.fetch_keywords_from_db.assert_called_once()
        
        # Проверяем, что метод отправки ключевых слов был вызван с правильными аргументами
        sender.send_keywords_to_neo4j.assert_called_once_with(test_keywords)
    else:
        # Для функции main
        
        # Мокируем функции
        test_keywords = [
            {"keyword": "keyword1", "frequency": 100},
            {"keyword": "keyword2", "frequency": 200}
        ]
        with patch("keyword_sending_to_neo4j.fetch_keywords_from_db", new_callable=AsyncMock) as mock_fetch, \
             patch("keyword_sending_to_neo4j.send_keywords_to_neo4j", new_callable=AsyncMock) as mock_send:
             
            # Настраиваем мок-функции
            mock_fetch.return_value = test_keywords
            
            # Вызываем тестируемую функцию
            await main()
            
            # Проверяем, что функция получения ключевых слов была вызвана
            mock_fetch.assert_called_once()
            
            # Проверяем, что функция отправки ключевых слов была вызвана с правильными аргументами
            mock_send.assert_called_once_with(test_keywords)


@pytest.mark.asyncio
async def test_keyword_sender_sends_to_neo4j():
    """
    Тест проверяет, что метод send_keywords_to_neo4j корректно отправляет ключевые слова в Neo4j
    """
    if class_based:
        # Для класса KeywordSender
        
        # Создаем экземпляр KeywordSender
        sender = KeywordSender()
        
        # Мокируем Neo4j клиент
        neo4j_mock = MagicMock()
        neo4j_mock.run_query = AsyncMock()
        sender.neo4j = neo4j_mock
        
        # Подготавливаем тестовые данные
        test_keywords = [
            {"keyword": "keyword1", "frequency": 100},
            {"keyword": "keyword2", "frequency": 200}
        ]
        
        # Вызываем тестируемый метод
        await sender.send_keywords_to_neo4j(test_keywords)
        
        # Проверяем, что метод run_query Neo4j был вызван для каждого ключевого слова
        assert neo4j_mock.run_query.call_count == 2, "Метод run_query Neo4j должен быть вызван для каждого ключевого слова"
    else:
        # Для функции main
        
        # Мокируем Neo4j клиент
        neo4j_mock = MagicMock()
        neo4j_mock.run_query = AsyncMock()
        
        # Подготавливаем тестовые данные
        test_keywords = [
            {"keyword": "keyword1", "frequency": 100},
            {"keyword": "keyword2", "frequency": 200}
        ]
        
        # Мокируем функции
        with patch("keyword_sending_to_neo4j.get_neo4j", return_value=neo4j_mock) as mock_get_neo4j:
            # Вызываем тестируемую функцию
            from keyword_sending_to_neo4j import send_keywords_to_neo4j
            await send_keywords_to_neo4j(test_keywords)
            
            # Проверяем, что метод run_query Neo4j был вызван для каждого ключевого слова
            assert neo4j_mock.run_query.call_count == 2, "Метод run_query Neo4j должен быть вызван для каждого ключевого слова"


@pytest.mark.asyncio
async def test_keyword_sender_handles_empty_keywords():
    """
    Тест проверяет, что KeywordSender корректно обрабатывает случай отсутствия ключевых слов
    """
    if class_based:
        # Для класса KeywordSender
        
        # Создаем экземпляр KeywordSender
        sender = KeywordSender()
        
        # Мокируем методы
        sender.fetch_keywords_from_db = AsyncMock(return_value=[])
        sender.send_keywords_to_neo4j = AsyncMock()
        sender.log_warning = MagicMock()
        
        # Вызываем тестируемый метод
        await sender.run()
        
        # Проверяем, что метод получения ключевых слов был вызван
        sender.fetch_keywords_from_db.assert_called_once()
        
        # Проверяем, что метод отправки ключевых слов не был вызван
        sender.send_keywords_to_neo4j.assert_not_called()
        
        # Проверяем, что метод логирования предупреждения был вызван
        sender.log_warning.assert_called_once()
    else:
        # Для функции main
        
        # Мокируем функции
        with patch("keyword_sending_to_neo4j.fetch_keywords_from_db", new_callable=AsyncMock) as mock_fetch, \
             patch("keyword_sending_to_neo4j.send_keywords_to_neo4j", new_callable=AsyncMock) as mock_send, \
             patch("keyword_sending_to_neo4j.log_warning") as mock_log_warning:
             
            # Настраиваем мок-функции
            mock_fetch.return_value = []
            
            # Вызываем тестируемую функцию
            await main()
            
            # Проверяем, что функция получения ключевых слов была вызвана
            mock_fetch.assert_called_once()
            
            # Проверяем, что функция отправки ключевых слов не была вызвана
            mock_send.assert_not_called()
            
            # Проверяем, что функция логирования предупреждения была вызвана
            mock_log_warning.assert_called_once() 