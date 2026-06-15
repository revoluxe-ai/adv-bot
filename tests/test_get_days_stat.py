"""Тесты для получения текста со статистикой за несколько дней."""

import datetime
from unittest.mock import AsyncMock, patch

import pytest

from app.client_bot.user_interface.views.messages.adv_keyword_messages.backend.common_stat_data_manager import (
    CommonStatDataManager,
    DaysStatTextOptions,
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
        patch.object(
            manager,
            "_load_daily_stat_data",
            new=AsyncMock(
                return_value=(
                    [stat_mock],
                    [common_card_stat_mock],
                    {test_date: 100},
                    {test_date: 0},
                    {test_date: 10},
                    {test_date: 1},
                    {test_date: 7},
                )
            ),
        ),
        patch(
            f"{mod}.is_rec_system_shelf_mode_operational",
            new=AsyncMock(return_value=False),
        ),
    ):
        text = await manager.get_days_static_text(adv_setting_mock, last_days)
        assert isinstance(text, str)
        assert len(text) > 0
        assert "Кл(рек.кл/орг/пол): 7/90/9 (106)" in text
        assert " ⚠" not in text
        print("\n", text)


@pytest.mark.asyncio
async def test_days_stat_uses_all_campaign_clicks_for_organic() -> None:
    """Органика по сумме кликов комплекса в строке Кл(...)."""
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
            cluster_keyword_clicks_by_day={test_date: 15},
        )
    assert "Кл(рек.кл/орг/пол): 15/90/3 (108)" in text


@pytest.mark.asyncio
async def test_days_stat_warning_suffix_only_on_today_line() -> None:
    """Кл(...) на каждой строке; ⚠ только у сегодня при полках и рек < полки."""
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
            cluster_keyword_clicks_by_day={today_d: 3, yesterday_d: 50},
        )

    assert text.count("Кл(рек.кл/орг/пол)") == 2
    lines = [ln for ln in text.splitlines() if ln.strip()]
    today_lines = [ln for ln in lines if ln.startswith(today_d.strftime("%d.%m.%Y"))]
    yesterday_lines = [ln for ln in lines if ln.startswith(yesterday_d.strftime("%d.%m.%Y"))]
    assert len(today_lines) == 1
    assert "Кл(рек.кл/орг/пол)" in today_lines[0]
    assert " ⚠" in today_lines[0]
    assert len(yesterday_lines) == 1
    assert "Кл(рек.кл/орг/пол)" in yesterday_lines[0]
    assert " ⚠" not in yesterday_lines[0]


@pytest.mark.asyncio
async def test_days_stat_formats_organic_percent_without_forecast() -> None:
    """Строка по дню для отдельного экрана содержит проценты органики и без прогноза."""
    test_date = datetime.datetime.now().date() - datetime.timedelta(days=1)

    stat_mock = SmallFullAdvStatPerDay(
        date=test_date,
        views=100,
        clicks=10,
        spend=100.0,
        added_to_cart=270,
        orders=53,
        sum_price=0.0,
    )
    common_card_stat = CommonCardStat(
        nmid=1,
        open_card=100,
        add_to_cart=347,
        orders=87,
        orders_sum=0,
        buy_outs=0,
    )
    common_card_stat.date = test_date

    line = manager._format_day_row(
        date_value=test_date,
        common_stat=common_card_stat,
        adv_stat=stat_mock,
        auto_views_by_day={test_date: 0},
        keywords_views_by_day={test_date: 0},
        auto_clicks_by_day={test_date: 0},
        keywords_clicks_by_day={test_date: 0},
        cluster_keyword_clicks_by_day={test_date: 0},
        shelves_operational=False,
        options=DaysStatTextOptions(
            show_forecast=False,
            show_clicks_warning=False,
            show_organic_pct=True,
        ),
        today_date=datetime.datetime.now().date(),
    )

    assert "Корз.:347(77, 22% орг.)" in line
    assert "Зак.:87(34, 39% орг.)шт." in line
    assert " ⚠" not in line
    assert "(" in line


@pytest.mark.asyncio
async def test_page_to_date_range_and_total_pages() -> None:
    """Проверяем расчёт окон по 14 дней и количество страниц по самой ранней дате."""
    today = datetime.datetime.now().date()
    start_date, end_date = manager.page_to_date_range(2, 14)
    assert start_date == today - datetime.timedelta(days=27)
    assert end_date == today - datetime.timedelta(days=14)

    adv_setting_mock = AsyncMock()
    adv_setting_mock.nmids = [1]
    adv_setting_mock.adv_id = 2
    adv_setting_mock.search_adv_id = None

    with patch.object(
        manager,
        "get_earliest_stat_date",
        new=AsyncMock(return_value=today - datetime.timedelta(days=27)),
    ):
        total_pages = await manager.get_total_pages(adv_setting_mock, page_size=14)

    assert total_pages == 2
