import asyncio
from unittest.mock import AsyncMock, patch

import pytest

from app.modules.shop_runner.wb_shop import WBShop


@pytest.mark.asyncio(loop_scope="session")
async def test_wb_shop_run_calls_all_coroutines() -> None:
    """
    Тест проверяет, что метод _run класса WBShop запускает необходимые корутины
    """
    # Создаем экземпляр WBShop
    shop_id = "test_shop_id"
    wb_cabinet_original_id = 12345
    wb_shop = WBShop(shop_id, wb_cabinet_original_id)

    # Мокируем все методы, которые должны вызываться из _run
    wb_shop.parsing_keywords_run = AsyncMock()
    wb_shop.update_advs_data_from_wb_to_pg = AsyncMock()
    wb_shop.update_cards_data_from_wb_to_pf = AsyncMock()
    wb_shop.update_cpm_run = AsyncMock()
    wb_shop.update_common_sale_stat = AsyncMock()
    wb_shop.update_full_stat_run = AsyncMock()

    # Подменяем asyncio.gather, чтобы мы могли проверить, какие корутины были переданы
    original_gather = asyncio.gather

    async def mock_gather(*args, **kwargs):
        # Создаем задачи для каждой корутины, но не запускаем их
        return [arg for arg in args]

    # Применяем наш мок-метод
    with patch("asyncio.gather", side_effect=mock_gather):
        # Вызываем тестируемый метод
        await wb_shop._run()

        # Проверяем, что _update_access был вызван

        # Проверяем, что все ожидаемые корутины были вызваны
        wb_shop.parsing_keywords_run.assert_called_once()
        wb_shop.update_advs_data_from_wb_to_pg.assert_called_once()
        wb_shop.update_cards_data_from_wb_to_pf.assert_called_once()
        wb_shop.update_cpm_run.assert_called_once()
        wb_shop.update_common_sale_stat.assert_called_once()
        wb_shop.update_full_stat_run.assert_called_once()


@pytest.mark.asyncio(loop_scope="session")
async def test_wb_shop_run_gathers_correct_number_of_coroutines():
    """
    Тест проверяет, что метод _run класса WBShop передает правильное количество
    корутин в asyncio.gather
    """
    # Создаем экземпляр WBShop
    shop_id = "test_shop_id"
    wb_cabinet_original_id = 12345
    wb_shop = WBShop(shop_id, wb_cabinet_original_id)

    # Мокируем все методы, которые должны вызываться из _run
    wb_shop.parsing_keywords_run = AsyncMock()
    wb_shop.update_advs_data_from_wb_to_pg = AsyncMock()
    wb_shop.update_cards_data_from_wb_to_pf = AsyncMock()
    wb_shop.update_cpm_run = AsyncMock()
    wb_shop.update_common_sale_stat = AsyncMock()
    wb_shop.update_full_stat_run = AsyncMock()

    # Мокируем asyncio.gather для проверки количества аргументов
    with patch("asyncio.gather") as mock_gather:
        # Настраиваем mock_gather, чтобы он возвращал корутину
        mock_gather.return_value = asyncio.create_task(asyncio.sleep(0))

        # Вызываем тестируемый метод
        await wb_shop._run()

        # Проверяем, что _update_access был вызван

        # Проверяем, что gather был вызван ровно один раз
        mock_gather.assert_called_once()

        # Получаем все аргументы, с которыми был вызван gather
        call_args = mock_gather.call_args[0]

        # Проверяем, что gather был вызван с 6 аргументами (по количеству методов)
        assert (
            len(call_args) == 6
        ), f"asyncio.gather должен быть вызван с 6 аргументами, получено {len(call_args)}"

        # Проверяем, что все методы были вызваны по одному разу
        wb_shop.parsing_keywords_run.assert_called_once()
        wb_shop.update_advs_data_from_wb_to_pg.assert_called_once()
        wb_shop.update_cards_data_from_wb_to_pf.assert_called_once()
        wb_shop.update_cpm_run.assert_called_once()
        wb_shop.update_common_sale_stat.assert_called_once()
        wb_shop.update_full_stat_run.assert_called_once()
