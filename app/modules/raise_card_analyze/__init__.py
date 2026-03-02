"""Raise card analyze: growth analysis for campaign/card from bid_decision_log."""

from .cache import RaiseCardAnalyzeCache
from .clickhouse_manager import RaiseCardAnalyzeClickHouseManager
from .constants import (
    BID_CAP,
    CORR_MIN_POINTS,
    CORR_MIN_SUM_D,
    K_MIN_ABS,
    LOW_CORR_ABS,
    MIN_ROWS_FOR_K,
    MIN_ROWS_FOR_SIGN,
    POS_CAP,
    SPREAD_MIN_ROWS,
    SPREAD_OK_MIN,
    SUM_D_WEEK_FAIL,
    TAIL_MODE_THRESHOLD,
    TAIL_TREND_THRESHOLD,
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
from .service import CampaignGrowthAnalysisService

__all__ = [
    "RaiseCardAnalyzeCache",
    "RaiseCardAnalyzeClickHouseManager",
    "CampaignGrowthAnalysisService",
    "KResult",
    "DayPoint",
    "WeekPoint",
    "TrendResult",
    "TrendVerdict",
    "Confidence",
    "BucketPoint",
    "BucketsResult",
    "POS_CAP",
    "BID_CAP",
    "TAIL_MODE_THRESHOLD",
    "TAIL_TREND_THRESHOLD",
    "SPREAD_MIN_ROWS",
    "MIN_ROWS_FOR_SIGN",
    "MIN_ROWS_FOR_K",
    "CORR_MIN_SUM_D",
    "CORR_MIN_POINTS",
    "K_MIN_ABS",
    "LOW_CORR_ABS",
    "SPREAD_OK_MIN",
    "SUM_D_WEEK_FAIL",
]
