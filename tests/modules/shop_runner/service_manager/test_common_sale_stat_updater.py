import datetime
from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest

from app.core.mp.wb.api.adapter.analitika_i_dannye_client.voronka_prodazh.post_sales_funnel_products_history.dto import (
    CommonSaleStatRow,
)
from app.modules.shop_runner.service_manager.services.common_sale_stat_updater.common_sale_stat_updater import (
    CommonSaleStatUpdater,
)


@pytest.mark.asyncio
async def test_common_sale_stat_updater_chunks_and_inserts():
    wb_data_manager = SimpleNamespace()
    wb_data_manager.get_sales_funnel_products_history = AsyncMock(
        side_effect=[
            [
                CommonSaleStatRow(
                    nmid=1,
                    day=datetime.date(2025, 12, 21),
                    open_card=1,
                    add_to_cart=1,
                    orders=1,
                    orders_sum=10.0,
                    buy_outs=1,
                )
            ],
            [
                CommonSaleStatRow(
                    nmid=21,
                    day=datetime.date(2025, 12, 21),
                    open_card=2,
                    add_to_cart=2,
                    orders=2,
                    orders_sum=20.0,
                    buy_outs=2,
                )
            ],
        ]
    )
    wb_manager_hub = SimpleNamespace(wb_data_manager=wb_data_manager)

    clickhouse_manager = SimpleNamespace()
    clickhouse_manager.insert = AsyncMock()

    updater = CommonSaleStatUpdater(
        wb_manager_hub=wb_manager_hub,
        clickhouse_manager=clickhouse_manager,
    )

    advs = [SimpleNamespace(main_nmid=i) for i in range(1, 26)]

    await updater.update_last_week_stats(advs)

    assert wb_data_manager.get_sales_funnel_products_history.await_count == 2
    clickhouse_manager.insert.assert_awaited_once()
    inserted_rows = clickhouse_manager.insert.call_args.args[0]
    assert len(inserted_rows) == 2


