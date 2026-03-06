"""Map WB API v3 FullStatsItem to app FullAdvStat."""

from __future__ import annotations

from datetime import date, datetime, timedelta
from typing import Any

from app.modules.full_stat_adv_updater.types.full_adv_stat import (
    BoosterStats,
    DayStats,
    FullAdvStat,
)

from app.core.mp.wb.api.generated.promotion.v1.marketing_and_promotions_client.models import (
    FullStatsItem,
)


def _parse_date(value: Any) -> datetime:
    """Parse date from API (string or datetime) to datetime."""
    if isinstance(value, datetime):
        return value
    if isinstance(value, str):
        s = value.replace("Z", "+00:00").split("+")[0].split(".")[0].strip()
        if len(s) == 10:
            return datetime.strptime(s, "%Y-%m-%d")
        if "T" in s:
            return datetime.strptime(s, "%Y-%m-%dT%H:%M:%S")
        return datetime.strptime(s[:10], "%Y-%m-%d")
    raise TypeError(f"Unexpected date type: {type(value)}")


def _days_to_day_stats(days_raw: Any) -> list[DayStats]:
    """Convert API days (list of dicts) to list[DayStats]."""
    if not days_raw:
        return []
    result: list[DayStats] = []
    for d in days_raw if isinstance(days_raw, list) else []:
        if not isinstance(d, dict):
            continue
        try:
            date_val = _parse_date(d.get("date", ""))
            result.append(
                DayStats(
                    date=date_val,
                    views=int(d.get("views", 0)),
                    clicks=int(d.get("clicks", 0)),
                    ctr=float(d.get("ctr", 0)),
                    cpc=float(d.get("cpc", 0)),
                    sum=float(d.get("sum", 0)),
                    atbs=int(d.get("atbs", 0)),
                    orders=int(d.get("orders", 0)),
                    cr=float(d.get("cr", 0)),
                    shks=int(d.get("shks", 0)),
                    sum_price=float(d.get("sum_price", 0)),
                )
            )
        except (TypeError, ValueError, KeyError):
            continue
    return result


def _booster_stats_from_item(booster_stats: Any) -> list[BoosterStats] | None:
    """Convert API boosterStats to list[BoosterStats]."""
    if booster_stats is None or not isinstance(booster_stats, list):
        return None
    result: list[BoosterStats] = []
    for b in booster_stats:
        if not isinstance(b, dict):
            continue
        try:
            result.append(
                BoosterStats(
                    date=str(b.get("date", "")),
                    nm=int(b.get("nm", 0)),
                    avg_position=int(b.get("avg_position", 0)),
                )
            )
        except (TypeError, ValueError, KeyError):
            continue
    return result if result else None


def full_stats_item_to_full_adv_stat(
    item: FullStatsItem,
    begin_date: date,
    end_date: date,
) -> FullAdvStat:
    """Map one FullStatsItem (v3 API) to FullAdvStat (app model)."""
    dates: list[str] = []
    d = begin_date
    while d <= end_date:
        dates.append(d.isoformat())
        d += timedelta(days=1)

    days_raw = item.days
    day_stats = _days_to_day_stats(days_raw if isinstance(days_raw, list) else [])
    booster_stats = _booster_stats_from_item(item.booster_stats)

    return FullAdvStat(
        dates=dates,
        views=item.views,
        clicks=item.clicks,
        ctr=item.ctr,
        cpc=item.cpc,
        sum=item.sum_,
        atbs=item.atbs,
        orders=item.orders,
        cr=item.cr,
        shks=item.shks,
        sum_price=item.sum_price,
        days=day_stats,
        boosterStats=booster_stats,
        advertId=item.advert_id,
    )
