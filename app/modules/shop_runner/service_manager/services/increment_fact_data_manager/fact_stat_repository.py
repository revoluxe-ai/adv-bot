from __future__ import annotations

import asyncio
from datetime import datetime
from pathlib import Path
from typing import Any, Optional, cast
from uuid import UUID
from zoneinfo import ZoneInfo

from clickhouse_connect.driver.query import QueryResult

from app.utils.ch_semaphore import anti_ch_crash_semaphore
from app.utils.click_house.client import get_clickhouse_client

from .dto import AdvCommonStat, CardCommonStat
from .dto.fact_stat_snapshot import FactStatSnapshot


class FactStatRepository:
    def __init__(self, tz_name: str = "Europe/Moscow") -> None:
        self._tz = ZoneInfo(tz_name)
        self._sql_dir = Path(__file__).parent.joinpath("sql")

    def _today_date(self) -> str:
        return datetime.now(self._tz).strftime("%Y-%m-%d")

    def _load_sql(self, filename: str) -> str:
        return self._sql_dir.joinpath(filename).read_text(encoding="utf-8")

    async def fetch_card_stat(self, nmids: list[int]) -> Optional[CardCommonStat]:
        query = self._load_sql("get_card_stat.sql")
        params = {"report_date": self._today_date(), "nmids": nmids}
        async with anti_ch_crash_semaphore:
            async with get_clickhouse_client() as client:
                result: QueryResult = await client.query(
                    query, parameters=params
                )
        if not result.result_set:
            return None
        row: dict[str, Any] | None = cast(dict[str, Any] | None, result.first_item)
        return CardCommonStat(
            open_card_sum=int(row["open_card_sum"]),
            carts_card_sum=int(row["carts_card_sum"]),
            orders_card_sum=int(row["orders_card_sum"]),
            orders_sum_card_rub=int(row["orders_sum_card_rub"]),
            buy_outs_sum=int(row["buy_outs_sum"]),
        )

    async def fetch_adv_stat(self, adv_ids: list[int]) -> Optional[AdvCommonStat]:
        query = self._load_sql("get_adv_stat.sql")
        params = {"report_date": self._today_date(), "adv_ids": adv_ids}
        async with anti_ch_crash_semaphore:
            async with get_clickhouse_client() as client:
                result: QueryResult = await client.query(
                    query, parameters=params
                )
        if not result.result_set:
            return None
        row: dict[str, Any] | None = cast(dict[str, Any] | None, result.first_item)
        if not row:
            return None
        return AdvCommonStat(
            views_adv_sum=int(row["views_adv_sum"]),
            clicks_adv_sum=int(row["clicks_adv_sum"]),
            carts_adv_sum=int(row["carts_adv_sum"]),
            orders_adv_sum=int(row["orders_adv_sum"]),
            spend_adv_sum_rub=int(row["spend_adv_sum_rub"]),
            orders_sum_adv_rub=int(row["orders_sum_adv_rub"]),
        )

    async def fetch_current_snapshot(
        self,
        shop_id: UUID,
        complex_adv_id: int,
        bucket_start: datetime,
        src_ts: datetime,
        version: int,
        nmids: list[int],
        adv_ids: list[int],
    ) -> FactStatSnapshot | None:
        card_stat, adv_stat = await asyncio.gather(
            self.fetch_card_stat(nmids), self.fetch_adv_stat(adv_ids)
        )
        if card_stat is None or adv_stat is None:
            return None
        return FactStatSnapshot(
            shop_id=shop_id,
            complex_adv_id=complex_adv_id,
            bucket_start=bucket_start,
            src_ts=src_ts,
            version=version,
            views_adv_sum=adv_stat.views_adv_sum,
            clicks_adv_sum=adv_stat.clicks_adv_sum,
            carts_adv_sum=adv_stat.carts_adv_sum,
            orders_adv_sum=adv_stat.orders_adv_sum,
            spend_adv_sum_rub=adv_stat.spend_adv_sum_rub,
            orders_sum_adv_rub=adv_stat.orders_sum_adv_rub,
            open_card_sum=card_stat.open_card_sum,
            carts_card_sum=card_stat.carts_card_sum,
            orders_card_sum=card_stat.orders_card_sum,
            orders_sum_card_rub=card_stat.orders_sum_card_rub,
            buy_outs_sum=card_stat.buy_outs_sum,
        )

    async def fetch_prev_fact_state(
        self, shop_id: UUID, complex_adv_id: int
    ) -> FactStatSnapshot | None:
        query = self._load_sql("get_prev_fact_state.sql")
        params = {"shop_id": str(shop_id), "complex_adv_id": complex_adv_id}
        async with anti_ch_crash_semaphore:
            async with get_clickhouse_client() as client:
                result: QueryResult = await client.query(
                    query, parameters=params
                )
        if not result.result_rows:
            return None
        row = dict(zip(result.column_names, result.result_rows[0]))
        return FactStatSnapshot.from_clickhouse(row)

    async def upsert_prev_fact_state(self, snapshot: FactStatSnapshot) -> None:
        query = self._load_sql("insert_prev_fact_state.sql")
        params = {
            "bucket_start": snapshot.bucket_start,
            "shop_id": str(snapshot.shop_id),
            "complex_adv_id": snapshot.complex_adv_id,
            "views_adv_sum": snapshot.views_adv_sum,
            "clicks_adv_sum": snapshot.clicks_adv_sum,
            "carts_adv_sum": snapshot.carts_adv_sum,
            "orders_adv_sum": snapshot.orders_adv_sum,
            "spend_adv_sum_rub": snapshot.spend_adv_sum_rub,
            "orders_sum_adv_rub": snapshot.orders_sum_adv_rub,
            "open_card_sum": snapshot.open_card_sum,
            "carts_card_sum": snapshot.carts_card_sum,
            "orders_card_sum": snapshot.orders_card_sum,
            "orders_sum_card_rub": snapshot.orders_sum_card_rub,
            "buy_outs_sum": snapshot.buy_outs_sum,
            "src_ts": snapshot.src_ts,
            "version": snapshot.version,
        }
        async with anti_ch_crash_semaphore:
            async with get_clickhouse_client() as client:
                await client.query(query, parameters=params)
