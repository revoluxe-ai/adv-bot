"""ClickHouse-аналитика по auto_shelf intervals для control-контура."""

from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
from typing import Any, cast

from clickhouse_connect.driver.query import QueryResult

from app.utils.ch_semaphore import anti_ch_crash_semaphore
from app.utils.click_house.client import get_clickhouse_client

from .bid_units import cpc_from_totals
from .dto import BidStatsDTO


class AutoShelfBidControlAnalyticsRepository:
    """Чтение дедуп-метрик по точкам ставки из auto_shelf_bid_intervals."""

    def __init__(self) -> None:
        self._sql_dir = Path(__file__).parent.joinpath("sql")

    def _load_sql(self, filename: str) -> str:
        """Прочитать SQL-шаблон из каталога sql/."""
        return self._sql_dir.joinpath(filename).read_text(encoding="utf-8")

    @staticmethod
    def _build_bid_stats_dto(row: dict[str, Any]) -> BidStatsDTO:
        """Собрать BidStatsDTO и вычислить производные метрики."""
        impressions = int(row["impressions"])
        clicks = int(row["clicks"])
        carts = int(row["carts"])
        orders = int(row["orders"])
        spend = float(row["spend"])
        # cart_cpa в DTO = CPC score (имя поля легаси, см. BidStatsDTO).
        cart_cpa = cpc_from_totals(spend, clicks)
        ctr = (clicks / impressions) if impressions > 0 else None
        cart_cr = (carts / clicks) if clicks > 0 else None
        last_raw = row.get("last_interval_at")
        last_interval_at: datetime | None
        if last_raw is None:
            last_interval_at = None
        elif isinstance(last_raw, datetime):
            last_interval_at = last_raw
        else:
            last_interval_at = datetime.fromisoformat(str(last_raw))
        if last_interval_at is not None and last_interval_at.tzinfo is None:
            last_interval_at = last_interval_at.replace(tzinfo=timezone.utc)
        return BidStatsDTO(
            bid_minor=int(row["bid_minor"]),
            currency=str(row["currency"]),
            mode=(None if row.get("mode") is None else str(row["mode"])),
            last_interval_at=last_interval_at,
            impressions=impressions,
            clicks=clicks,
            carts=carts,
            orders=orders,
            spend=spend,
            cart_cpa=cart_cpa,
            ctr=ctr,
            cart_cr=cart_cr,
        )

    async def get_bid_stats(
        self,
        nmid: int,
        from_ts: datetime,
        currency: str,
        mode: str | None = None,
        bid_minor: int | None = None,
        *,
        to_ts: datetime | None = None,
    ) -> list[BidStatsDTO]:
        """Агрегаты по bid_minor (все mode на одной ставке), read-time dedup."""
        query = self._load_sql("get_bid_stats_dedup.sql")
        params = {
            "nmid": nmid,
            "from_ts": from_ts,
            "to_ts": to_ts,
            "currency": currency,
            "mode": mode,
            "bid_minor": bid_minor,
        }
        async with anti_ch_crash_semaphore:
            async with get_clickhouse_client() as client:
                result: QueryResult = await client.query(query, parameters=params)
        if not result.result_rows:
            return []
        names = cast(tuple[object, ...], result.column_names)
        column_names = [str(name) for name in names]
        out: list[BidStatsDTO] = []
        for row_values in result.result_rows:
            row: dict[str, Any] = dict(zip(column_names, tuple(row_values)))
            out.append(self._build_bid_stats_dto(row))
        return out

    async def get_impressions(
        self,
        nmid: int,
        from_ts: datetime,
        currency: str,
        bid_minor: int,
        *,
        mode: str | None = None,
    ) -> int:
        """Показы по ставке; ``mode=None`` — все mode (пассивный/legacy main)."""
        query = self._load_sql("get_impressions_for_mode_bid.sql")
        params = {
            "nmid": nmid,
            "from_ts": from_ts,
            "currency": currency,
            "mode": mode,
            "bid_minor": bid_minor,
        }
        async with anti_ch_crash_semaphore:
            async with get_clickhouse_client() as client:
                result: QueryResult = await client.query(query, parameters=params)
        if not result.result_rows:
            return 0
        return int(result.result_rows[0][0])

    async def get_best_bid_by_cart_cpa(
        self,
        nmid: int,
        from_ts: datetime,
        currency: str,
        *,
        mode: str | None = None,
        to_ts: datetime | None = None,
        min_impressions: int | None = None,
    ) -> BidStatsDTO | None:
        """Лучшая ставка: min CPC ``spend/clicks`` при ``impressions > 0``, ``clicks > 0``.

        Args:
            min_impressions: не используется в control (всегда ``None``); оставлен
                для совместимости SQL-шаблона.
        """
        query = self._load_sql("get_best_bid_by_cart_cpa.sql")
        params = {
            "nmid": nmid,
            "from_ts": from_ts,
            "to_ts": to_ts,
            "currency": currency,
            "mode": mode,
            "min_impressions": min_impressions,
        }
        async with anti_ch_crash_semaphore:
            async with get_clickhouse_client() as client:
                result: QueryResult = await client.query(query, parameters=params)
        if not result.result_rows:
            return None
        names = cast(tuple[object, ...], result.column_names)
        column_names = [str(name) for name in names]
        row: dict[str, Any] = dict(zip(column_names, tuple(result.result_rows[0])))
        return self._build_bid_stats_dto(row)

    async def get_best_bid_by_ctr(
        self,
        nmid: int,
        from_ts: datetime,
        currency: str,
        *,
        mode: str | None = None,
        to_ts: datetime | None = None,
    ) -> BidStatsDTO | None:
        """Лучшая ставка: max CTR ``clicks/impressions`` при ``impressions > 0``.

        Для режима оптимизации по CTR, когда фактическое CPO ниже resolve CPO.
        """
        query = self._load_sql("get_best_bid_by_ctr.sql")
        params = {
            "nmid": nmid,
            "from_ts": from_ts,
            "to_ts": to_ts,
            "currency": currency,
            "mode": mode,
        }
        async with anti_ch_crash_semaphore:
            async with get_clickhouse_client() as client:
                result: QueryResult = await client.query(query, parameters=params)
        if not result.result_rows:
            return None
        names = cast(tuple[object, ...], result.column_names)
        column_names = [str(name) for name in names]
        row: dict[str, Any] = dict(zip(column_names, tuple(result.result_rows[0])))
        return self._build_bid_stats_dto(row)

