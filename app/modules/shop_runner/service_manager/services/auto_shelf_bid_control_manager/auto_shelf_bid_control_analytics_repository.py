"""ClickHouse-аналитика по auto_shelf intervals для control-контура."""

from __future__ import annotations
import logging
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, cast

from clickhouse_connect.driver.query import QueryResult

from app.domain.rec_system_bid_math.hour_observation_builder import (
    BidBucketObservation,
    build_hour_observations_from_buckets,
)
from app.utils.ch_semaphore import anti_ch_crash_semaphore
from app.utils.click_house.client import get_clickhouse_client

from ..auto_shelf_bid_increment_manager.bid_bucket_row_mapper import (
    build_bid_bucket_observations_from_ch_rows,
)
from .bid_coverage_selector import BidCoverage
from .bid_units import cpc_from_totals
from .dto import BidStatsDTO

logger = logging.getLogger(__name__)


class AutoShelfBidControlAnalyticsRepository:
    """Чтение дедуп-метрик по точкам ставки из auto_shelf_bid_intervals."""

    def __init__(self) -> None:
        self._sql_dir = Path(__file__).parent.joinpath("sql")

    def _load_sql(self, filename: str) -> str:
        """Прочитать SQL-шаблон из каталога sql/."""
        return self._sql_dir.joinpath(filename).read_text(encoding="utf-8")

    @staticmethod
    def _result_column_names(result: QueryResult) -> list[str]:
        """Нормализовать имена колонок CH в явный список строк."""
        raw_column_names = cast(tuple[Any, ...], getattr(result, "column_names"))
        column_names: list[str] = []
        for name in raw_column_names:
            column_names.append(str(name))
        return column_names

    @staticmethod
    def _mode_filter_clause(mode: str | None) -> str:
        """Собрать SQL-фильтр по mode только для конкретного режима."""
        return "" if mode is None else "  AND mode = %(mode)s\n"

    @staticmethod
    def _filter_buckets_by_price_minor(
        buckets: list[BidBucketObservation],
        *,
        price_minor: int | None,
    ) -> list[BidBucketObservation]:
        """Оставить только bucket-наблюдения точного price-контекста."""
        if price_minor is None:
            return [bucket for bucket in buckets if bucket.price_minor is None]
        normalized = int(price_minor)
        return [bucket for bucket in buckets if bucket.price_minor == normalized]

    @staticmethod
    def _price_filter_clause(price_minor: int | None) -> str:
        """Собрать SQL-фильтр по точному price-контексту."""
        if price_minor is None:
            return "  AND price_minor IS NULL\n"
        return "  AND price_minor = %(price_minor)s\n"

    def _bucket_rows_query(
        self,
        *,
        mode: str | None,
        price_minor: int | None,
    ) -> str:
        """Построить SQL чтения bucket-строк для coverage-контекста."""
        return (
            "SELECT\n"
            "    event_id,\n"
            "    version,\n"
            "    mode,\n"
            "    bucket_start,\n"
            "    bid_minor,\n"
            "    price_minor,\n"
            "    delta_impressions,\n"
            "    delta_clicks,\n"
            "    delta_orders,\n"
            "    delta_spend\n"
            "FROM default_db.auto_shelf_bid_intervals\n"
            "WHERE nmid = %(nmid)s\n"
            "  AND currency = %(currency)s\n"
            "  AND bucket_start >= %(date_from)s\n"
            "  AND bucket_start < %(date_to)s\n"
            "  AND delta_impressions IS NOT NULL\n"
            f"{self._price_filter_clause(price_minor)}"
            f"{self._mode_filter_clause(mode)}"
            "ORDER BY bucket_start ASC\n"
        )

    @staticmethod
    def _normalize_click_to_order_cr(value: float) -> float:
        """Нормализовать CR клики->заказы в безопасный диапазон [0, 1]."""
        if value < 0.0:
            return 0.0
        if value > 1.0:
            logger.debug(
                "click_to_order_cr_7d_capped_to_one",
                extra={"raw_click_to_order_cr_7d": value},
            )
            return 1.0
        return value


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
        column_names = self._result_column_names(result)
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
        return build_bid_bucket_observations_from_ch_rows(rows)

    async def _fetch_bucket_observations_for_coverage_context(
        self,
        *,
        nmid: int,
        date_from: datetime,
        date_to: datetime,
        currency: str,
        price_minor: int | None,
        mode: str | None = None,
    ) -> list[BidBucketObservation]:
        """Прочитать bucket-наблюдения точного coverage-контекста."""
        query = self._bucket_rows_query(mode=mode, price_minor=price_minor)
        params: dict[str, object] = {
            "nmid": nmid,
            "currency": currency,
            "date_from": date_from,
            "date_to": date_to,
        }
        if price_minor is not None:
            params["price_minor"] = int(price_minor)
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
        return build_bid_bucket_observations_from_ch_rows(rows)

    async def get_first_available_bid_bucket_start(
        self,
        *,
        nmid: int,
        currency: str,
        price_minor: int | None,
        mode: str | None = None,
    ) -> datetime | None:
        """Вернуть первый доступный bucket_start точного coverage-контекста."""
        query = (
            "SELECT minOrNull(bucket_start) AS first_bucket_start\n"
            "FROM default_db.auto_shelf_bid_intervals\n"
            "WHERE nmid = %(nmid)s\n"
            "  AND currency = %(currency)s\n"
            "  AND delta_impressions IS NOT NULL\n"
            f"{self._price_filter_clause(price_minor)}"
            f"{self._mode_filter_clause(mode)}"
        )
        params: dict[str, object] = {
            "nmid": nmid,
            "currency": currency,
        }
        if price_minor is not None:
            params["price_minor"] = int(price_minor)
        if mode is not None:
            params["mode"] = mode
        async with anti_ch_crash_semaphore:
            async with get_clickhouse_client() as client:
                result: QueryResult = await client.query(query, parameters=params)
        if not result.result_rows:
            return None
        raw = result.result_rows[0][0]
        if raw is None:
            return None
        if isinstance(raw, datetime):
            return raw
        return datetime.fromisoformat(str(raw))

    async def get_bid_coverages(
        self,
        *,
        nmid: int,
        date_from: datetime,
        date_to: datetime,
        currency: str,
        price_minor: int | None,
        mode: str | None = None,
    ) -> list[BidCoverage]:
        """Вернуть накопленное coverage по bid_minor: показы и валидные часы."""
        scoped_buckets = await self._fetch_bucket_observations_for_coverage_context(
            nmid=nmid,
            date_from=date_from,
            date_to=date_to,
            currency=currency,
            price_minor=price_minor,
            mode=mode,
        )
        scoped_buckets = self._filter_buckets_by_price_minor(
            scoped_buckets,
            price_minor=price_minor,
        )
        if not scoped_buckets:
            return []
        hours = build_hour_observations_from_buckets(scoped_buckets)
        if not hours:
            return []
        impressions_by_bid: dict[int, int] = defaultdict(int)
        valid_hours_by_bid: dict[int, int] = defaultdict(int)
        for observation in hours:
            impressions_by_bid[int(observation.bid)] += int(observation.impressions_sum)
            valid_hours_by_bid[int(observation.bid)] += int(
                observation.valid_hours_count
            )
        all_bids = sorted(set(impressions_by_bid) | set(valid_hours_by_bid))
        return [
            BidCoverage(
                bid_minor=bid,
                impressions=impressions_by_bid.get(bid, 0),
                valid_hours=valid_hours_by_bid.get(bid, 0),
            )
            for bid in all_bids
        ]

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
        raw_click_to_order_cr_7d = orders / clicks if clicks > 0 else 0.0
        return self._normalize_click_to_order_cr(raw_click_to_order_cr_7d)

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
        column_names = self._result_column_names(result)
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
        column_names = self._result_column_names(result)
        row: dict[str, Any] = dict(zip(column_names, tuple(result.result_rows[0])))
        return self._build_bid_stats_dto(row)
