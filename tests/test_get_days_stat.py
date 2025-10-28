"""Тесты для получения текста со статистикой за несколько дней."""

import datetime
from unittest.mock import AsyncMock, patch

import pytest

from app.client_bot.user_interface.views.messages.adv_keyword_messages.backend.common_stat_data_manager import \
    CommonStatDataManager
from app.modules.full_stat_adv_updater.types.full_adv_stat import SmallFullAdvStatPerDay
from app.modules.shop_runner.wb_statistic_manager.backend.types.common_card_stat import (
    CommonCardStat,
)


manager = CommonStatDataManager()


@pytest.mark.asyncio
async def test_get_days_stat_text(adv_setting_mock: AsyncMock) -> None:
    """Тестируем получение текста со статистикой за несколько дней."""

    last_days = 2
    adv_setting_mock.adv_id = 123456
    adv_setting_mock.search_adv_id = 789012

    # Создаем моки для статистики (берем вчерашнюю дату, чтобы всегда попадать в диапазон last_days)
    test_date = (datetime.datetime.now() - datetime.timedelta(days=1)).date()
    stat_mock = SmallFullAdvStatPerDay(
        date=test_date,
        views=100,
        clicks=10,
        spend=1000,
        added_to_cart=5,
        orders=2,
        sum_price=2000,
    )

    common_card_stat_mock = CommonCardStat(
        nmid=123456,
        open_card=100,
        add_to_cart=5,
        orders=2,
        orders_sum=2000,
        buy_outs=0.5,
    )
    common_card_stat_mock.date = datetime.datetime.combine(test_date, datetime.time.min)

    # Подменяем методы, которые делают запросы к базам данных
    with (
        patch(
            "app.client_bot.user_interface.views.messages.adv_keyword_messages.backend.common_stat_data_manager"
            ".full_wb_adv_stat.get_daily_stats_by_last_days",
            new=AsyncMock(return_value=[stat_mock]),
        ),
        patch(
            "app.client_bot.user_interface.views.messages.adv_keyword_messages.backend.common_stat_data_manager"
            ".common_stat_manager.get_stats_by_days",
            new=AsyncMock(return_value=[common_card_stat_mock]),
        ),
    ):
        text = await manager.get_days_static_text(adv_setting_mock, last_days)
        assert isinstance(text, str)
        assert len(text) > 0
        print("\n", text)
