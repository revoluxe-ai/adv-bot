"""Запись строк в ClickHouse: интервалы и prev-снимки auto_shelf_bid."""

from __future__ import annotations

from pathlib import Path

from app.utils.ch_semaphore import anti_ch_crash_semaphore
from app.utils.click_house.client import get_clickhouse_client

from .dto import AutoShelfBidIntervalRow, AutoShelfBidSnapshot


class ClickHouseAutoShelfBidWriter:
    """INSERT в auto_shelf_bid_intervals и auto_shelf_bid_prev через SQL-файлы."""

    def __init__(self) -> None:
        self._sql_dir = Path(__file__).parent.joinpath("sql")

    def _load_sql(self, filename: str) -> str:
        """Прочитать SQL из sql/ рядом с модулем."""
        return self._sql_dir.joinpath(filename).read_text(encoding="utf-8")

    async def insert_interval(self, row: AutoShelfBidIntervalRow) -> None:
        """Вставить дельту интервала (insert_auto_shelf_bid_interval.sql)."""
        query = self._load_sql("insert_auto_shelf_bid_interval.sql")
        params = {
            "event_date": row.event_date,
            "event_id": row.event_id,
            "src_ts": row.src_ts,
            "bucket_start": row.bucket_start,
            "version": row.version,
            "nmid": row.nmid,
            "mode": row.mode,
            "bid_minor": row.bid_minor,
            "currency": row.currency,
            "price_minor": row.price_minor,
            "price_currency": row.price_currency,
            "delta_impressions": row.delta_impressions,
            "delta_clicks": row.delta_clicks,
            "delta_carts": row.delta_carts,
            "delta_orders": row.delta_orders,
            "delta_spend": row.delta_spend,
        }
        async with anti_ch_crash_semaphore:
            async with get_clickhouse_client() as client:
                _ = await client.query(query, parameters=params)

    async def insert_prev(self, snapshot: AutoShelfBidSnapshot) -> None:
        """Сохранить снимок в prev-таблицу (insert_prev_auto_shelf_bid.sql)."""
        query = self._load_sql("insert_prev_auto_shelf_bid.sql")
        params = {
            "nmid": snapshot.nmid,
            "src_ts": snapshot.src_ts,
            "version": snapshot.version,
            "mode": snapshot.mode,
            "bid_minor": snapshot.bid_minor,
            "currency": snapshot.currency,
            "price_minor": snapshot.price_minor,
            "price_currency": snapshot.price_currency,
            "impressions": snapshot.impressions,
            "clicks": snapshot.clicks,
            "carts": snapshot.carts,
            "orders": snapshot.orders,
            "spend": snapshot.spend,
        }
        async with anti_ch_crash_semaphore:
            async with get_clickhouse_client() as client:
                _ = await client.query(query, parameters=params)
