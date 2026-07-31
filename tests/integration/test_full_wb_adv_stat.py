"""Integration: full_wb_adv_stat against Guarded test CH (rewrite default_db).

Act uses production SQL with ``default_db.*``; tests redirect
``get_clickhouse_client`` and rewrite qualifiers to
``test_adv_bot_clickhouse.*`` before the destructive guard sees them.
"""

import datetime as dt
from unittest.mock import AsyncMock, patch

import pytest

import app.modules.shop_runner.wb_stat_manager.clickhouse_manager.full_wb_adv_stat as full_wb_adv_stat_module
from app.modules.shop_runner.wb_stat_manager.clickhouse_manager import full_wb_adv_stat

from clickhouse_connect import get_async_client  # Import for type hinting
from tests.support.rewrite_default_db_ch_client import patch_get_clickhouse_client

pytestmark = pytest.mark.destructive_local


@pytest.mark.integration
async def test_get_keywords_views_by_days(
    clickhouse_client: get_async_client,
    monkeypatch: pytest.MonkeyPatch,
):
    """Seed test CH → Act via rewritten client → assert keyword/auto views text."""
    adv_id = 123
    start_date = dt.datetime(2025, 11, 26)
    end_date = dt.datetime(2025, 11, 28)

    # Очищаем таблицы перед тестом
    await clickhouse_client.command(f"TRUNCATE TABLE test_adv_bot_clickhouse.full_adv_wb_stat")
    await clickhouse_client.command(f"TRUNCATE TABLE test_adv_bot_clickhouse.clusters_adv_stats")
    await clickhouse_client.command(f"TRUNCATE TABLE test_adv_bot_clickhouse.mv_clusters_daily_agg")

    patch_get_clickhouse_client(
        monkeypatch, [full_wb_adv_stat_module], clickhouse_client
    )


    # Тестовые данные для mv_clusters_daily_agg через clusters_adv_stats
    # День 1: 2025-11-26
    cluster_rows = [
        (
            adv_id,
            1111,
            "category",
            "ключ1",
            5000,
            1000,
            0.2,
            10.0,
            0,
            0,
            0.0,
            0.0,
            dt.date(2025, 11, 26),
            0.0,
            dt.datetime(2025, 11, 26, 12, 0, 0),
        ),
        (
            adv_id,
            1111,
            "category",
            "ключ2",
            10000,
            2000,
            0.2,
            10.0,
            0,
            0,
            0.0,
            0.0,
            dt.date(2025, 11, 26),
            0.0,
            dt.datetime(2025, 11, 26, 12, 30, 0),
        ),
        (
            adv_id,
            1111,
            "category",
            "ключ1",
            7000,
            1500,
            0.214,
            10.714285,
            0,
            0,
            0.0,
            0.0,
            dt.date(2025, 11, 27),
            0.0,
            dt.datetime(2025, 11, 27, 12, 0, 0),
        ),
        (
            adv_id,
            1111,
            "category",
            "ключ3",
            3000,
            500,
            0.166,
            10.0,
            0,
            0,
            0.0,
            0.0,
            dt.date(2025, 11, 27),
            0.0,
            dt.datetime(2025, 11, 27, 12, 30, 0),
        ),
    ]

    await clickhouse_client.insert(
        "test_adv_bot_clickhouse.clusters_adv_stats",
        cluster_rows,
        column_names=[
            "adv_id",
            "nmid",
            "wb_category",
            "norm_query",
            "views",
            "clicks",
            "ctr",
            "cpm",
            "add_to_cart",
            "orders",
            "cpc",
            "avr_pos",
            "date",
            "spend",
            "timestamp",
        ],
    )

    # Тестовые данные для full_adv_wb_stat
    # День 1: 2025-11-26
    await clickhouse_client.insert(
        "test_adv_bot_clickhouse.full_adv_wb_stat",
        [
            (adv_id, dt.date(2025, 11, 26), 20000, 3000, 150.0, 50, 5, 2500.0, 50.0),
        ],
        column_names=[
            'adv_id',
            'date',
            'views',
            'clicks',
            'spend',
            'added_to_cart',
            'orders',
            'sum_price_orders',
            'version',
        ]
    )

    # День 2: 2025-11-27
    await clickhouse_client.insert(
        "test_adv_bot_clickhouse.full_adv_wb_stat",
        [
            (adv_id, dt.date(2025, 11, 27), 15000, 2000, 100.0, 30, 3, 1500.0, 75.0),
        ],
        column_names=[
            'adv_id',
            'date',
            'views',
            'clicks',
            'spend',
            'added_to_cart',
            'orders',
            'sum_price_orders',
            'version',
        ]
    )

    # День 3: 2025-11-28
    await clickhouse_client.insert(
        "test_adv_bot_clickhouse.full_adv_wb_stat",
        [
            (adv_id, dt.date(2025, 11, 28), 10000, 1000, 50.0, 10, 1, 500.0, 100.0),
        ],
        column_names=[
            'adv_id',
            'date',
            'views',
            'clicks',
            'spend',
            'added_to_cart',
            'orders',
            'sum_price_orders',
            'version',
        ]
    )

    result_keywords_views = await full_wb_adv_stat.get_keywords_views_by_days(
        [adv_id], start_date, end_date
    )
    result_auto_adv_stats = await full_wb_adv_stat.get_daily_stats_by_last_days(
        [adv_id], start_date, end_date
    )

    auto_views_by_day = {stat.date: stat.views for stat in result_auto_adv_stats}

    # Ожидаемые показы по ключевым словам
    expected_keywords_views = {
        dt.date(2025, 11, 26): 15000,  # 5000 + 10000
        dt.date(2025, 11, 27): 10000,  # 7000 + 3000
        dt.date(2025, 11, 28): 0,
    }
    assert result_keywords_views == expected_keywords_views

    # Ожидаемые дополнительные показы
    expected_extra_views = {
        dt.date(2025, 11, 26): auto_views_by_day.get(dt.date(2025, 11, 26), 0) - expected_keywords_views.get(dt.date(2025, 11, 26), 0), # 20000 - 15000 = 5000
        dt.date(2025, 11, 27): auto_views_by_day.get(dt.date(2025, 11, 27), 0) - expected_keywords_views.get(dt.date(2025, 11, 27), 0), # 15000 - 10000 = 5000
        dt.date(2025, 11, 28): auto_views_by_day.get(dt.date(2025, 11, 28), 0) - expected_keywords_views.get(dt.date(2025, 11, 28), 0), # 10000 - 0 = 10000
    }

    # Добавим проверку, что _get_days_static_text формирует правильный текст
    # Для этого нам понадобится CommonStatDataManager и AdvSetting
    from app.client_bot.user_interface.views.messages.adv_keyword_messages.backend.common_stat_data_manager import CommonStatDataManager
    from app.modules.common_slaves.wildberries.models import AdvSetting
    from app.modules.common_slaves.wildberries.models.wb_cabinet import WBCabinet
    from app.modules.shop_runner.wb_statistic_manager.backend.types.common_card_stat import CommonCardStat

    # Создаем фиктивный WBCabinet
    wb_cabinet = WBCabinet(
        id=1,
        shop_id="test_shop_id",
        active=True,
        expiration_time=dt.datetime.now() + dt.timedelta(days=7),
        balance=0.0,
        bonus=0.0,
        demo=False,
        expiration_alarm_days_pass=None,
    )

    adv_setting = AdvSetting(
        adv_id=adv_id,
        nmids=[1111],
        plan_for_sales_for_day=15,
        target_price_for_order=45.0,
        max_price_for_order=200.0,
        wb_cabinet_id=wb_cabinet.id,  # Привязываем к созданному кабинету
        name="Тестовая РК", # Добавляем обязательное поле name
    )

    # Создадим фиктивные common_card_stats для теста
    common_card_stats = [
        CommonCardStat(nmid=1111, _date=dt.date(2025, 11, 26), open_card=100, add_to_cart=8, orders=0, orders_sum=0, buy_outs=0),
        CommonCardStat(nmid=1111, _date=dt.date(2025, 11, 27), open_card=100, add_to_cart=8, orders=2, orders_sum=517.61, buy_outs=0),
        CommonCardStat(nmid=1111, _date=dt.date(2025, 11, 28), open_card=100, add_to_cart=2, orders=0, orders_sum=0, buy_outs=0),
    ]

    # Создадим фиктивные SmallFullAdvStatPerDay для теста (для concatenated_adv_stat_result)
    concatenated_adv_stat_result = [
        full_wb_adv_stat.SmallFullAdvStatPerDay(date=dt.date(2025, 11, 26), views=auto_views_by_day.get(dt.date(2025, 11, 26),0), clicks=0, spend=718.39, added_to_cart=8, orders=0, sum_price=0),
        full_wb_adv_stat.SmallFullAdvStatPerDay(date=dt.date(2025, 11, 27), views=auto_views_by_day.get(dt.date(2025, 11, 27),0), clicks=0, spend=517.61, added_to_cart=8, orders=2, sum_price=0),
        full_wb_adv_stat.SmallFullAdvStatPerDay(date=dt.date(2025, 11, 28), views=auto_views_by_day.get(dt.date(2025, 11, 28),0), clicks=0, spend=679.28, added_to_cart=2, orders=0, sum_price=0),
    ]

    stat_data_manager = CommonStatDataManager()

    with patch(
        "app.client_bot.user_interface.views.messages.adv_keyword_messages.backend."
        "common_stat_data_manager.is_rec_system_shelf_mode_operational",
        new=AsyncMock(return_value=False),
    ):
        generated_text = await stat_data_manager._get_days_static_text(
            adv_setting,
            concatenated_adv_stat_result,
            common_card_stats,
            auto_views_by_day,
            result_keywords_views,
            {},
            {},
            {},
        )

    expected_text = """26.11.2025: Корз.:8(0) Зак.:0(0)шт.Себеc: 718.39р. Доп.пок.: 5000 Кл(рек.кл/орг/пол): 0/100/0 (100)
27.11.2025: Корз.:8(0) Зак.:2(0)шт.Себеc: 258.81р. Доп.пок.: 5000 Кл(рек.кл/орг/пол): 0/100/0 (100)
28.11.2025: Корз.:2(0) Зак.:0(0)шт.Себеc: 679.28р. Доп.пок.: 10000 Кл(рек.кл/орг/пол): 0/100/0 (100)
План: продажи: 15 Цель: 45.0р. Макс: 200.0р.
"""
    # Ожидаемый текст нужно будет скорректировать под фактические значения mean_pay_for_order
    assert generated_text == expected_text

    # Тестирование с пустыми данными
    await clickhouse_client.command(f"TRUNCATE TABLE test_adv_bot_clickhouse.clusters_adv_stats")
    await clickhouse_client.command(f"TRUNCATE TABLE test_adv_bot_clickhouse.mv_clusters_daily_agg")
    empty_result_views = await full_wb_adv_stat.get_keywords_views_by_days(
        [adv_id], start_date, end_date
    )
    assert empty_result_views == {dt.date(2025, 11, 26): 0, dt.date(2025, 11, 27): 0, dt.date(2025, 11, 28): 0}


@pytest.mark.integration
async def test_get_spend_by_last_days_with_argmax(
    clickhouse_client: get_async_client,
    monkeypatch: pytest.MonkeyPatch,
):
    """Argmax spend by version: Act via rewritten client hits test CH rows only."""
    adv_id = 321
    other_adv_id = 999
    start_date = dt.datetime(2025, 11, 26)
    end_date = dt.datetime(2025, 11, 27)

    await clickhouse_client.command("TRUNCATE TABLE test_adv_bot_clickhouse.full_adv_wb_stat")

    await clickhouse_client.insert(
        "test_adv_bot_clickhouse.full_adv_wb_stat",
        [
            (adv_id, dt.date(2025, 11, 26), 1, 1, 50.0, 0, 0, 0.0, 1.0),
            (adv_id, dt.date(2025, 11, 26), 1, 1, 75.0, 0, 0, 0.0, 2.0),
            (adv_id, dt.date(2025, 11, 27), 1, 1, 40.0, 0, 0, 0.0, 1.0),
            (adv_id, dt.date(2025, 11, 27), 1, 1, 55.0, 0, 0, 0.0, 3.0),
            (other_adv_id, dt.date(2025, 11, 26), 1, 1, 999.0, 0, 0, 0.0, 5.0),
        ],
        column_names=[
            "adv_id",
            "date",
            "views",
            "clicks",
            "spend",
            "added_to_cart",
            "orders",
            "sum_price_orders",
            "version",
        ],
    )

    patch_get_clickhouse_client(
        monkeypatch, [full_wb_adv_stat_module], clickhouse_client
    )
    value = await full_wb_adv_stat.get_spend_by_last_days(
        [adv_id], start_date, end_date
    )

    assert value == pytest.approx(75.0 + 55.0)
