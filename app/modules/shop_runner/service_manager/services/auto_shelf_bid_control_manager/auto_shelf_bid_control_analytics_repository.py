"""ClickHouse-аналитика по auto_shelf intervals для control-контура."""

from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
from typing import Any, cast

from clickhouse_connect.driver.query import QueryResult

from app.domain.rec_system_bid_math.hour_observation_builder import (
    BidBucketObservation,
)
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
    def _mode_filter_clause(mode: str | None) -> str:
        """Собрать SQL-фильтр по mode только для конкретного режима."""
        return "" if mode is None else "  AND mode = %(mode)s\n"


    @staticmethod
    def _build_bid_bucket_observations_from_ch_rows(
        rows: list[dict[str, object]],
    ) -> list[BidBucketObservation]:
        """Build 15-minute bucket observations from CH rows.

        Rows are grouped by the full bucket context:
            (bucket_start, bid_minor, price_minor).
        """
        grouped: dict[tuple[datetime, int, int | None], list[dict[str, object]]] = {}
        for row in rows:
            bucket_start = row.get("bucket_start")
            if not isinstance(bucket_start, datetime):
                raise KeyError("row is missing bucket_start")
            bid_value = row.get("bid_minor", row.get("bid"))
            if bid_value is None:
                raise KeyError("row is missing bid_minor/bid")
            price_value = row.get("price_minor")
            key = (
                bucket_start,
                int(cast(Any, bid_value)),
                None if price_value is None else int(cast(Any, price_value)),
            )
            grouped.setdefault(key, []).append(row)

        observations: list[BidBucketObservation] = []
        for (bucket_start, bid_minor, price_minor), bucket_rows in grouped.items():
            impressions_sum = 0.0
            for row in bucket_rows:
                impressions_value = row.get("delta_impressions", row.get("impressions"))
                if impressions_value is None:
                    raise KeyError("row is missing delta_impressions/impressions")
                impressions_sum += float(cast(Any, impressions_value))

            if impressions_sum < 0:
                continue

            observations.append(
                BidBucketObservation(
                    bid=bid_minor,
                    bucket_start=bucket_start,
                    impressions=impressions_sum,
                    price_minor=price_minor,
                )
            )

        return observations

    @staticmethod
    def _to_int(value: object) -> int:
        """Безопасно привести значение CH к int."""
        if isinstance(value, bool):
            return int(value)
        if isinstance(value, int):
            return value
        if isinstance(value, float):
            return int(value)
        if isinstance(value, str):
            return int(value)
        raise TypeError(f"Cannot cast to int: {type(value)!r}")

    @staticmethod
    def _to_float(value: object) -> float:
        """Безопасно привести значение CH к float."""
        if isinstance(value, bool):
            return float(int(value))
        if isinstance(value, int | float):
            return float(value)
        if isinstance(value, str):
            return float(value)
        raise TypeError(f"Cannot cast to float: {type(value)!r}")

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

    async def fetch_rec_bid_bucket_observations_for_nmid(
        self,
        nmid: int,
        mode: str | None,
        date_from: datetime,
        date_to: datetime,
    ) -> list[BidBucketObservation]:
        """Собрать read-only bucket-строки для rec bid recommendation.

        Args:
            mode: Аналитический mode-фильтр; None = all modes.
        """
        query = self._load_sql("fetch_rec_bid_bucket_rows.sql").replace(
            "  -- MODE_FILTER\n",
            self._mode_filter_clause(mode),
        )
        params: dict[str, object] = {
            "nmid": nmid,
            "date_from": date_from,
            "date_to": date_to,
        }
        if mode is not None:
            params["mode"] = mode
        async with anti_ch_crash_semaphore:
            async with get_clickhouse_client() as client:
                result: QueryResult = await client.query(query, parameters=params)
        if not result.result_rows:
            return []
        raw_column_names = cast(
            tuple[object, ...],
            result.column_names,  # pyright: ignore[reportUnknownMemberType]
        )
        column_names = [str(name) for name in raw_column_names]
        rows = [dict(zip(column_names, tuple(row))) for row in result.result_rows]
        return self._build_bid_bucket_observations_from_ch_rows(rows)

    async def fetch_rec_bid_ctr_by_bid_for_nmid(
        self,
        nmid: int,
        mode: str | None,
        date_from: datetime,
        date_to: datetime,
    ) -> dict[int, float]:
        """Вернуть CTR по bid для read-only recommendation.

        Args:
            mode: Аналитический mode-фильтр; None = all modes.
        """
        query = self._load_sql("fetch_rec_bid_ctr_by_bid.sql").replace(
            "  -- MODE_FILTER\n",
            self._mode_filter_clause(mode),
        )
        params: dict[str, object] = {
            "nmid": nmid,
            "date_from": date_from,
            "date_to": date_to,
        }
        if mode is not None:
            params["mode"] = mode
        async with anti_ch_crash_semaphore:
            async with get_clickhouse_client() as client:
                result: QueryResult = await client.query(query, parameters=params)
        if not result.result_rows:
            return {}
        raw_column_names = cast(
            tuple[object, ...],
            result.column_names,  # pyright: ignore[reportUnknownMemberType]
        )
        column_names = [str(name) for name in raw_column_names]
        ctr_by_bid: dict[int, float] = {}
        for row in result.result_rows:
            row_dict = dict(zip(column_names, tuple(row)))
            bid = self._to_int(row_dict["bid"])
            impressions = self._to_float(row_dict["impressions"])
            clicks = self._to_float(row_dict["clicks"])
            ctr_by_bid[bid] = clicks / impressions if impressions > 0 else 0.0
        return ctr_by_bid

    async def fetch_rec_bid_click_to_order_cr_7d_for_nmid(
        self,
        nmid: int,
        mode: str | None,
        date_from: datetime,
        date_to: datetime,
    ) -> float:
        """Вернуть 7d click-to-order CR для PlanContext recommendation.

        Args:
            mode: Аналитический mode-фильтр; None = all modes.
        """
        query = self._load_sql("fetch_rec_bid_click_to_order_cr_7d.sql").replace(
            "  -- MODE_FILTER\n",
            self._mode_filter_clause(mode),
        )
        params: dict[str, object] = {
            "nmid": nmid,
            "date_from": date_from,
            "date_to": date_to,
        }
        if mode is not None:
            params["mode"] = mode
        async with anti_ch_crash_semaphore:
            async with get_clickhouse_client() as client:
                result: QueryResult = await client.query(query, parameters=params)
        if not result.result_rows:
            return 0.0
        raw_column_names = cast(
            tuple[object, ...],
            result.column_names,  # pyright: ignore[reportUnknownMemberType]
        )
        column_names = [str(name) for name in raw_column_names]
        row_dict = dict(zip(column_names, tuple(result.result_rows[0])))
        clicks = self._to_float(row_dict["clicks"])
        orders = self._to_float(row_dict["orders"])
        return orders / clicks if clicks > 0 else 0.0

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

