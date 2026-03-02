"""Redis cache for raise card analyze results."""

from __future__ import annotations

import json
from datetime import date, datetime
from typing import Any

from .dto import (
    BucketsResult,
    Confidence,
    DayPoint,
    KResult,
    TrendResult,
    TrendVerdict,
    WeekPoint,
)

CACHE_KEY_PREFIX = "rk_growth"
CACHE_TTL_SEC = 600  # 10 min


def _serialize_date(d: date) -> str:
    return d.isoformat()


def _deserialize_date(s: str) -> date:
    return date.fromisoformat(s[:10])


def _k_result_to_dict(k: KResult) -> dict[str, Any]:
    return {
        "k": k.k,
        "b": k.b,
        "corr_ln": k.corr_ln,
        "k_source": k.k_source,
        "spread_ok_window": k.spread_ok_window,
        "spread_used_recent": k.spread_used_recent,
        "k_is_weak": k.k_is_weak,
        "weak_reasons": list(k.weak_reasons),
        "window_days": k.window_days,
        "rows_used": k.rows_used,
        "keys_used": k.keys_used,
    }


def _k_result_from_dict(d: dict[str, Any]) -> KResult:
    return KResult(
        k=float(d["k"]),
        b=float(d["b"]),
        corr_ln=float(d["corr_ln"]) if d.get("corr_ln") is not None else None,
        k_source=str(d["k_source"]),
        spread_ok_window=float(d["spread_ok_window"]) if d.get("spread_ok_window") is not None else None,
        spread_used_recent=float(d["spread_used_recent"]) if d.get("spread_used_recent") is not None else None,
        k_is_weak=bool(d["k_is_weak"]),
        weak_reasons=tuple(d.get("weak_reasons") or []),
        window_days=int(d["window_days"]),
        rows_used=int(d["rows_used"]),
        keys_used=int(d["keys_used"]),
    )


def _day_point_to_dict(p: DayPoint) -> dict[str, Any]:
    return {
        "day": _serialize_date(p.day),
        "strength_index_med": p.strength_index_med,
        "sum_d": p.sum_d,
        "sum_w": p.sum_w,
        "rows_filtered": p.rows_filtered,
        "keys_filtered": p.keys_filtered,
    }


def _day_point_from_dict(d: dict[str, Any]) -> DayPoint:
    return DayPoint(
        day=_deserialize_date(d["day"]),
        strength_index_med=float(d["strength_index_med"]),
        sum_d=float(d["sum_d"]),
        sum_w=float(d["sum_w"]),
        rows_filtered=int(d["rows_filtered"]),
        keys_filtered=int(d["keys_filtered"]),
    )


def _week_point_to_dict(p: WeekPoint) -> dict[str, Any]:
    return {
        "week_start": _serialize_date(p.week_start),
        "strength_index_med": p.strength_index_med,
        "sum_d": p.sum_d,
        "sum_w": p.sum_w,
        "rows_filtered": p.rows_filtered,
        "keys_filtered": p.keys_filtered,
    }


def _week_point_from_dict(d: dict[str, Any]) -> WeekPoint:
    return WeekPoint(
        week_start=_deserialize_date(d["week_start"]),
        strength_index_med=float(d["strength_index_med"]),
        sum_d=float(d["sum_d"]),
        sum_w=float(d["sum_w"]),
        rows_filtered=int(d["rows_filtered"]),
        keys_filtered=int(d["keys_filtered"]),
    )


def _trend_to_dict(t: TrendResult | None) -> dict[str, Any] | None:
    if t is None:
        return None
    return {
        "verdict": t.verdict.value,
        "change_pct": t.change_pct,
        "last_median": t.last_median,
        "prev_median": t.prev_median,
        "trend_days": t.trend_days,
        "mode": t.mode,
    }


def _trend_from_dict(d: dict[str, Any] | None) -> TrendResult | None:
    if d is None:
        return None
    return TrendResult(
        verdict=TrendVerdict(d["verdict"]),
        change_pct=float(d["change_pct"]),
        last_median=float(d["last_median"]),
        prev_median=float(d["prev_median"]),
        trend_days=d.get("trend_days"),
        mode=str(d.get("mode", "")),
    )


def _confidence_to_dict(c: Confidence) -> dict[str, Any]:
    return {
        "level": c.level,
        "score": c.score,
        "k_source": c.k_source,
        "notes": list(c.notes),
        "is_noisy_mode": c.is_noisy_mode,
        "tail_mode": c.tail_mode,
        "tail_share": c.tail_share,
    }


def _confidence_from_dict(d: dict[str, Any]) -> Confidence:
    return Confidence(
        level=str(d["level"]),
        score=int(d["score"]),
        k_source=str(d["k_source"]),
        notes=tuple(d.get("notes") or []),
        is_noisy_mode=bool(d.get("is_noisy_mode")),
        tail_mode=bool(d.get("tail_mode")),
        tail_share=float(d.get("tail_share", 0)),
    )


def _build_cache_key(
    adv_id: int,
    nmid: int,
    calc_profile: str,
    k_source: str,
    window_days: int,
    series_days: int,
    min_d: int,
    trend_mode: str,
    asof10m: int,
) -> str:
    return f"{CACHE_KEY_PREFIX}:{adv_id}:{nmid}:{calc_profile}:{k_source}:{window_days}:{series_days}:{min_d}:{trend_mode}:{asof10m}"


class RaiseCardAnalyzeCache:
    """Redis cache for analysis result (KResult + series + trend + confidence)."""

    def __init__(self, redis_client: Any) -> None:
        self._redis = redis_client

    def _key(
        self,
        adv_id: int,
        nmid: int,
        calc_profile: str,
        k_source: str,
        window_days: int,
        series_days: int,
        min_d: int,
        trend_mode: str,
    ) -> str:
        from time import time
        asof10m = int(time() // 600)  # 10 min bucket
        return _build_cache_key(adv_id, nmid, calc_profile, k_source, window_days, series_days, min_d, trend_mode, asof10m)

    async def get(
        self,
        adv_id: int,
        nmid: int,
        calc_profile: str,
        k_source: str,
        window_days: int,
        series_days: int,
        min_d: int,
        trend_mode: str,
    ) -> dict[str, Any] | None:
        """Returns cached payload or None. Payload has k_result, series, series_type, trend, confidence, is_noisy_mode, tail_share."""
        key = self._key(adv_id, nmid, calc_profile, k_source, window_days, series_days, min_d, trend_mode)
        raw = await self._redis.get(key)
        if not raw:
            return None
        data = json.loads(raw)
        data["k_result"] = _k_result_from_dict(data["k_result"])
        if data.get("series_type") == "day":
            data["series"] = [_day_point_from_dict(p) for p in data["series"]]
        else:
            data["series"] = [_week_point_from_dict(p) for p in data["series"]]
        data["trend"] = _trend_from_dict(data.get("trend"))
        data["confidence"] = _confidence_from_dict(data["confidence"])
        return data

    async def set(
        self,
        adv_id: int,
        nmid: int,
        calc_profile: str,
        k_source: str,
        window_days: int,
        series_days: int,
        min_d: int,
        trend_mode: str,
        payload: dict[str, Any],
        ttl_sec: int = CACHE_TTL_SEC,
    ) -> None:
        """Serialize and store payload."""
        key = self._key(adv_id, nmid, calc_profile, k_source, window_days, series_days, min_d, trend_mode)
        out = {
            "k_result": _k_result_to_dict(payload["k_result"]),
            "series_type": payload.get("series_type", "day"),
            "series": [
                _day_point_to_dict(p) if isinstance(p, DayPoint) else _week_point_to_dict(p)
                for p in payload["series"]
            ],
            "trend": _trend_to_dict(payload.get("trend")),
            "confidence": _confidence_to_dict(payload["confidence"]),
            "is_noisy_mode": payload.get("is_noisy_mode", False),
            "tail_share": payload.get("tail_share", 0.0),
        }
        await self._redis.set(key, json.dumps(out), ex=ttl_sec)
