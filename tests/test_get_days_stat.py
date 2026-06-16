"""Тесты для получения текста со статистикой за несколько дней."""

import datetime
from unittest.mock import AsyncMock, patch

import pytest

from app.client_bot.user_interface.views.messages.adv_keyword_messages.backend.common_stat_data_manager import (
    CommonStatDataManager,
    DaysStatTextOptions,
)
from app.client_bot.user_interface.views import keyboards
from app.client_bot.user_interface.views import callbacks
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
    assert start_date is not None and end_date is not None
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


def test_page_to_date_range_returns_none_when_window_before_earliest() -> None:
    """Страница не должна открывать окно раньше earliest_date."""
    today = datetime.date(2026, 6, 16)
    earliest = datetime.date(2026, 6, 3)

    page1 = manager.page_to_date_range(1, 14, earliest_date=earliest, today=today)
    assert page1 == (datetime.date(2026, 6, 3), today)

    page2 = manager.page_to_date_range(2, 14, earliest_date=earliest, today=today)
    assert page2 is None


@pytest.mark.asyncio
async def test_days_page_second_window_loads_when_earliest_allows() -> None:
    """Вторая страница должна грузить данные, если окно попадает в историю РК."""
    today = datetime.datetime.now().date()
    earliest = today - datetime.timedelta(days=27)

    adv_setting_mock = AsyncMock()
    adv_setting_mock.nmids = [1]
    adv_setting_mock.adv_id = 2
    adv_setting_mock.search_adv_id = 3
    adv_setting_mock.plan_for_sales_for_day = None
    adv_setting_mock.target_price_for_order = None
    adv_setting_mock.max_price_for_order = None

    page2_start, page2_end = manager.page_to_date_range(2, 14, earliest_date=earliest)
    assert page2_start is not None and page2_end is not None

    stat = SmallFullAdvStatPerDay(
        date=page2_end,
        views=100,
        clicks=10,
        spend=100.0,
        added_to_cart=1,
        orders=1,
        sum_price=0.0,
    )
    card = CommonCardStat(
        nmid=1, open_card=100, add_to_cart=2, orders=1, orders_sum=0, buy_outs=0
    )
    card.date = page2_end

    with (
        patch.object(manager, "get_total_pages", new=AsyncMock(return_value=2)),
        patch.object(
            manager, "get_earliest_stat_date", new=AsyncMock(return_value=earliest)
        ),
        patch.object(
            manager,
            "_load_daily_stat_data",
            new=AsyncMock(
                return_value=(
                    [stat],
                    [card],
                    {page2_end: 0},
                    {page2_end: 0},
                    {page2_end: 0},
                    {page2_end: 0},
                    {page2_end: 0},
                )
            ),
        ),
        patch(
            "app.client_bot.user_interface.views.messages.adv_keyword_messages.backend.common_stat_data_manager.is_rec_system_shelf_mode_operational",
            new=AsyncMock(return_value=False),
        ),
    ):
        text, current_page, total_pages = await manager.get_days_static_text_page(
            adv_setting_mock,
            2,
            options=DaysStatTextOptions(
                show_forecast=False,
                show_clicks_warning=False,
                show_organic_pct=True,
            ),
        )

    assert current_page == 2
    assert total_pages == 2
    assert text
    assert page2_end.strftime("%d.%m.%Y") in text


@pytest.mark.asyncio
async def test_collect_historical_adv_ids_merges_rebound_and_current() -> None:
    """Дневная статистика должна видеть старые adv_id после перепривязки."""
    adv_setting_mock = AsyncMock()
    adv_setting_mock.id = 99
    adv_setting_mock.adv_id = 32824944
    adv_setting_mock.search_adv_id = 29734515
    adv_setting_mock.nmids = [10749810]
    adv_setting_mock.wb_cabinet_id = 1

    with (
        patch.object(
            manager,
            "_get_pg_sibling_adv_ids",
            new=AsyncMock(return_value=({32824944}, {29734515})),
        ),
        patch.object(
            manager,
            "_get_cluster_adv_ids_for_nmid",
            new=AsyncMock(return_value={11111111}),
        ),
        patch(
            "app.client_bot.user_interface.views.messages.adv_keyword_messages.backend.common_stat_data_manager.get_rebound_wb_adv_ids",
            new=AsyncMock(return_value=({22222222}, {33333333})),
        ),
    ):
        auto_ids, auction_ids = await manager._collect_historical_adv_ids(
            adv_setting_mock
        )

    assert auto_ids == [11111111, 22222222, 32824944]
    assert auction_ids == [29734515, 33333333]


@pytest.mark.asyncio
async def test_earliest_stat_date_uses_latest_required_source() -> None:
    """Если карточная история начинается раньше кампании, граница страниц не должна уезжать назад."""
    today = datetime.datetime.now().date()
    common_earliest = today - datetime.timedelta(days=60)
    adv_earliest = today - datetime.timedelta(days=27)

    adv_setting_mock = AsyncMock()
    adv_setting_mock.nmids = [1]
    adv_setting_mock.adv_id = 2
    adv_setting_mock.search_adv_id = 3

    with (
        patch.object(
            manager,
            "_collect_historical_adv_ids",
            new=AsyncMock(return_value=([2], [3])),
        ),
        patch.object(
            manager,
            "_get_min_date",
            new=AsyncMock(return_value=adv_earliest),
        ),
    ):
        earliest_date = await manager.get_earliest_stat_date(adv_setting_mock)

    assert earliest_date == adv_earliest


@pytest.mark.asyncio
async def test_earliest_stat_date_returns_none_without_auto_adv() -> None:
    """Без auto adv_id экран не должен делать ClickHouse-запросы для границы страниц."""
    adv_setting_mock = AsyncMock()
    adv_setting_mock.nmids = [1]
    adv_setting_mock.adv_id = None
    adv_setting_mock.search_adv_id = 3

    with patch.object(manager, "_get_min_date", new=AsyncMock()) as get_min_date_mock:
        earliest_date = await manager.get_earliest_stat_date(adv_setting_mock)

    assert earliest_date is None
    get_min_date_mock.assert_not_awaited()


@pytest.mark.asyncio
async def test_days_page_sorts_newest_first_without_affecting_inline_stats() -> None:
    """Экран по кнопке должен быть newest-first, но это не влияет на встроенный блок."""
    today = datetime.datetime.now().date()
    yesterday = today - datetime.timedelta(days=1)

    adv_setting_mock = AsyncMock()
    adv_setting_mock.nmids = [1]
    adv_setting_mock.adv_id = 2
    adv_setting_mock.search_adv_id = 3
    adv_setting_mock.plan_for_sales_for_day = None
    adv_setting_mock.target_price_for_order = None
    adv_setting_mock.max_price_for_order = None

    today_stat = SmallFullAdvStatPerDay(
        date=today,
        views=100,
        clicks=10,
        spend=100.0,
        added_to_cart=1,
        orders=1,
        sum_price=0.0,
    )
    yesterday_stat = SmallFullAdvStatPerDay(
        date=yesterday,
        views=100,
        clicks=10,
        spend=100.0,
        added_to_cart=1,
        orders=1,
        sum_price=0.0,
    )
    today_card = CommonCardStat(
        nmid=1, open_card=100, add_to_cart=2, orders=1, orders_sum=0, buy_outs=0
    )
    yesterday_card = CommonCardStat(
        nmid=1, open_card=100, add_to_cart=2, orders=1, orders_sum=0, buy_outs=0
    )
    today_card.date = today
    yesterday_card.date = yesterday

    with (
        patch.object(manager, "get_total_pages", new=AsyncMock(return_value=1)),
        patch.object(
            manager,
            "get_earliest_stat_date",
            new=AsyncMock(return_value=yesterday),
        ),
        patch.object(
            manager,
            "_load_daily_stat_data",
            new=AsyncMock(
                return_value=(
                    [yesterday_stat, today_stat],
                    [yesterday_card, today_card],
                    {today: 0, yesterday: 0},
                    {today: 0, yesterday: 0},
                    {today: 0, yesterday: 0},
                    {today: 0, yesterday: 0},
                    {today: 0, yesterday: 0},
                )
            ),
        ),
        patch(
            "app.client_bot.user_interface.views.messages.adv_keyword_messages.backend.common_stat_data_manager.is_rec_system_shelf_mode_operational",
            new=AsyncMock(return_value=False),
        ),
    ):
        text, current_page, total_pages = await manager.get_days_static_text_page(
            adv_setting_mock,
            1,
            options=DaysStatTextOptions(
                show_forecast=False,
                show_clicks_warning=False,
                show_organic_pct=True,
            ),
        )

    lines = [
        line
        for line in text.splitlines()
        if line.startswith(today.strftime("%d.%m.%Y"))
        or line.startswith(yesterday.strftime("%d.%m.%Y"))
    ]
    assert current_page == 1
    assert total_pages == 1
    assert lines[0].startswith(today.strftime("%d.%m.%Y"))
    assert lines[1].startswith(yesterday.strftime("%d.%m.%Y"))


def test_daily_stats_keyboard_preserves_sort_mode() -> None:
    """Кнопка возврата должна вести в тот же режим списка ключей."""
    markup = keyboards.get_keywords_daily_stats_keyboard(
        adv_original_id=10,
        page=1,
        total_pages=3,
        keywords_page=7,
        sort_mode="only_out_index",
    )

    back_button = markup.inline_keyboard[-1][0]
    callback_data = callbacks.SettingKeywords.unpack(back_button.callback_data)
    assert callback_data.type == "only_out_index"
    assert callback_data.page == 7
