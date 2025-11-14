import datetime
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.modules.full_stat_adv_updater.types.full_adv_stat import SmallFullAdvStatPerDay
from app.modules.shop_runner.wb_stat_manager.clickhouse_manager import full_wb_adv_stat
from app.modules.shop_runner.wb_stat_manager.clickhouse_manager.full_wb_adv_stat import (
    get_daily_stats_by_last_days,
)


@pytest.mark.skip("Временно отключен для отладки")
@pytest.mark.asyncio
async def test_concatenate_stats():
    today = datetime.datetime.now().date()
    yesterday = today - datetime.timedelta(days=1)

    # Создаем тестовые данные для авто-рекламы
    result_auto = [
        SmallFullAdvStatPerDay(
            date=today,
            views=100,
            clicks=10,
            spend=1000,
            added_to_cart=5,
            orders=2,
            sum_price=2000,
        ),
        SmallFullAdvStatPerDay(
            date=yesterday,
            views=90,
            clicks=9,
            spend=900,
            added_to_cart=4,
            orders=1,
            sum_price=1000,
        ),
    ]

    # Создаем тестовые данные для аукционной рекламы
    result_auction = [
        SmallFullAdvStatPerDay(
            date=today,
            views=50,
            clicks=5,
            spend=500,
            added_to_cart=2,
            orders=1,
            sum_price=1000,
        ),
        SmallFullAdvStatPerDay(
            date=yesterday,
            views=40,
            clicks=4,
            spend=400,
            added_to_cart=1,
            orders=0,
            sum_price=0,
        ),
    ]

    # Объединяем статистику
    concat_result = full_wb_adv_stat.concatenate_stats(result_auto, result_auction)

    # Проверяем результаты
    assert isinstance(concat_result, list)
    assert len(concat_result) == 2  # Должно быть две записи (за сегодня и вчера)

    # Проверяем, что записи отсортированы по дате в обратном порядке
    assert concat_result[0].date == today
    assert concat_result[1].date == yesterday

    # Проверяем, что значения правильно суммируются для каждого дня
    today_stat = concat_result[0]
    assert today_stat.views == 150  # 100 + 50
    assert today_stat.clicks == 15  # 10 + 5
    assert today_stat.spend == 1500  # 1000 + 500
    assert today_stat.added_to_cart == 7  # 5 + 2
    assert today_stat.orders == 3  # 2 + 1
    assert today_stat.sum_price == 3000  # 2000 + 1000

    yesterday_stat = concat_result[1]
    assert yesterday_stat.views == 130  # 90 + 40
    assert yesterday_stat.clicks == 13  # 9 + 4
    assert yesterday_stat.spend == 1300  # 900 + 400
    assert yesterday_stat.added_to_cart == 5  # 4 + 1
    assert yesterday_stat.orders == 1  # 1 + 0
    assert yesterday_stat.sum_price == 1000  # 1000 + 0


@pytest.mark.skip("Временно отключен для отладки")
@pytest.mark.asyncio
async def test_get_daily_stats_by_last_days():
    test_adv_id = 25040169
    today = datetime.datetime.now()
    yesterday = today - datetime.timedelta(days=1)

    # Создаем мок для результата запроса к ClickHouse
    mock_result = MagicMock()
    mock_result.result_rows = [
        (
            yesterday.date(),
            100,
            10,
            1000.0,
            5,
            2,
            2000.0,
        ),  # date, views, clicks, spend, added_to_cart, orders, sum_price
        (today.date(), 200, 20, 2000.0, 10, 4, 4000.0),
    ]

    # Создаем мок для клиента ClickHouse
    mock_client = MagicMock()
    mock_client.query = AsyncMock(return_value=mock_result)
    mock_client.__aenter__ = AsyncMock(return_value=mock_client)
    mock_client.__aexit__ = AsyncMock(return_value=None)

    # Подменяем функцию получения клиента
    with patch(
        "app.modules.shop_runner.wb_stat_manager.clickhouse_manager.full_wb_adv_stat.get_clickhouse_client",
        return_value=mock_client,
    ):
        result = await get_daily_stats_by_last_days([test_adv_id], yesterday, today)

        # Проверяем результаты
        assert isinstance(result, list)
        assert len(result) == 2

        # Проверяем данные за вчера
        assert result[0].date == yesterday.date()
        assert result[0].views == 100
        assert result[0].clicks == 10
        assert result[0].spend == 1000.0
        assert result[0].added_to_cart == 5
        assert result[0].orders == 2
        assert result[0].sum_price == 2000.0

        # Проверяем данные за сегодня
        assert result[1].date == today.date()
        assert result[1].views == 200
        assert result[1].clicks == 20
        assert result[1].spend == 2000.0
        assert result[1].added_to_cart == 10
        assert result[1].orders == 4
        assert result[1].sum_price == 4000.0
