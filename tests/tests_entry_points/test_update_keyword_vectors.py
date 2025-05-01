from unittest.mock import AsyncMock, patch, MagicMock

import numpy as np
import pytest

# Предполагаем, что в run_update_keyword_vectors_in_redis.py есть функция main или класс VectorUpdater
# Адаптируйте импорт под реальную структуру модуля
try:
    from run_update_keyword_vectors_in_redis import VectorUpdater

    class_based = True
except ImportError:
    from run_update_keyword_vectors_in_redis import main

    class_based = False


@pytest.mark.asyncio(loop_scope="session")
async def test_vector_updater_initialization():
    """
    Тест проверяет, что класс или функция VectorUpdater инициализируется корректно
    """
    if class_based:
        # Для класса VectorUpdater

        # Мокируем зависимости
        with patch(
            "run_update_keyword_vectors_in_redis.get_config"
        ) as mock_get_config, patch(
            "run_update_keyword_vectors_in_redis.setup_logging"
        ) as mock_setup_logging, patch(
            "run_update_keyword_vectors_in_redis.init_redis"
        ) as mock_init_redis, patch(
            "run_update_keyword_vectors_in_redis.init_neo4j"
        ) as mock_init_neo4j:

            # Настраиваем мок-конфиг
            mock_get_config.return_value = {
                "redis_url": "redis://localhost:6379",
                "neo4j_uri": "bolt://localhost:7687",
                "neo4j_user": "neo4j",
                "neo4j_password": "password",
                "log_level": "INFO",
            }

            # Создаем экземпляр VectorUpdater
            updater = VectorUpdater()

            # Проверяем, что зависимости были вызваны
            mock_get_config.assert_called_once()
            mock_setup_logging.assert_called_once()
            mock_init_redis.assert_called_once()
            mock_init_neo4j.assert_called_once()

            # Проверяем, что атрибуты настроены правильно
            assert hasattr(
                updater, "config"
            ), "У объекта VectorUpdater должен быть атрибут config"
    else:
        # Для функции main

        # Мокируем функции инициализации
        with patch(
            "run_update_keyword_vectors_in_redis.setup_logging"
        ) as mock_setup_logging, patch(
            "run_update_keyword_vectors_in_redis.load_config"
        ) as mock_load_config, patch(
            "run_update_keyword_vectors_in_redis.init_redis"
        ) as mock_init_redis, patch(
            "run_update_keyword_vectors_in_redis.init_neo4j"
        ) as mock_init_neo4j:

            # Настраиваем мок-функции
            mock_load_config.return_value = {
                "redis_url": "redis://localhost:6379",
                "neo4j_uri": "bolt://localhost:7687",
                "neo4j_user": "neo4j",
                "neo4j_password": "password",
                "log_level": "INFO",
            }
            mock_init_redis.return_value = MagicMock()
            mock_init_neo4j.return_value = MagicMock()

            # Блокируем реальное выполнение
            with patch("asyncio.run"):
                # Импортируем модуль

                # Проверяем, что функции инициализации были вызваны
                mock_setup_logging.assert_called_once()
                mock_load_config.assert_called_once()
                mock_init_redis.assert_called_once()
                mock_init_neo4j.assert_called_once()


@pytest.mark.asyncio(loop_scope="session")
async def test_vector_updater_fetches_keywords_from_neo4j():
    """
    Тест проверяет, что метод run получает ключевые слова из Neo4j
    """
    if class_based:
        # Для класса VectorUpdater

        # Создаем экземпляр VectorUpdater
        updater = VectorUpdater()

        # Мокируем методы, которые должны вызываться из run
        test_keywords = [
            {"keyword": "keyword1", "vector": [0.1, 0.2, 0.3]},
            {"keyword": "keyword2", "vector": [0.4, 0.5, 0.6]},
        ]
        updater.fetch_keywords_from_neo4j = AsyncMock(return_value=test_keywords)
        updater.update_vectors_in_redis = AsyncMock()

        # Вызываем тестируемый метод
        await updater.run()

        # Проверяем, что метод получения ключевых слов был вызван
        updater.fetch_keywords_from_neo4j.assert_called_once()

        # Проверяем, что метод обновления векторов был вызван с правильными аргументами
        updater.update_vectors_in_redis.assert_called_once_with(test_keywords)
    else:
        # Для функции main

        # Мокируем функции
        test_keywords = [
            {"keyword": "keyword1", "vector": [0.1, 0.2, 0.3]},
            {"keyword": "keyword2", "vector": [0.4, 0.5, 0.6]},
        ]
        with patch(
            "run_update_keyword_vectors_in_redis.fetch_keywords_from_neo4j",
            new_callable=AsyncMock,
        ) as mock_fetch, patch(
            "run_update_keyword_vectors_in_redis.update_vectors_in_redis",
            new_callable=AsyncMock,
        ) as mock_update:

            # Настраиваем мок-функции
            mock_fetch.return_value = test_keywords

            # Вызываем тестируемую функцию
            await main()

            # Проверяем, что функция получения ключевых слов была вызвана
            mock_fetch.assert_called_once()

            # Проверяем, что функция обновления векторов была вызвана с правильными аргументами
            mock_update.assert_called_once_with(test_keywords)


@pytest.mark.asyncio(loop_scope="session")
async def test_vector_updater_updates_redis():
    """
    Тест проверяет, что метод update_vectors_in_redis корректно обновляет векторы в Redis
    """
    if class_based:
        # Для класса VectorUpdater

        # Создаем экземпляр VectorUpdater
        updater = VectorUpdater()

        # Мокируем Redis клиент
        redis_mock = MagicMock()
        updater.redis = redis_mock

        # Подготавливаем тестовые данные
        test_keywords = [
            {"keyword": "keyword1", "vector": np.array([0.1, 0.2, 0.3])},
            {"keyword": "keyword2", "vector": np.array([0.4, 0.5, 0.6])},
        ]

        # Вызываем тестируемый метод
        await updater.update_vectors_in_redis(test_keywords)

        # Проверяем, что метод set Redis был вызван для каждого ключевого слова
        assert (
            redis_mock.set.call_count == 2
        ), "Метод set Redis должен быть вызван для каждого ключевого слова"
    else:
        # Для функции main

        # Мокируем Redis клиент
        redis_mock = MagicMock()

        # Подготавливаем тестовые данные
        test_keywords = [
            {"keyword": "keyword1", "vector": np.array([0.1, 0.2, 0.3])},
            {"keyword": "keyword2", "vector": np.array([0.4, 0.5, 0.6])},
        ]

        # Мокируем функции
        with patch(
            "run_update_keyword_vectors_in_redis.get_redis", return_value=redis_mock
        ) as mock_get_redis:
            # Вызываем тестируемую функцию
            from run_update_keyword_vectors_in_redis import update_vectors_in_redis

            await update_vectors_in_redis(test_keywords)

            # Проверяем, что метод set Redis был вызван для каждого ключевого слова
            assert (
                redis_mock.set.call_count == 2
            ), "Метод set Redis должен быть вызван для каждого ключевого слова"


@pytest.mark.asyncio(loop_scope="session")
async def test_vector_updater_handles_empty_keywords():
    """
    Тест проверяет, что VectorUpdater корректно обрабатывает случай отсутствия ключевых слов
    """
    if class_based:
        # Для класса VectorUpdater

        # Создаем экземпляр VectorUpdater
        updater = VectorUpdater()

        # Мокируем методы
        updater.fetch_keywords_from_neo4j = AsyncMock(return_value=[])
        updater.update_vectors_in_redis = AsyncMock()
        updater.log_warning = MagicMock()

        # Вызываем тестируемый метод
        await updater.run()

        # Проверяем, что метод получения ключевых слов был вызван
        updater.fetch_keywords_from_neo4j.assert_called_once()

        # Проверяем, что метод обновления векторов не был вызван
        updater.update_vectors_in_redis.assert_not_called()

        # Проверяем, что метод логирования предупреждения был вызван
        updater.log_warning.assert_called_once()
    else:
        # Для функции main

        # Мокируем функции
        with patch(
            "run_update_keyword_vectors_in_redis.fetch_keywords_from_neo4j",
            new_callable=AsyncMock,
        ) as mock_fetch, patch(
            "run_update_keyword_vectors_in_redis.update_vectors_in_redis",
            new_callable=AsyncMock,
        ) as mock_update, patch(
            "run_update_keyword_vectors_in_redis.log_warning"
        ) as mock_log_warning:

            # Настраиваем мок-функции
            mock_fetch.return_value = []

            # Вызываем тестируемую функцию
            await main()

            # Проверяем, что функция получения ключевых слов была вызвана
            mock_fetch.assert_called_once()

            # Проверяем, что функция обновления векторов не была вызвана
            mock_update.assert_not_called()

            # Проверяем, что функция логирования предупреждения была вызвана
            mock_log_warning.assert_called_once()
