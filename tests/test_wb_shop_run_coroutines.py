import asyncio
from typing import Any
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

    # Создаем мок для CoroutinesManager
    coroutines_manager_mock = MagicMock()
    coroutines_manager_mock.update_advs_data_from_wb_to_pg = AsyncMock()
    coroutines_manager_mock.update_cards_data_from_wb_to_pg = AsyncMock()
    coroutines_manager_mock.update_cpm_bid = AsyncMock()
    coroutines_manager_mock.update_common_sale_stat = AsyncMock()
    coroutines_manager_mock.update_full_adv_stat = AsyncMock()
    coroutines_manager_mock.adv_settings_auto_update = AsyncMock()
    coroutines_manager_mock.update_top_key_in_advs = AsyncMock()
    coroutines_manager_mock.delete_keywords_from_wl_by_mean_auto_ctr = AsyncMock()
    coroutines_manager_mock.update_minus_phrases_in_advs = AsyncMock()
    coroutines_manager_mock.update_clusters_adv_stats_today = AsyncMock()
    coroutines_manager_mock.update_clusters_adv_stats_history = AsyncMock()

    # Подменяем создание CoroutinesManager
    with patch(
        "app.modules.shop_runner.wb_shop.CoroutinesManager",
        return_value=coroutines_manager_mock,
    ):
        # Подменяем asyncio.gather, чтобы мы могли проверить, какие корутины были переданы
        async def mock_gather(*args: Any, **kwargs: Any) -> list[Any]:
            # Создаем задачи для каждой корутины, но не запускаем их
            return [arg for arg in args]

        # Применяем наш мок-метод
        with patch("asyncio.gather", side_effect=mock_gather):
            # Вызываем тестируемый метод
            await wb_shop.run()

            # Проверяем, что все ожидаемые корутины были вызваны
            coroutines_manager_mock.update_advs_data_from_wb_to_pg.assert_called_once()
            coroutines_manager_mock.update_cards_data_from_wb_to_pg.assert_called_once()
            coroutines_manager_mock.update_cpm_bid.assert_called_once()
            coroutines_manager_mock.update_common_sale_stat.assert_called_once()
            coroutines_manager_mock.update_full_adv_stat.assert_called_once()
            coroutines_manager_mock.adv_settings_auto_update.assert_called_once()
            coroutines_manager_mock.update_top_key_in_advs.assert_called_once()
            coroutines_manager_mock.delete_keywords_from_wl_by_mean_auto_ctr.assert_called_once()
            coroutines_manager_mock.update_minus_phrases_in_advs.assert_called_once()
            coroutines_manager_mock.update_clusters_adv_stats_today.assert_called_once()
            coroutines_manager_mock.update_clusters_adv_stats_history.assert_called_once()

@pytest.mark.asyncio
async def test_wb_shop_run_gathers_correct_number_of_coroutines() -> None:
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

    # Создаем мок для CoroutinesManager
    coroutines_manager_mock = MagicMock()
    coroutines_manager_mock.update_advs_data_from_wb_to_pg = AsyncMock()
    coroutines_manager_mock.update_cards_data_from_wb_to_pg = AsyncMock()
    coroutines_manager_mock.update_cpm_bid = AsyncMock()
    coroutines_manager_mock.update_common_sale_stat = AsyncMock()
    coroutines_manager_mock.update_full_adv_stat = AsyncMock()
    coroutines_manager_mock.adv_settings_auto_update = AsyncMock()
    coroutines_manager_mock.update_top_key_in_advs = AsyncMock()
    coroutines_manager_mock.delete_keywords_from_wl_by_mean_auto_ctr = AsyncMock()
    coroutines_manager_mock.update_minus_phrases_in_advs = AsyncMock()
    coroutines_manager_mock.update_clusters_adv_stats_today = AsyncMock()
    coroutines_manager_mock.update_clusters_adv_stats_history = AsyncMock()

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

            # 12 корутин: 1 (_alive_worker_run) + 11 из CoroutinesManager
            assert (
                len(call_args) == 12
            ), f"asyncio.gather должен быть вызван с 12 аргументами, получено {len(call_args)}"

            # Проверяем, что все методы были вызваны по одному разу
            coroutines_manager_mock.update_advs_data_from_wb_to_pg.assert_called_once()
            coroutines_manager_mock.update_cards_data_from_wb_to_pg.assert_called_once()
            coroutines_manager_mock.update_cpm_bid.assert_called_once()
            coroutines_manager_mock.update_common_sale_stat.assert_called_once()
            coroutines_manager_mock.update_full_adv_stat.assert_called_once()
            coroutines_manager_mock.adv_settings_auto_update.assert_called_once()
            coroutines_manager_mock.update_top_key_in_advs.assert_called_once()
            coroutines_manager_mock.delete_keywords_from_wl_by_mean_auto_ctr.assert_called_once()
            coroutines_manager_mock.update_minus_phrases_in_advs.assert_called_once()
            coroutines_manager_mock.update_clusters_adv_stats_today.assert_called_once()
            coroutines_manager_mock.update_clusters_adv_stats_history.assert_called_once()