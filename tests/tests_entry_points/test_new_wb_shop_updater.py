from unittest.mock import AsyncMock, MagicMock, patch

import pytest

# Предполагаем, что в new_wb_shop_update_run.py есть функция main или класс ShopUpdater
# Адаптируйте импорт под реальную структуру модуля
try:
    from new_wb_shop_update_run import ShopUpdater

    class_based = True
except ImportError:
    from new_wb_shop_update_run import main

    class_based = False


@pytest.mark.asyncio
async def test_shop_updater_initialization():
    """
    Тест проверяет, что класс или функция ShopUpdater инициализируется корректно
    """
    if class_based:
        # Для класса ShopUpdater

        # Мокируем зависимости
        with patch("new_wb_shop_update_run.get_config") as mock_get_config, patch(
            "new_wb_shop_update_run.setup_logging"
        ) as mock_setup_logging:

            # Настраиваем мок-конфиг
            mock_get_config.return_value = {
                "db_connection": "test_connection_string",
                "redis_url": "redis://localhost:6379",
                "log_level": "INFO",
            }

            # Создаем экземпляр ShopUpdater
            updater = ShopUpdater()

            # Проверяем, что зависимости были вызваны
            mock_get_config.assert_called_once()
            mock_setup_logging.assert_called_once()

            # Проверяем, что атрибуты настроены правильно
            assert hasattr(
                updater, "config"
            ), "У объекта ShopUpdater должен быть атрибут config"
    else:
        # Для функции main

        # Мокируем функции инициализации
        with patch("new_wb_shop_update_run.initialize_db") as mock_init_db, patch(
            "new_wb_shop_update_run.initialize_redis"
        ) as mock_init_redis, patch(
            "new_wb_shop_update_run.setup_logging"
        ) as mock_setup_logging:

            # Настраиваем мок-функции
            mock_init_db.return_value = MagicMock()
            mock_init_redis.return_value = MagicMock()

            # Блокируем реальное выполнение
            with patch("asyncio.run"):
                # Импортируем модуль

                # Проверяем, что функции инициализации были вызваны
                mock_init_db.assert_called_once()
                mock_init_redis.assert_called_once()
                mock_setup_logging.assert_called_once()


@pytest.mark.asyncio
async def test_shop_updater_run_calls_required_functions():
    """
    Тест проверяет, что метод run вызывает необходимые функции
    """
    if class_based:
        # Для класса ShopUpdater

        # Создаем экземпляр ShopUpdater
        updater = ShopUpdater()

        # Мокируем методы, которые должны вызываться из run
        updater.get_shops = AsyncMock(return_value=["shop1", "shop2", "shop3"])
        updater.process_shop = AsyncMock()
        updater.cleanup = AsyncMock()

        # Вызываем тестируемый метод
        await updater.run()

        # Проверяем, что метод получения списка магазинов был вызван
        updater.get_shops.assert_called_once()

        # Проверяем, что метод обработки магазина был вызван для каждого магазина
        assert (
            updater.process_shop.call_count == 3
        ), "Метод process_shop должен вызываться для каждого магазина"

        # Проверяем, что метод очистки был вызван
        updater.cleanup.assert_called_once()
    else:
        # Для функции main

        # Мокируем функции
        with patch(
            "new_wb_shop_update_run.get_shops", new_callable=AsyncMock
        ) as mock_get_shops, patch(
            "new_wb_shop_update_run.process_shop", new_callable=AsyncMock
        ) as mock_process_shop, patch(
            "new_wb_shop_update_run.cleanup", new_callable=AsyncMock
        ) as mock_cleanup:

            # Настраиваем мок-функции
            mock_get_shops.return_value = ["shop1", "shop2", "shop3"]

            # Вызываем тестируемую функцию
            await main()

            # Проверяем, что функция получения списка магазинов была вызвана
            mock_get_shops.assert_called_once()

            # Проверяем, что функция обработки магазина была вызвана для каждого магазина
            assert (
                mock_process_shop.call_count == 3
            ), "Функция process_shop должна вызываться для каждого магазина"

            # Проверяем, что функция очистки была вызвана
            mock_cleanup.assert_called_once()


@pytest.mark.asyncio
async def test_shop_updater_processes_shops_in_parallel():
    """
    Тест проверяет, что обработка магазинов происходит параллельно
    """
    if class_based:
        # Для класса ShopUpdater

        # Создаем экземпляр ShopUpdater
        updater = ShopUpdater()

        # Мокируем методы
        updater.get_shops = AsyncMock(return_value=["shop1", "shop2", "shop3"])
        updater.process_shop = AsyncMock()
        updater.cleanup = AsyncMock()

        # Мокируем asyncio.gather для проверки параллельного запуска
        with patch("asyncio.gather") as mock_gather:
            # Вызываем тестируемый метод
            await updater.run()

            # Проверяем, что gather был вызван с правильным количеством аргументов
            assert (
                mock_gather.call_count == 1
            ), "asyncio.gather должен вызываться один раз"

            # Получаем аргументы вызова gather
            call_args = mock_gather.call_args[0]

            # Проверяем, что gather был вызван с правильным количеством корутин
            assert (
                len(call_args) == 3
            ), "asyncio.gather должен быть вызван с 3 аргументами"
    else:
        # Для функции main

        # Мокируем функции
        with patch(
            "new_wb_shop_update_run.get_shops", new_callable=AsyncMock
        ) as mock_get_shops, patch(
            "new_wb_shop_update_run.process_shop", new_callable=AsyncMock
        ) as mock_process_shop, patch(
            "new_wb_shop_update_run.cleanup", new_callable=AsyncMock
        ) as mock_cleanup, patch(
            "asyncio.gather"
        ) as mock_gather:

            # Настраиваем мок-функции
            mock_get_shops.return_value = ["shop1", "shop2", "shop3"]
            mock_gather.return_value = ["result1", "result2", "result3"]

            # Вызываем тестируемую функцию
            await main()

            # Проверяем, что gather был вызван с правильным количеством аргументов
            assert (
                mock_gather.call_count == 1
            ), "asyncio.gather должен вызываться один раз"

            # Получаем аргументы вызова gather
            call_args = mock_gather.call_args[0]

            # Проверяем, что gather был вызван с правильным количеством корутин
            assert (
                len(call_args) == 3
            ), "asyncio.gather должен быть вызван с 3 аргументами"
