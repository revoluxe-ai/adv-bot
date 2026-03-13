"""ClickHouse manager for raise card analyze: k regression, series, buckets, spread, tail_share."""

from __future__ import annotations

import math
from datetime import date, datetime
from typing import Any

from app.core.clickhouse_manager.base_clickhouse_manager import BaseClickHouseManager
from app.utils.ch_semaphore import anti_ch_crash_semaphore
from app.utils.click_house.client import get_clickhouse_client

from .constants import (
    BID_CAP,
    CORR_MIN_POINTS,
    CORR_MIN_SUM_D,
    POS_CAP,
    SPREAD_MIN_ROWS,
)
from .dto import DayPoint, WeekPoint


class RaiseCardAnalyzeClickHouseManager(BaseClickHouseManager):
    """Fetches k, series, buckets, spread, tail_share from bid_decision_log."""

    async def estimate_k_item(
        self,
        adv_id: int,
        nmid: int,
        window_days: int,
        min_d_views: int,
    ) -> dict[str, Any] | None:
        """One row: k, b, corr_ln, rows_used, keys_used, spread_ok."""
        query = self._get_query("estimate_k_item")
        async with anti_ch_crash_semaphore:
            async with get_clickhouse_client() as client:
                response = await client.query(
                    query,
                    parameters={
                        "adv_id": adv_id,
                        "nmid": nmid,
                        "window_days": window_days,
                        "min_d_views": min_d_views,
                        "pos_cap": POS_CAP,
                        "bid_cap": BID_CAP,
                        "spread_min_rows": SPREAD_MIN_ROWS,
                    },
                )
        rows = list(response.named_results())
        if not rows:
            return None
        row = rows[0]
        if row.get("rows_used") == 0:
            return None
        return {
            "k": float(row["k"]),
            "b": float(row["b"]),
            "corr_ln": float(row["corr_ln"]) if row.get("corr_ln") is not None else None,
            "rows_used": int(row["rows_used"]),
            "keys_used": int(row["keys_used"]),
            "spread_ok_window": float(row["spread_ok"]) if row.get("spread_ok") is not None else None,
        }

    async def estimate_k_adv(
        self,
        adv_id: int,
        window_days: int,
        min_d_views: int,
    ) -> dict[str, Any] | None:
        query = self._get_query("estimate_k_adv")
        async with anti_ch_crash_semaphore:
            async with get_clickhouse_client() as client:
                response = await client.query(
                    query,
                    parameters={
                        "adv_id": adv_id,
                        "window_days": window_days,
                        "min_d_views": min_d_views,
                        "pos_cap": POS_CAP,
                        "bid_cap": BID_CAP,
                        "spread_min_rows": SPREAD_MIN_ROWS,
                    },
                )
        rows = list(response.named_results())
        if not rows or rows[0].get("rows_used") == 0:
            return None
        row = rows[0]
        return {
            "k": float(row["k"]),
            "b": float(row["b"]),
            "corr_ln": float(row["corr_ln"]) if row.get("corr_ln") is not None else None,
            "rows_used": int(row["rows_used"]),
            "keys_used": int(row["keys_used"]),
            "spread_ok_window": float(row["spread_ok"]) if row.get("spread_ok") is not None else None,
        }

    async def estimate_k_category(
        self,
        wb_category: str,
        window_days: int,
        min_d_views: int,
    ) -> dict[str, Any] | None:
        if not wb_category:
            return None
        query = self._get_query("estimate_k_category")
        async with anti_ch_crash_semaphore:
            async with get_clickhouse_client() as client:
                response = await client.query(
                    query,
                    parameters={
                        "wb_category": wb_category,
                        "window_days": window_days,
                        "min_d_views": min_d_views,
                        "pos_cap": POS_CAP,
                        "bid_cap": BID_CAP,
                        "spread_min_rows": SPREAD_MIN_ROWS,
                    },
                )
        rows = list(response.named_results())
        if not rows or rows[0].get("rows_used") == 0:
            return None
        row = rows[0]
        return {
            "k": float(row["k"]),
            "b": float(row["b"]),
            "corr_ln": float(row["corr_ln"]) if row.get("corr_ln") is not None else None,
            "rows_used": int(row["rows_used"]),
            "keys_used": int(row["keys_used"]),
            "spread_ok_window": float(row["spread_ok"]) if row.get("spread_ok") is not None else None,
        }

    async def estimate_k_global(
        self,
        window_days: int,
        min_d_views: int,
    ) -> dict[str, Any] | None:
        query = self._get_query("estimate_k_global")
        async with anti_ch_crash_semaphore:
            async with get_clickhouse_client() as client:
                response = await client.query(
                    query,
                    parameters={
                        "window_days": window_days,
                        "min_d_views": min_d_views,
                        "pos_cap": POS_CAP,
                        "bid_cap": BID_CAP,
                        "spread_min_rows": SPREAD_MIN_ROWS,
                    },
                )
        rows = list(response.named_results())
        if not rows or rows[0].get("rows_used") == 0:
            return None
        row = rows[0]
        return {
            "k": float(row["k"]),
            "b": float(row["b"]),
            "corr_ln": float(row["corr_ln"]) if row.get("corr_ln") is not None else None,
            "rows_used": int(row["rows_used"]),
            "keys_used": int(row["keys_used"]),
            "spread_ok_window": float(row["spread_ok"]) if row.get("spread_ok") is not None else None,
        }

    async def get_spread_recent_item(self, adv_id: int, nmid: int) -> tuple[float | None, int]:
        """Returns (spread, rows_recent). spread is None if rows_recent < SPREAD_MIN_ROWS."""
        query = self._get_query("spread_recent_item")
        async with anti_ch_crash_semaphore:
            async with get_clickhouse_client() as client:
                response = await client.query(
                    query,
                    parameters={
                        "adv_id": adv_id,
                        "nmid": nmid,
                        "bid_cap": BID_CAP,
                        "spread_min_rows": SPREAD_MIN_ROWS,
                    },
                )
        rows = list(response.named_results())
        if not rows:
            return (None, 0)
        row = rows[0]
        rows_recent = int(row["rows_recent"])
        spread = float(row["spread"]) if row.get("spread") is not None else None
        return (spread, rows_recent)

    async def get_spread_recent_adv(self, adv_id: int) -> tuple[float | None, int]:
        query = self._get_query("spread_recent_adv")
        async with anti_ch_crash_semaphore:
            async with get_clickhouse_client() as client:
                response = await client.query(
                    query,
                    parameters={
                        "adv_id": adv_id,
                        "bid_cap": BID_CAP,
                        "spread_min_rows": SPREAD_MIN_ROWS,
                    },
                )
        rows = list(response.named_results())
        if not rows:
            return (None, 0)
        row = rows[0]
        rows_recent = int(row["rows_recent"])
        spread = float(row["spread"]) if row.get("spread") is not None else None
        return (spread, rows_recent)

    async def get_wb_category(
        self,
        adv_id: int,
        nmid: int,
        window_days: int,
    ) -> str | None:
        query = self._get_query("get_wb_category")
        async with anti_ch_crash_semaphore:
            async with get_clickhouse_client() as client:
                response = await client.query(
                    query,
                    parameters={"adv_id": adv_id, "nmid": nmid, "window_days": window_days},
                )
        rows = list(response.named_results())
        if not rows or rows[0].get("wb_category") is None:
            return None
        return str(rows[0]["wb_category"]).strip() or None

    def _parse_date(self, value: Any) -> date:
        if isinstance(value, date) and not isinstance(value, datetime):
            return value
        if isinstance(value, datetime):
            return value.date()
        if hasattr(value, "date"):
            return value.date()
        return date.fromisoformat(str(value)[:10])

    async def get_daily_series(
        self,
        adv_id: int,
        nmid: int,
        k_used: float,
        series_days: int,
        min_d_views: int,
    ) -> list[DayPoint]:
        query = self._get_query("daily_series")
        async with anti_ch_crash_semaphore:
            async with get_clickhouse_client() as client:
                response = await client.query(
                    query,
                    parameters={
                        "adv_id": adv_id,
                        "nmid": nmid,
                        "k_used": k_used,
                        "series_days": series_days,
                        "min_d_views": min_d_views,
                        "pos_cap": POS_CAP,
                        "bid_cap": BID_CAP,
                    },
                )
        result: list[DayPoint] = []
        for row in response.named_results():
            result.append(
                DayPoint(
                    day=self._parse_date(row["day"]),
                    strength_index_med=float(row["strength_index_med"]),
                    sum_d=float(row["sum_d"]),
                    sum_w=float(row["sum_w"]),
                    rows_filtered=int(row["rows_filtered"]),
                    keys_filtered=int(row["keys_filtered"]),
                )
            )
        return result

    async def get_weekly_series(
        self,
        adv_id: int,
        nmid: int,
        k_used: float,
        series_days: int,
        min_d_views: int,
    ) -> list[WeekPoint]:
        query = self._get_query("weekly_series")
        async with anti_ch_crash_semaphore:
            async with get_clickhouse_client() as client:
                response = await client.query(
                    query,
                    parameters={
                        "adv_id": adv_id,
                        "nmid": nmid,
                        "k_used": k_used,
                        "series_days": series_days,
                        "min_d_views": min_d_views,
                        "pos_cap": POS_CAP,
                        "bid_cap": BID_CAP,
                    },
                )
        result: list[WeekPoint] = []
        for row in response.named_results():
            result.append(
                WeekPoint(
                    week_start=self._parse_date(row["week_start"]),
                    strength_index_med=float(row["strength_index_med"]),
                    sum_d=float(row["sum_d"]),
                    sum_w=float(row["sum_w"]),
                    rows_filtered=int(row["rows_filtered"]),
                    keys_filtered=int(row["keys_filtered"]),
                )
            )
        return result

    async def get_buckets(
        self,
        adv_id: int,
        nmid: int,
        min_d_views: int,
    ) -> list[dict[str, Any]]:
        query = self._get_query("buckets")
        async with anti_ch_crash_semaphore:
            async with get_clickhouse_client() as client:
                response = await client.query(
                    query,
                    parameters={
                        "adv_id": adv_id,
                        "nmid": nmid,
                        "min_d_views": min_d_views,
                        "pos_cap": POS_CAP,
                        "bid_cap": BID_CAP,
                    },
                )
        return [dict(r) for r in response.named_results()]

    async def get_tail_share(
        self,
        adv_id: int,
        nmid: int,
        last_days: int,
        min_d_views: int,
    ) -> tuple[float, float, int]:
        """Returns (tail_share, median_pos, rows_count)."""
        query = self._get_query("tail_share_last_period")
        async with anti_ch_crash_semaphore:
            async with get_clickhouse_client() as client:
                response = await client.query(
                    query,
                    parameters={
                        "adv_id": adv_id,
                        "nmid": nmid,
                        "last_days": last_days,
                        "min_d_views": min_d_views,
                        "pos_cap": float(POS_CAP),
                    },
                )
        rows = list(response.named_results())
        if not rows:
            return (0.0, 0.0, 0)
        row = rows[0]
        return (
            float(row["tail_share"] or 0),
            float(row["median_pos"] or 0),
            int(row["rows_count"] or 0),
        )

    async def get_corr_aggregates_item(
        self,
        adv_id: int,
        nmid: int,
        window_days: int,
    ) -> list[tuple[float, float, float]]:
        """Returns list of (ln_bid_median, ln_pos_median, weight=sum_d) for points with sum_d >= CORR_MIN_SUM_D."""
        query = self._get_query("corr_aggregates_item")
        async with anti_ch_crash_semaphore:
            async with get_clickhouse_client() as client:
                response = await client.query(
                    query,
                    parameters={
                        "adv_id": adv_id,
                        "nmid": nmid,
                        "window_days": window_days,
                        "pos_cap": POS_CAP,
                        "bid_cap": BID_CAP,
                        "corr_min_sum_d": float(CORR_MIN_SUM_D),
                    },
                )
        points: list[tuple[float, float, float]] = []
        for row in response.named_results():
            bid_med = float(row["bid_median"])
            pos_med = float(row["pos_median"])
            sum_d = float(row["sum_d"])
            if bid_med <= 0 or pos_med <= 0:
                continue
            points.append((math.log(bid_med), math.log(pos_med), sum_d))
        return points

    @staticmethod
    def weighted_correlation(
        points: list[tuple[float, float, float]],
    ) -> float | None:
        """Weighted Pearson correlation. points = (x, y, weight). Returns None if < CORR_MIN_POINTS."""
        if len(points) < CORR_MIN_POINTS:
            return None
        total_w = sum(p[2] for p in points)
        if total_w <= 0:
            return None
        mean_x = sum(p[0] * p[2] for p in points) / total_w
        mean_y = sum(p[1] * p[2] for p in points) / total_w
        cov = sum((p[0] - mean_x) * (p[1] - mean_y) * p[2] for p in points) / total_w
        var_x = sum((p[0] - mean_x) ** 2 * p[2] for p in points) / total_w
        var_y = sum((p[1] - mean_y) ** 2 * p[2] for p in points) / total_w
        if var_x <= 0 or var_y <= 0:
            return None
        return cov / math.sqrt(var_x * var_y)
