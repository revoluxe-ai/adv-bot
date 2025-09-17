import asyncio
from unittest.mock import AsyncMock, Mock, patch

import pytest

from app.modules.shop_runner.modules.wb_api import WBApi
from app.modules.shop_runner.shop_run_worker.redis_manager import RedisShopManager
from app.modules.shop_runner.wb_shop import WBShop


async def mock_infinite_run():
    """Мок-функция для имитации бесконечного выполнения корутины"""
    while True:
        await asyncio.sleep(0.1)


@pytest.mark.asyncio
async def test_wb_shop_run_calls_all_coroutines():
    """
    Тест проверяет, что метод run класса WBShop запускает необходимые корутины
    """
    # Создаем моки для зависимостей
    mock_wb_api = Mock(spec=WBApi)
    mock_wb_api.shop_id = "test_shop_id"
    mock_redis_manager = Mock(spec=RedisShopManager)
    mock_redis_manager.DEFAULT_TTL = 300

    # Создаем экземпляр WBShop
    wb_shop = WBShop(mock_wb_api, mock_redis_manager)

    # Мокируем метод _alive_worker_run
    wb_shop._alive_worker_run = AsyncMock()  # type: ignore[method-assign]

    # Подменяем asyncio.gather, чтобы мы могли проверить, какие корутины были переданы
    async def mock_gather(*args, **kwargs) -> list:  # type: ignore[misc]
        # Создаем задачи для каждой корутины, но не запускаем их
        return [arg for arg in args]

    # Применяем наш мок-метод
    with patch("asyncio.gather", side_effect=mock_gather):
        with patch(
            "app.modules.shop_runner.wb_shop.CoroutinesManager"
        ) as mock_coroutines_manager:
            # Настраиваем мок CoroutinesManager
            mock_manager_instance = mock_coroutines_manager.return_value
            mock_manager_instance.parsing_keywords_run = AsyncMock()
            mock_manager_instance.update_advs_data_from_wb_to_pg = AsyncMock()
            mock_manager_instance.update_cards_data_from_wb_to_pg = AsyncMock()
            mock_manager_instance.update_cpm_bid = AsyncMock()
            mock_manager_instance.update_common_sale_stat = AsyncMock()
            mock_manager_instance.update_full_adv_stat = AsyncMock()
            mock_manager_instance.adv_settings_auto_update = AsyncMock()
            mock_manager_instance.update_top_key_in_advs = AsyncMock()

            # Вызываем тестируемый метод
            await wb_shop.run()

            # Проверяем, что CoroutinesManager был создан с правильным аргументом
            mock_coroutines_manager.assert_called_once_with(mock_wb_api)

            # Проверяем, что _alive_worker_run был вызван
            wb_shop._alive_worker_run.assert_called_once()

            # Проверяем, что все методы CoroutinesManager были вызваны
            mock_manager_instance.parsing_keywords_run.assert_called_once()
            mock_manager_instance.update_advs_data_from_wb_to_pg.assert_called_once()
            mock_manager_instance.update_cards_data_from_wb_to_pg.assert_called_once()
            mock_manager_instance.update_cpm_bid.assert_called_once()
            mock_manager_instance.update_common_sale_stat.assert_called_once()
            mock_manager_instance.update_full_adv_stat.assert_called_once()
            mock_manager_instance.adv_settings_auto_update.assert_called_once()
            mock_manager_instance.update_top_key_in_advs.assert_called_once()


@pytest.mark.asyncio
async def test_wb_shop_run_gathers_correct_number_of_coroutines() -> None:
    """
    Тест проверяет, что метод run класса WBShop передает правильное количество
    корутин в asyncio.gather
    """
    # Создаем моки для зависимостей
    mock_wb_api = Mock(spec=WBApi)
    mock_wb_api.shop_id = "test_shop_id"
    mock_redis_manager = Mock(spec=RedisShopManager)
    mock_redis_manager.DEFAULT_TTL = 300

    # Создаем экземпляр WBShop
    wb_shop = WBShop(mock_wb_api, mock_redis_manager)

    # Мокируем метод _alive_worker_run
    wb_shop._alive_worker_run = AsyncMock()  # type: ignore[method-assign]

    # Мокируем asyncio.gather для проверки количества аргументов
    with patch("asyncio.gather") as mock_gather:
        with patch(
            "app.modules.shop_runner.wb_shop.CoroutinesManager"
        ) as mock_coroutines_manager:
            # Настраиваем mock_gather, чтобы он возвращал корутину
            mock_gather.return_value = asyncio.create_task(asyncio.sleep(0))

            # Настраиваем мок CoroutinesManager
            mock_manager_instance = mock_coroutines_manager.return_value
            mock_manager_instance.parsing_keywords_run = AsyncMock()
            mock_manager_instance.update_advs_data_from_wb_to_pg = AsyncMock()
            mock_manager_instance.update_cards_data_from_wb_to_pg = AsyncMock()
            mock_manager_instance.update_cpm_bid = AsyncMock()
            mock_manager_instance.update_common_sale_stat = AsyncMock()
            mock_manager_instance.update_full_adv_stat = AsyncMock()
            mock_manager_instance.adv_settings_auto_update = AsyncMock()
            mock_manager_instance.update_top_key_in_advs = AsyncMock()

            # Вызываем тестируемый метод
            await wb_shop.run()

            # Проверяем, что gather был вызван ровно один раз
            mock_gather.assert_called_once()

            # Получаем все аргументы, с которыми был вызван gather
            call_args = mock_gather.call_args[0]

            # Проверяем, что gather был вызван с 9 аргументами (1 _alive_worker_run + 8 методов CoroutinesManager)
            assert len(call_args) == 9, (
                f"asyncio.gather должен быть вызван с 9 аргументами, получено {len(call_args)}"
            )


@pytest.mark.asyncio
async def test_wb_shop_alive_worker_run() -> None:
    """
    Тест проверяет работу метода _alive_worker_run
    """
    # Создаем моки для зависимостей
    mock_wb_api = Mock(spec=WBApi)
    mock_wb_api.shop_id = "test_shop_id"
    mock_redis_manager = Mock(spec=RedisShopManager)
    mock_redis_manager.DEFAULT_TTL = 300
    mock_redis_manager.renew_shop_ttl = AsyncMock()

    # Создаем экземпляр WBShop
    wb_shop = WBShop(mock_wb_api, mock_redis_manager)

    # Создаем задачу для тестирования _alive_worker_run
    task = asyncio.create_task(wb_shop._alive_worker_run())  # type: ignore[no-untyped-call]

    # Подождем немного, чтобы убедиться, что метод работает
    await asyncio.sleep(0.2)

    # Отменяем задачу
    task.cancel()

    # Ждем завершения отмены
    try:
        await task
    except asyncio.CancelledError:
        pass

    # Проверяем, что renew_shop_ttl был вызван хотя бы один раз
    mock_redis_manager.renew_shop_ttl.assert_called_with("test_shop_id")
