import asyncio
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.modules.shop_runner.shop_run_worker.redis_manager import RedisShopManager
from app.modules.shop_runner.wb_shop import WBShop


@pytest.mark.asyncio
async def test_wb_shop_run_calls_all_coroutines() -> None:
    """
    Тест проверяет, что метод run класса WBShop запускает необходимые корутины
    """
    # Создаем моки
    wb_api_mock = MagicMock()
    wb_api_mock.shop_id = "test_shop_id"
    redis_manager_mock = MagicMock(spec=RedisShopManager)
    redis_manager_mock.DEFAULT_TTL = 60
    redis_manager_mock.renew_shop_ttl = AsyncMock()

    # Создаем экземпляр WBShop
    wb_shop = WBShop(wb_api_mock, redis_manager_mock)

    # Создаем мок для CoroutinesManager (только активные методы)
    coroutines_manager_mock = MagicMock()
    coroutines_manager_mock.update_cpm_bid_in_search_advs = AsyncMock()

    # Подменяем создание CoroutinesManager
    with patch(
        "app.modules.shop_runner.wb_shop.CoroutinesManager",
        return_value=coroutines_manager_mock,
    ):
        # Подменяем asyncio.gather, чтобы мы могли проверить, какие корутины были переданы
        async def mock_gather(*args, **kwargs):
            # Создаем задачи для каждой корутины, но не запускаем их
            return list(args)

        # Применяем наш мок-метод
        with patch("asyncio.gather", side_effect=mock_gather):
            # Вызываем тестируемый метод
            await wb_shop.run()

            # Проверяем, что активный метод был вызван
            coroutines_manager_mock.update_cpm_bid_in_search_advs.assert_called_once()


@pytest.mark.asyncio
async def test_wb_shop_run_gathers_correct_number_of_coroutines():
    """
    Тест проверяет, что метод run класса WBShop передает правильное количество
    корутин в asyncio.gather
    """
    # Создаем моки
    wb_api_mock = MagicMock()
    wb_api_mock.shop_id = "test_shop_id"
    redis_manager_mock = MagicMock(spec=RedisShopManager)
    redis_manager_mock.DEFAULT_TTL = 60
    redis_manager_mock.renew_shop_ttl = AsyncMock()

    # Создаем экземпляр WBShop
    wb_shop = WBShop(wb_api_mock, redis_manager_mock)

    # Создаем мок для CoroutinesManager (только активные методы)
    coroutines_manager_mock = MagicMock()
    coroutines_manager_mock.update_cpm_bid_in_search_advs = AsyncMock()

    # Подменяем создание CoroutinesManager
    with patch(
        "app.modules.shop_runner.wb_shop.CoroutinesManager",
        return_value=coroutines_manager_mock,
    ):
        # Мокируем asyncio.gather для проверки количества аргументов
        with patch("asyncio.gather") as mock_gather:
            # Настраиваем mock_gather, чтобы он возвращал корутину
            mock_gather.return_value = asyncio.create_task(asyncio.sleep(0))

            # Вызываем тестируемый метод
            await wb_shop.run()

            # Проверяем, что gather был вызван ровно один раз
            mock_gather.assert_called_once()

            # Получаем все аргументы, с которыми был вызван gather
            call_args = mock_gather.call_args[0]

            # Проверяем, что gather был вызван с 2 аргументами (1 корутина + _alive_worker_run)
            assert len(call_args) == 2, f"asyncio.gather должен быть вызван с 2 аргументами, получено {len(call_args)}"

            # Проверяем, что только активный метод был вызван
            coroutines_manager_mock.update_cpm_bid_in_search_advs.assert_called_once()
