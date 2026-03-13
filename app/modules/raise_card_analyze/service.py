"""Campaign growth analysis service: resolve_k, series, trend, confidence, buckets."""

from __future__ import annotations

import math
from dataclasses import dataclass
from datetime import date, datetime
from typing import Any

from .constants import (
    K_MIN_ABS,
    LOW_CORR_ABS,
    MIN_D_VIEWS_COLD,
    MIN_D_VIEWS_NORMAL,
    MIN_ROWS_FOR_K,
    MIN_ROWS_FOR_SIGN,
    POS_CAP,
    ROWS_WEEK_WARN,
    SERIES_DAYS_COLD,
    SERIES_WEEKS_NORMAL,
    SPREAD_MIN_ROWS,
    SPREAD_OK_MIN,
    SUM_D_WEEK_FAIL,
    TAIL_MODE_THRESHOLD,
    TAIL_TREND_THRESHOLD,
    TREND_VERDICT_THRESHOLD,
    WINDOW_DAYS_FOR_K_COLD,
    WINDOW_DAYS_FOR_K_NORMAL,
)
from .dto import (
    BucketPoint,
    BucketsResult,
    Confidence,
    DayPoint,
    KResult,
    TrendResult,
    TrendVerdict,
    WeekPoint,
)
from .clickhouse_manager import RaiseCardAnalyzeClickHouseManager


@dataclass
class QualityGateResult:
    """Result of quality_gate check."""

    fail: bool  # sum_d_week < 100
    warn: bool  # rows_week < 30 with sum_d >= 100
    message: str


def _weak_reasons(
    k: float,
    rows_used: int,
    spread_used_recent: float | None,
    corr_ln: float | None,
    k_source: str,
) -> tuple[str, ...]:
    """Build weak_reasons in order: low_spread, wrong_sign, flat_k, low_corr (item/adv only)."""
    reasons: list[str] = []
    if spread_used_recent is not None and spread_used_recent < SPREAD_OK_MIN and rows_used >= SPREAD_MIN_ROWS:
        reasons.append("low_spread")
    if k >= 0 and rows_used >= MIN_ROWS_FOR_SIGN:
        reasons.append("wrong_sign")
    if abs(k) < K_MIN_ABS and rows_used >= MIN_ROWS_FOR_K:
        reasons.append("flat_k")
    if k_source in ("item", "adv") and corr_ln is not None and abs(corr_ln) < LOW_CORR_ABS:
        reasons.append("low_corr")
    return tuple(reasons)


class CampaignGrowthAnalysisService:
    """Orchestrates CH manager for k, series, trend, confidence, buckets."""

    def __init__(self, ch_manager: RaiseCardAnalyzeClickHouseManager) -> None:
        self._ch = ch_manager

    def quality_gate(
        self,
        rows_week: int,
        sum_d_week: float,
        k_is_weak: bool,
    ) -> QualityGateResult:
        """Before verdict: fail if sum_d_week < 100; warn if rows_week < 30 (when sum_d >= 100)."""
        if sum_d_week < SUM_D_WEEK_FAIL:
            return QualityGateResult(fail=True, warn=False, message="Недостаточно трафика")
        if rows_week < ROWS_WEEK_WARN:
            return QualityGateResult(fail=False, warn=True, message="мало точек")
        if k_is_weak:
            return QualityGateResult(fail=False, warn=False, message="Нельзя оценить эффект ставки")
        return QualityGateResult(fail=False, warn=False, message="")

    async def resolve_k(
        self,
        adv_id: int,
        nmid: int,
        *,
        is_cold: bool,
    ) -> KResult:
        """Resolve k from item → adv → category → global. Fetches wb_category if needed."""
        window_days = WINDOW_DAYS_FOR_K_COLD if is_cold else WINDOW_DAYS_FOR_K_NORMAL
        min_d = MIN_D_VIEWS_COLD if is_cold else MIN_D_VIEWS_NORMAL

        # Spread for weak_reasons: last 14 days, min_d=1
        spread_item, rows_recent_item = await self._ch.get_spread_recent_item(adv_id, nmid)
        spread_adv, rows_recent_adv = await self._ch.get_spread_recent_adv(adv_id)
        spread_used_recent: float | None = spread_item if (rows_recent_item >= SPREAD_MIN_ROWS) else (spread_adv if (rows_recent_adv >= SPREAD_MIN_ROWS) else None)

        # Item
        item = await self._ch.estimate_k_item(adv_id, nmid, window_days, min_d)
        if item and item["rows_used"] >= 300 and (item.get("spread_ok_window") or 0) >= SPREAD_OK_MIN:
            corr_ln: float | None = None
            agg = await self._ch.get_corr_aggregates_item(adv_id, nmid, window_days)
            if len(agg) >= 200:
                corr_ln = self._ch.weighted_correlation(agg)
            weak = _weak_reasons(item["k"], item["rows_used"], spread_used_recent, corr_ln, "item")
            return KResult(
                k=item["k"],
                b=item["b"],
                corr_ln=corr_ln,
                k_source="item",
                spread_ok_window=item.get("spread_ok_window"),
                spread_used_recent=spread_used_recent,
                k_is_weak=len(weak) > 0,
                weak_reasons=weak,
                window_days=window_days,
                rows_used=item["rows_used"],
                keys_used=item["keys_used"],
            )

        # Adv
        adv = await self._ch.estimate_k_adv(adv_id, window_days, min_d)
        if adv and adv["rows_used"] >= 1000 and (adv.get("corr_ln") is not None and abs(adv["corr_ln"]) >= 0.1):
            weak = _weak_reasons(adv["k"], adv["rows_used"], spread_used_recent, adv.get("corr_ln"), "adv")
            return KResult(
                k=adv["k"],
                b=adv["b"],
                corr_ln=adv.get("corr_ln"),
                k_source="adv",
                spread_ok_window=adv.get("spread_ok_window"),
                spread_used_recent=spread_used_recent,
                k_is_weak=len(weak) > 0,
                weak_reasons=weak,
                window_days=window_days,
                rows_used=adv["rows_used"],
                keys_used=adv["keys_used"],
            )

        # Category
        wb_category: str | None = await self._ch.get_wb_category(adv_id, nmid, window_days)
        if wb_category:
            cat = await self._ch.estimate_k_category(wb_category, window_days, min_d)
            if cat and cat["rows_used"] >= 5000 and (cat.get("corr_ln") is not None and abs(cat["corr_ln"]) >= 0.05):
                weak = _weak_reasons(cat["k"], cat["rows_used"], spread_used_recent, None, "category")
                return KResult(
                    k=cat["k"],
                    b=cat["b"],
                    corr_ln=cat.get("corr_ln"),
                    k_source="category",
                    spread_ok_window=cat.get("spread_ok_window"),
                    spread_used_recent=spread_used_recent,
                    k_is_weak=len(weak) > 0,
                    weak_reasons=weak,
                    window_days=window_days,
                    rows_used=cat["rows_used"],
                    keys_used=cat["keys_used"],
                )

        # Global
        gl = await self._ch.estimate_k_global(window_days, min_d)
        if gl:
            weak = _weak_reasons(gl["k"], gl["rows_used"], spread_used_recent, None, "global")
            return KResult(
                k=gl["k"],
                b=gl["b"],
                corr_ln=gl.get("corr_ln"),
                k_source="global",
                spread_ok_window=gl.get("spread_ok_window"),
                spread_used_recent=spread_used_recent,
                k_is_weak=len(weak) > 0,
                weak_reasons=weak,
                window_days=window_days,
                rows_used=gl["rows_used"],
                keys_used=gl["keys_used"],
            )

        # Fallback: use item or adv even if below thresholds, with weak
        if item:
            corr_ln = None
            agg = await self._ch.get_corr_aggregates_item(adv_id, nmid, window_days)
            if len(agg) >= 200:
                corr_ln = self._ch.weighted_correlation(agg)
            weak = _weak_reasons(item["k"], item["rows_used"], spread_used_recent, corr_ln, "item")
            return KResult(
                k=item["k"],
                b=item["b"],
                corr_ln=corr_ln,
                k_source="item",
                spread_ok_window=item.get("spread_ok_window"),
                spread_used_recent=spread_used_recent,
                k_is_weak=True,
                weak_reasons=weak,
                window_days=window_days,
                rows_used=item["rows_used"],
                keys_used=item["keys_used"],
            )
        if adv:
            weak = _weak_reasons(adv["k"], adv["rows_used"], spread_used_recent, adv.get("corr_ln"), "adv")
            return KResult(
                k=adv["k"],
                b=adv["b"],
                corr_ln=adv.get("corr_ln"),
                k_source="adv",
                spread_ok_window=adv.get("spread_ok_window"),
                spread_used_recent=spread_used_recent,
                k_is_weak=True,
                weak_reasons=weak,
                window_days=window_days,
                rows_used=adv["rows_used"],
                keys_used=adv["keys_used"],
            )
        if gl:
            weak = _weak_reasons(gl["k"], gl["rows_used"], spread_used_recent, None, "global")
            return KResult(
                k=gl["k"],
                b=gl["b"],
                corr_ln=gl.get("corr_ln"),
                k_source="global",
                spread_ok_window=gl.get("spread_ok_window"),
                spread_used_recent=spread_used_recent,
                k_is_weak=True,
                weak_reasons=weak,
                window_days=window_days,
                rows_used=gl["rows_used"],
                keys_used=gl["keys_used"],
            )

        # No data at all: return a dummy weak result
        return KResult(
            k=0.0,
            b=0.0,
            corr_ln=None,
            k_source="global",
            spread_ok_window=None,
            spread_used_recent=spread_used_recent,
            k_is_weak=True,
            weak_reasons=("low_spread",) if spread_used_recent is not None and spread_used_recent < SPREAD_OK_MIN else (),
            window_days=window_days,
            rows_used=0,
            keys_used=0,
        )

    async def compute_daily_series(
        self,
        adv_id: int,
        nmid: int,
        k_used: float,
        *,
        is_cold: bool,
        min_d_views_override: int | None = None,
    ) -> tuple[list[DayPoint], int]:
        """Daily series 14 days. Returns (points, min_d_used). Fallback to min_d=1 if empty."""
        min_d = min_d_views_override if min_d_views_override is not None else (MIN_D_VIEWS_COLD if is_cold else MIN_D_VIEWS_NORMAL)
        points = await self._ch.get_daily_series(adv_id, nmid, k_used, SERIES_DAYS_COLD, min_d)
        if not points and min_d != 1:
            points = await self._ch.get_daily_series(adv_id, nmid, k_used, SERIES_DAYS_COLD, 1)
            min_d = 1
        return (points, min_d)

    async def compute_weekly_series(
        self,
        adv_id: int,
        nmid: int,
        k_used: float,
        *,
        min_d_views_override: int | None = None,
    ) -> tuple[list[WeekPoint], int]:
        """Weekly series 8 weeks. Fallback to min_d=1 if empty."""
        min_d = min_d_views_override if min_d_views_override is not None else MIN_D_VIEWS_NORMAL
        series_days = 56  # 8 weeks
        points = await self._ch.get_weekly_series(adv_id, nmid, k_used, series_days, min_d)
        if not points and min_d != 1:
            points = await self._ch.get_weekly_series(adv_id, nmid, k_used, series_days, 1)
            min_d = 1
        return (points, min_d)

    def compute_trend(
        self,
        series: list[DayPoint] | list[WeekPoint],
        mode: str,
        k_is_weak: bool,
        is_noisy_mode: bool,
        tail_mode: bool,
        *,
        is_cold: bool,
    ) -> TrendResult | None:
        """Trend from series. Returns None if is_noisy_mode or k_is_weak."""
        if is_noisy_mode or k_is_weak:
            return None
        threshold = TAIL_TREND_THRESHOLD if tail_mode else TREND_VERDICT_THRESHOLD
        if not series:
            return None
        if isinstance(series[0], DayPoint):
            day_series = series
            if len(day_series) < 14:
                return None
            last7 = day_series[-7:]
            prev7 = day_series[-14:-7]
            if not last7 or not prev7:
                return None
            last_med = float(_median([p.strength_index_med for p in last7]))
            prev_med = float(_median([p.strength_index_med for p in prev7]))
            if prev_med == 0:
                change_pct = 0.0
            else:
                change_pct = (last_med - prev_med) / abs(prev_med)
            verdict = _verdict_from_change(change_pct, threshold)
            return TrendResult(
                verdict=verdict,
                change_pct=change_pct * 100,
                last_median=last_med,
                prev_median=prev_med,
                trend_days=14,
                mode="last_7_vs_prev_7",
            )
        # Normal: week_over_week
        week_series = series
        if len(week_series) < 2:
            return None
        last_w = week_series[-1]
        prev_w = week_series[-2]
        last_med = last_w.strength_index_med
        prev_med = prev_w.strength_index_med
        if prev_med == 0:
            change_pct = 0.0
        else:
            change_pct = (last_med - prev_med) / abs(prev_med)
        verdict = _verdict_from_change(change_pct, threshold)
        return TrendResult(
            verdict=verdict,
            change_pct=change_pct * 100,
            last_median=last_med,
            prev_median=prev_med,
            trend_days=None,
            mode="week_over_week",
        )

    def compute_confidence(
        self,
        k_result: KResult,
        sum_d_week: float,
        rows_week: int,
        is_noisy_mode: bool,
        tail_mode: bool,
        tail_share: float,
        *,
        is_cold: bool,
    ) -> Confidence:
        """Confidence level and notes. k_is_weak or weak link -> max low."""
        notes: list[str] = []
        if k_result.k_is_weak:
            notes.append("Связь ставки и позиции слабая или не определена")
        if is_noisy_mode:
            notes.append("Режим шумный: min_d=1")
        if tail_mode:
            notes.append("Позиции в хвосте, точность оценки ограничена клипом")
        if sum_d_week < SUM_D_WEEK_FAIL:
            score = 0
            level = "low"
        elif rows_week < ROWS_WEEK_WARN:
            score = min(40, int(sum_d_week / 5))
            level = "low"
        elif k_result.k_is_weak or tail_mode:
            score = min(50, 20 + rows_week // 2)
            level = "low"
        else:
            score = min(100, 50 + int(sum_d_week / 20) + (10 if k_result.k_source == "item" else 0))
            level = "high" if score >= 70 else ("medium" if score >= 50 else "low")
        return Confidence(
            level=level,
            score=min(100, max(0, score)),
            k_source=k_result.k_source,
            notes=tuple(notes),
            is_noisy_mode=is_noisy_mode,
            tail_mode=tail_mode,
            tail_share=tail_share,
        )

    async def get_tail_share_last_period(
        self,
        adv_id: int,
        nmid: int,
        *,
        is_cold: bool,
        min_d_views: int,
    ) -> tuple[float, float, int]:
        """Tail share and median_pos on last period (7 days)."""
        last_days = 7
        return await self._ch.get_tail_share(adv_id, nmid, last_days, min_d_views)

    async def compute_buckets(
        self,
        adv_id: int,
        nmid: int,
        *,
        min_d_views: int = MIN_D_VIEWS_NORMAL,
    ) -> BucketsResult:
        """Top 3–5 buckets by max sum_d, tie-breaker sum_w."""
        rows = await self._ch.get_buckets(adv_id, nmid, min_d_views)
        if not rows:
            return BucketsResult(buckets=())
        sorted_rows = sorted(rows, key=lambda r: (r["sum_d"], r["sum_w"]), reverse=True)
        top = sorted_rows[:5]
        def _parse_d(d: Any) -> date:
            if isinstance(d, date) and not isinstance(d, datetime):
                return d
            if hasattr(d, "date"):
                return d.date()
            return date.fromisoformat(str(d)[:10])

        buckets = tuple(
            BucketPoint(
                week_start=_parse_d(r["week_start"]),
                bid_bucket=float(r["bid_bucket"]),
                avg_pos=float(r["avg_pos"]),
                rows=int(r["rows"]),
                sum_d=float(r["sum_d"]),
                sum_w=float(r["sum_w"]),
            )
            for r in top
        )
        return BucketsResult(buckets=buckets)

    async def run_full_analysis(
        self,
        adv_id: int,
        nmid: int,
        *,
        is_cold: bool,
    ) -> dict[str, Any]:
        """Resolve k, series, trend, confidence. Returns payload for cache and UI."""
        k_result = await self.resolve_k(adv_id, nmid, is_cold=is_cold)
        min_d_used = MIN_D_VIEWS_COLD if is_cold else MIN_D_VIEWS_NORMAL
        is_noisy_mode = False
        series: list[DayPoint] | list[WeekPoint]
        series_type: str

        if is_cold:
            series, min_d_used = await self.compute_daily_series(
                adv_id, nmid, k_result.k, is_cold=True, min_d_views_override=None
            )
            if min_d_used == 1:
                is_noisy_mode = True
            series_type = "day"
        else:
            series, min_d_used = await self.compute_weekly_series(
                adv_id, nmid, k_result.k, min_d_views_override=None
            )
            if min_d_used == 1:
                is_noisy_mode = True
            series_type = "week"

        tail_share_val, median_pos, _ = await self.get_tail_share_last_period(
            adv_id, nmid, is_cold=is_cold, min_d_views=min_d_used
        )
        tail_mode = (
            tail_share_val > TAIL_MODE_THRESHOLD
            or (median_pos > POS_CAP * 0.7)
        )

        trend = self.compute_trend(
            series,
            "last_7_vs_prev_7" if is_cold else "week_over_week",
            k_result.k_is_weak,
            is_noisy_mode,
            tail_mode,
            is_cold=is_cold,
        )

        if is_cold and series:
            last_7 = series[-7:] if len(series) >= 7 else series
            sum_d_week = sum(p.sum_d for p in last_7)
            rows_week = len(last_7)
        elif series:
            last_week_point = series[-1]
            sum_d_week = last_week_point.sum_d
            rows_week = getattr(last_week_point, "rows_filtered", 0)
        else:
            sum_d_week = 0
            rows_week = 0

        gate = self.quality_gate(rows_week, sum_d_week, k_result.k_is_weak)
        confidence = self.compute_confidence(
            k_result,
            sum_d_week,
            rows_week,
            is_noisy_mode,
            tail_mode,
            tail_share_val,
            is_cold=is_cold,
        )

        return {
            "k_result": k_result,
            "series": series,
            "series_type": series_type,
            "trend": trend,
            "confidence": confidence,
            "is_noisy_mode": is_noisy_mode,
            "tail_share": tail_share_val,
            "tail_mode": tail_mode,
            "quality_gate_fail": gate.fail,
            "quality_gate_warn": gate.warn,
            "quality_gate_message": gate.message,
        }


def _median(values: list[float]) -> float:
    if not values:
        return 0.0
    s = sorted(values)
    n = len(s)
    if n % 2 == 1:
        return s[n // 2]
    return (s[n // 2 - 1] + s[n // 2]) / 2


def _verdict_from_change(change_pct: float, threshold: float) -> TrendVerdict:
    """strength_index: lower = better (residual dropped). So change_pct < 0 = growth."""
    if change_pct <= -threshold:
        return TrendVerdict.GROWS
    if change_pct >= threshold:
        return TrendVerdict.FALLS
    return TrendVerdict.FLAT
