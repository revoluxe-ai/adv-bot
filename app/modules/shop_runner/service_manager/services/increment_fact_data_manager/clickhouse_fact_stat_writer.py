from __future__ import annotations

from app.utils.ch_semaphore import anti_ch_crash_semaphore
from app.utils.click_house.client import get_clickhouse_client

from .dto import FactStatRow


class ClickHouseFactStatWriter:
    async def insert(self, row: FactStatRow) -> None:
        query = """
        INSERT INTO default_db.fact_stat_states (
    bucket_start,
    shop_id,
    complex_adv_id,
    views_adv_sum,
    clicks_adv_sum,
    carts_adv_sum,
    orders_adv_sum,
    spend_adv_sum_rub,
            orders_sum_adv_rub,
    open_card_sum,
    carts_card_sum,
    orders_card_sum,
    orders_sum_card_rub,
    buy_outs_sum,
    src_ts,
    version
)
VALUES (
    %(bucket_start)s,
    %(shop_id)s,
    %(complex_adv_id)s,
    %(views_adv_sum)s,
    %(clicks_adv_sum)s,
    %(carts_adv_sum)s,
    %(orders_adv_sum)s,
    %(spend_adv_sum_rub)s,
            %(orders_sum_adv_rub)s,
    %(open_card_sum)s,
    %(carts_card_sum)s,
    %(orders_card_sum)s,
    %(orders_sum_card_rub)s,
    %(buy_outs_sum)s,
    %(src_ts)s,
    %(version)s
)
"""
        params = {
            "bucket_start": row.bucket_start,
            "shop_id": str(row.shop_id),
            "complex_adv_id": row.complex_adv_id,
            "views_adv_sum": row.views_adv_sum,
            "clicks_adv_sum": row.clicks_adv_sum,
            "carts_adv_sum": row.carts_adv_sum,
            "orders_adv_sum": row.orders_adv_sum,
            "spend_adv_sum_rub": row.spend_adv_sum_rub,
            "orders_sum_adv_rub": row.orders_sum_adv_rub,
            "open_card_sum": row.open_card_sum,
            "carts_card_sum": row.carts_card_sum,
            "orders_card_sum": row.orders_card_sum,
            "orders_sum_card_rub": row.orders_sum_card_rub,
            "buy_outs_sum": row.buy_outs_sum,
            "src_ts": row.src_ts,
            "version": row.version,
        }
        async with anti_ch_crash_semaphore:
            async with get_clickhouse_client() as client:
                _ = await client.query(query, parameters=params)
        return None