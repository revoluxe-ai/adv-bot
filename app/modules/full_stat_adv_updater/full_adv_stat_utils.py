"""Helpers for FullAdvStat: filter to specific dates and contiguity check."""

from __future__ import annotations

from datetime import date, datetime, timedelta

from app.modules.full_stat_adv_updater.types.full_adv_stat import (
    BoosterStats,
    DayStats,
    FullAdvStat,
    compute_aggregate_ctr_cpc_cr,
)


def _day_stats_date(d: DayStats) -> date:
    """Normalize DayStats.date (datetime or date) to date."""
    val = d.date
    return val.date() if isinstance(val, datetime) else val


def requested_dates_are_contiguous(dates: list[date]) -> bool:
    """True iff the set of dates equals the full range from min to max."""
    if len(dates) <= 1:
        return True
    requested_set = set(dates)
    lo = min(dates)
    hi = max(dates)
    current = lo
    while current <= hi:
        if current not in requested_set:
            return False
        current += timedelta(days=1)
    return len(requested_set) == (hi - lo).days + 1


def filter_full_adv_stat_to_dates(
    stats: list[FullAdvStat],
    requested_dates: list[date],
) -> list[FullAdvStat]:
    """
    Re-aggregate each FullAdvStat to only the requested dates using per-day data.

    The v3 API returns stats for a contiguous range; when the caller passed
    non-contiguous dates we request min..max then filter to requested days
    so that views, clicks, sum, etc. match the old v2 semantics (only those days).
    """
    requested_set = set(requested_dates)
    if not requested_set:
        return stats

    result: list[FullAdvStat] = []
    for stat in stats:
        filtered_days = [d for d in stat.days if _day_stats_date(d) in requested_set]
        filtered_days.sort(key=lambda d: _day_stats_date(d))

        if not filtered_days:
            ctr0, cpc0, cr0 = compute_aggregate_ctr_cpc_cr(0, 0, 0.0, 0)
            result.append(
                FullAdvStat(
                    dates=[d.isoformat() for d in sorted(requested_dates)],
                    views=0,
                    clicks=0,
                    ctr=ctr0,
                    cpc=cpc0,
                    sum=0.0,
                    atbs=0,
                    orders=0,
                    cr=cr0,
                    shks=0,
                    sum_price=0.0,
                    days=[],
                    boosterStats=_filter_booster_stats_to_dates(
                        stat.boosterStats, requested_set
                    ),
                    advertId=stat.advertId,
                )
            )
            continue

        views = sum(d.views for d in filtered_days)
        clicks = sum(d.clicks for d in filtered_days)
        sum_ = sum(d.sum for d in filtered_days)
        atbs = sum(d.atbs for d in filtered_days)
        orders = sum(d.orders for d in filtered_days)
        shks = sum(d.shks for d in filtered_days)
        sum_price = sum(d.sum_price for d in filtered_days)

        ctr, cpc, cr = compute_aggregate_ctr_cpc_cr(views, clicks, sum_, orders)

        dates_str = [d.isoformat() for d in sorted(_day_stats_date(d) for d in filtered_days)]

        result.append(
            FullAdvStat(
                dates=dates_str,
                views=views,
                clicks=clicks,
                ctr=ctr,
                cpc=cpc,
                sum=sum_,
                atbs=atbs,
                orders=orders,
                cr=cr,
                shks=shks,
                sum_price=sum_price,
                days=filtered_days,
                boosterStats=_filter_booster_stats_to_dates(
                    stat.boosterStats, requested_set
                ),
                advertId=stat.advertId,
            )
        )
    return result


def _booster_stat_date_to_date(s: str) -> date | None:
    """Parse BoosterStats.date (API: ISO date or datetime like 2023-10-07T00:00:00Z) to date."""
    if not s:
        return None
    s = s.strip()
    if len(s) < 10:
        return None
    # Date-only "YYYY-MM-DD"
    if s[4] == "-" and s[7] == "-":
        try:
            return date.fromisoformat(s[:10])
        except ValueError:
            pass
    try:
        # Datetime with optional Z
        dt = datetime.fromisoformat(s.replace("Z", "+00:00"))
        return dt.date()
    except ValueError:
        return None


def _filter_booster_stats_to_dates(
    booster_stats: list[BoosterStats] | None,
    requested_set: set[date],
) -> list[BoosterStats] | None:
    """Keep only booster stats whose date is in requested_set."""
    if not booster_stats:
        return None
    filtered = [
        b
        for b in booster_stats
        if _booster_stat_date_to_date(b.date) in requested_set
    ]
    return filtered if filtered else None
