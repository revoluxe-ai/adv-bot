import time

from app.core.mp.wb.api.adapter.analitika_i_dannye_client.voronka_prodazh.post_sales_funnel_products_history.dto import (
    CommonSaleStatRow,
)
from app.utils.ch_semaphore import run_ch_with_timeout
from app.utils.click_house.client import get_clickhouse_client


class ClickHouseCommonStatManager:
    async def insert(self, rows: list[CommonSaleStatRow]) -> None:
        if not rows:
            return None

        values = [
            (
                row.nmid,
                "'%s'" % row.day.strftime("%Y-%m-%d"),
                row.open_card,
                row.add_to_cart,
                row.orders,
                row.orders_sum,
                row.buy_outs,
                row.buyouts_sum_rub,
            )
            for row in rows
        ]

        version = time.time()

        query = """
        INSERT INTO wb_common_stat
        (nmid, date, open_card, add_to_cart, orders, orders_sum, buy_outs, buyouts_sum_rub, version)
        VALUES
        """
        query += ",".join(
            ["(%s, %s, %s, %s, %s, %s, %s, %s, %s)" % (*value, version) for value in values]
        )
        async def _insert() -> None:
            async with get_clickhouse_client() as client:
                await client.query(query)

        await run_ch_with_timeout(_insert())
        return None


