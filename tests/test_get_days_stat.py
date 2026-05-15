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
    common_card_stat_mock.date = test_date

    mod = (
        "app.client_bot.user_interface.views.messages.adv_keyword_messages.backend."
        "common_stat_data_manager"
    )
    with (
        patch(
            f"{mod}.full_wb_adv_stat.get_daily_stats_by_last_days",
            new=AsyncMock(return_value=[stat_mock]),
        ),
        patch(
            f"{mod}.common_stat_manager.get_stats_by_days",
            new=AsyncMock(return_value=[common_card_stat_mock]),
        ),
        patch(
            f"{mod}.full_wb_adv_stat.get_keywords_views_by_days",
            new=AsyncMock(return_value={}),
        ),
        patch(
            f"{mod}.full_wb_adv_stat.get_keywords_clicks_by_days",
            new=AsyncMock(return_value={}),
        ),
        patch(
            f"{mod}.is_rec_system_shelf_mode_operational",
            new=AsyncMock(return_value=False),
        ),
    ):
        text = await manager.get_days_static_text(adv_setting_mock, last_days)
        assert isinstance(text, str)
        assert len(text) > 0
        assert "Кл(рек.кл/орг/пол)" not in text
        print("\n", text)


@pytest.mark.asyncio
async def test_days_stat_uses_all_campaign_clicks_for_organic_today_only() -> None:
    """Блок Кл только за сегодня; органика по сумме кликов комплекса."""
    test_date = datetime.datetime.now().date()
    adv_setting_mock = AsyncMock()
    adv_setting_mock.rec_system_mode = False
    adv_setting_mock.active_status = "started"
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

    mod = (
        "app.client_bot.user_interface.views.messages.adv_keyword_messages.backend."
        "common_stat_data_manager"
    )
    with patch(
        f"{mod}.is_rec_system_shelf_mode_operational",
        new=AsyncMock(return_value=False),
    ):
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


@pytest.mark.asyncio
async def test_days_stat_clicks_and_warning_only_on_today_line() -> None:
    """Вчера без Кл(...); сегодня с Кл и ⚠ при полках и рек < полки."""
    today_d = datetime.datetime.now().date()
    yesterday_d = today_d - datetime.timedelta(days=1)

    adv_setting_mock = AsyncMock()
    adv_setting_mock.plan_for_sales_for_day = None
    adv_setting_mock.target_price_for_order = None
    adv_setting_mock.max_price_for_order = None

    stats_today = SmallFullAdvStatPerDay(
        date=today_d,
        views=100,
        clicks=5,
        spend=10.0,
        added_to_cart=1,
        orders=1,
        sum_price=0.0,
    )
    stats_yesterday = SmallFullAdvStatPerDay(
        date=yesterday_d,
        views=100,
        clicks=99,
        spend=10.0,
        added_to_cart=1,
        orders=1,
        sum_price=0.0,
    )

    cc_today = CommonCardStat(
        nmid=1, open_card=100, add_to_cart=2, orders=1, orders_sum=0, buy_outs=0
    )
    cc_yesterday = CommonCardStat(
        nmid=1, open_card=100, add_to_cart=2, orders=1, orders_sum=0, buy_outs=0
    )
    cc_today.date = today_d
    cc_yesterday.date = yesterday_d

    mod = (
        "app.client_bot.user_interface.views.messages.adv_keyword_messages.backend."
        "common_stat_data_manager"
    )
    with patch(
        f"{mod}.is_rec_system_shelf_mode_operational",
        new=AsyncMock(return_value=True),
    ):
        text = await manager._get_days_static_text(
            adv_setting_mock,
            [stats_yesterday, stats_today],
            [cc_yesterday, cc_today],
            auto_views_by_day={today_d: 0, yesterday_d: 0},
            keywords_views_by_day={today_d: 0, yesterday_d: 0},
            auto_clicks_by_day={today_d: 50, yesterday_d: 1},
            keywords_clicks_by_day={today_d: 10, yesterday_d: 0},
        )

    assert text.count("Кл(рек.кл/орг/пол)") == 1
    lines = [ln for ln in text.splitlines() if ln.strip()]
    today_lines = [ln for ln in lines if ln.startswith(today_d.strftime("%d.%m.%Y"))]
    yesterday_lines = [ln for ln in lines if ln.startswith(yesterday_d.strftime("%d.%m.%Y"))]
    assert len(today_lines) == 1
    assert "Кл(рек.кл/орг/пол)" in today_lines[0]
    assert " ⚠" in today_lines[0]
    assert len(yesterday_lines) == 1
    assert "Кл(рек.кл/орг/пол)" not in yesterday_lines[0]
