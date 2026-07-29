import datetime

import pytest

from app.core.mp.wb.api.adapter.analitika_i_dannye_client.voronka_prodazh.post_sales_funnel_products_history.dto import (
    CommonSaleStatRow,
)
from app.modules.shop_runner.service_manager.services.common_sale_stat_updater.clickhouse_common_stat_manager import (
    ClickHouseCommonStatManager,
)
from app.utils.ch_semaphore import anti_ch_crash_semaphore

pytestmark = pytest.mark.destructive_local


@pytest.mark.integration
@pytest.mark.asyncio
async def test_clickhouse_common_stat_manager_insert_and_select(clickhouse_client):
    # Arrange: очистим таблицу, чтобы тест был детерминированным
    await clickhouse_client.command("TRUNCATE TABLE test_adv_bot_clickhouse.wb_common_stat")

    manager = ClickHouseCommonStatManager()
    day = datetime.date(2025, 12, 21)

    rows = [
        CommonSaleStatRow(
            nmid=123,
            day=day,
            open_card=10,
            add_to_cart=3,
            orders=2,
            orders_sum=199.99,
            buy_outs=1,
            buyouts_sum_rub=50.0,
        ),
        CommonSaleStatRow(
            nmid=456,
            day=day,
            open_card=20,
            add_to_cart=6,
            orders=4,
            orders_sum=399.5,
            buy_outs=2,
            buyouts_sum_rub=100.0,
        ),
    ]

    # Act
    await manager.insert(rows)
    async with anti_ch_crash_semaphore:
        # Assert
        result = await clickhouse_client.query(
            """
            SELECT nmid, date, open_card, add_to_cart, orders, orders_sum, buy_outs, buyouts_sum_rub
            FROM test_adv_bot_clickhouse.wb_common_stat
            WHERE nmid IN (123, 456) AND date = '2025-12-21'
            ORDER BY nmid
            """
    )

    assert result is not None
    assert result.result_rows == [
        (123, day, 10, 3, 2, 199.99, 1, 50.0),
        (456, day, 20, 6, 4, 399.5, 2, 100.0),
    ]


