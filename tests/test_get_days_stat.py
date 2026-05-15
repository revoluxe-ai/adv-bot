"""Тесты для получения текста со статистикой за несколько дней."""

import datetime
from unittest.mock import AsyncMock, patch

import pytest

from app.client_bot.user_interface.views.messages.adv_keyword_messages.backend.common_stat_data_manager import (
    CommonStatDataManager,
)
from app.modules.full_stat_adv_updater.types.full_adv_stat import SmallFullAdvStatPerDay
from app.modules.shop_runner.wb_statistic_manager.backend.types.common_card_stat import (
    CommonCardStat,
)

pytestmark = pytest.mark.unit


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


@pytest.mark.asyncio
async def test_days_stat_uses_all_campaign_clicks_for_organic() -> None:
    """Органика по сумме кликов комплекса; Кл(рек.кл/орг/пол) всегда, в т.ч. при rec_system_mode=False."""
    test_date = (datetime.datetime.now() - datetime.timedelta(days=1)).date()
    adv_setting_mock = AsyncMock()
    adv_setting_mock.rec_system_mode = False
    adv_setting_mock.plan_for_sales_for_day = None
    adv_setting_mock.target_price_for_order = None
    adv_setting_mock.max_price_for_order = None

    concatenated_adv_stat_result = [
        SmallFullAdvStatPerDay(
            date=test_date,
            views=100,
            clicks=10,  # all campaign clicks (auto + search)
            spend=100.0,
            added_to_cart=2,
            orders=1,
            sum_price=0.0,
        )
    ]
    common_card_stat = CommonCardStat(
        nmid=1,
        open_card=100,
        add_to_cart=5,
        orders=3,
        orders_sum=0,
        buy_outs=0,
    )
    common_card_stat.date = test_date

    text = await manager._get_days_static_text(
        adv_setting_mock,
        concatenated_adv_stat_result,
        [common_card_stat],
        auto_views_by_day={test_date: 90},
        keywords_views_by_day={test_date: 80},
        auto_clicks_by_day={test_date: 4},
        keywords_clicks_by_day={test_date: 1},
    )
    assert "Кл(рек.кл/орг/пол): 10/90/3" in text
