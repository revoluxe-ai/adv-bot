import datetime as dt
import pytest

from app.modules.shop_runner.wb_stat_manager.clickhouse_manager import full_wb_adv_stat
from clickhouse_connect import get_async_client # Import for type hinting

@pytest.mark.integration
async def test_get_keywords_views_by_days(clickhouse_client: get_async_client):
    adv_id = 123
    start_date = dt.datetime(2025, 11, 26)
    end_date = dt.datetime(2025, 11, 28)

    # Очищаем таблицы перед тестом
    await clickhouse_client.command(f"TRUNCATE TABLE default_db.full_adv_wb_stat")
    await clickhouse_client.command(f"TRUNCATE TABLE default_db.advkeyword_new")


    # Тестовые данные для advkeyword_new
    # День 1: 2025-11-26
    await clickhouse_client.command(f"""
        INSERT INTO default_db.advkeyword_new (adv_id, text, date, clicks_state, views_state, spend_state, version)
        SELECT
            {adv_id},
            'ключ1',
            '2025-11-26'::Date,
            argMaxState(CAST(1000 AS Int32), 50.0),
            argMaxState(CAST(5000 AS Int32), 50.0),
            argMaxState(CAST(50.0 AS Float64), 50.0),
            50.0
        
        UNION ALL
        
        SELECT
            {adv_id},
            'ключ2',
            '2025-11-26'::Date,
            argMaxState(CAST(2000 AS Int32), 100.0),
            argMaxState(CAST(10000 AS Int32), 100.0),
            argMaxState(CAST(100.0 AS Float64), 100.0),
            100.0
    """)

    # День 2: 2025-11-27
    await clickhouse_client.command(f"""
        INSERT INTO default_db.advkeyword_new (adv_id, text, date, clicks_state, views_state, spend_state, version)
        SELECT
            {adv_id},
            'ключ1',
            '2025-11-27'::Date,
            argMaxState(CAST(1500 AS Int32), 75.0),
            argMaxState(CAST(7000 AS Int32), 75.0),
            argMaxState(CAST(75.0 AS Float64), 75.0),
            75.0
        
        UNION ALL
        
        SELECT
            {adv_id},
            'ключ3',
            '2025-11-27'::Date,
            argMaxState(CAST(500 AS Int32), 30.0),
            argMaxState(CAST(3000 AS Int32), 30.0),
            argMaxState(CAST(30.0 AS Float64), 30.0),
            30.0
    """)

    # Тестовые данные для full_adv_wb_stat
    # День 1: 2025-11-26
    await clickhouse_client.insert(
        "default_db.full_adv_wb_stat",
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
        "default_db.full_adv_wb_stat",
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
        "default_db.full_adv_wb_stat",
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

    # Вызываем тестируемую функцию
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
    from app.modules.common_slaves.wildberries.models import AdvSetting, WBCabinet
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
        white_list_update_active=False,
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

    generated_text = await stat_data_manager._get_days_static_text(
        adv_setting,
        concatenated_adv_stat_result,
        common_card_stats,
        auto_views_by_day,
        result_keywords_views,
    )

    expected_text = """26.11.2025: Корз.: 8 Зак.: 0шт.Себеc: 718.39р. Доп.пок.: 5000
27.11.2025: Корз.: 8 Зак.: 2шт.Себеc: 258.81р. Доп.пок.: 5000
28.11.2025: Корз.: 2 Зак.: 0шт.Себеc: 679.28р. Доп.пок.: 10000
План: продажи: 15 Цель: 45.0р. Макс: 200.0р.
"""
    # Ожидаемый текст нужно будет скорректировать под фактические значения mean_pay_for_order
    assert generated_text == expected_text

    # Тестирование с пустыми данными
    await clickhouse_client.command(f"TRUNCATE TABLE default_db.advkeyword_new")
    empty_result_views = await full_wb_adv_stat.get_keywords_views_by_days(
        [adv_id], start_date, end_date
    )
    assert empty_result_views == {dt.date(2025, 11, 26): 0, dt.date(2025, 11, 27): 0, dt.date(2025, 11, 28): 0}
