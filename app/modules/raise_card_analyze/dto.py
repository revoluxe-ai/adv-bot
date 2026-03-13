"""DTOs for raise card analyze module."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from enum import Enum


@dataclass(frozen=True)
class KResult:
    """Result of resolve_k: k, intercept, correlation, source, spread, weak flags."""

    k: float
    b: float  # intercept
    corr_ln: float | None
    k_source: str  # "item" | "adv" | "category" | "global"
    spread_ok_window: float | None  # for choosing k level (window_days_for_k, min_d 2/3)
    spread_used_recent: float | None  # for weak_reasons (last 14d, min_d=1); None if rows_recent < SPREAD_MIN_ROWS
    k_is_weak: bool
    weak_reasons: tuple[str, ...]  # "low_corr" | "flat_k" | "low_spread" | "wrong_sign"
    window_days: int
    rows_used: int
    keys_used: int


@dataclass(frozen=True)
class DayPoint:
    """One day in daily_series: strength_index_med, sum_d, sum_w, rows, keys."""

    day: date
    strength_index_med: float
    sum_d: float
    sum_w: float
    rows_filtered: int
    keys_filtered: int


@dataclass(frozen=True)
class WeekPoint:
    """One week in weekly_series."""

    week_start: date
    strength_index_med: float
    sum_d: float
    sum_w: float
    rows_filtered: int
    keys_filtered: int


class TrendVerdict(str, Enum):
    """Verdict for trend."""

    GROWS = "растёт"
    FLAT = "стоит"
    FALLS = "падает"


@dataclass(frozen=True)
class TrendResult:
    """Computed trend (when not noisy_mode and not k_is_weak)."""

    verdict: TrendVerdict
    change_pct: float
    last_median: float
    prev_median: float
    trend_days: int | None
    mode: str  # "last_7_vs_prev_7" | "week_over_week"


@dataclass(frozen=True)
class Confidence:
    """Confidence level and notes for UI."""

    level: str  # "high" | "medium" | "low"
    score: int  # 0..100
    k_source: str
    notes: tuple[str, ...]
    is_noisy_mode: bool
    tail_mode: bool
    tail_share: float  # 0..1, share(pos_final > POS_CAP) on last period


@dataclass(frozen=True)
class BucketPoint:
    """One bucket: week, bid_bucket, avg_pos, rows, sum_d, sum_w."""

    week_start: date
    bid_bucket: float
    avg_pos: float
    rows: int
    sum_d: float
    sum_w: float


@dataclass(frozen=True)
class BucketsResult:
    """Selected buckets (3–5 by max sum_d, tie-breaker sum_w)."""

    buckets: tuple[BucketPoint, ...]
