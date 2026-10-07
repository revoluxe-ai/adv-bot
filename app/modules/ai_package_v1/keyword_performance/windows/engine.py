"""UTC window catalog: rolling, calendar, comparables, all_available."""

from __future__ import annotations

import calendar
import statistics
from collections import defaultdict
from collections.abc import Iterable
from dataclasses import dataclass
from datetime import date, timedelta

from app.modules.ai_package_v1.keyword_performance.domain.cutoff import PackageCutoff
from app.modules.ai_package_v1.keyword_performance.domain.derived_metrics import (
    safe_cpo,
    safe_ratio,
)
from app.modules.ai_package_v1.keyword_performance.domain.enums import (
    ComparatorKind,
    KeywordLegRole,
    QuerySpendStatus,
    WindowSpendStatus,
)
from app.modules.ai_package_v1.keyword_performance.domain.models import (
    KeywordChangeRowV1,
    KeywordDailyRowV1,
    KeywordWindowRowV1,
)

ROLLING_WINDOWS: dict[str, int] = {
    "1d": 1,
    "3d": 3,
    "7d": 7,
    "14d": 14,
    "30d": 30,
    "90d": 90,
    "180d": 180,
    "365d": 365,
}

COMPARABLE_PREV: dict[str, str] = {
    "3d": "3d_vs_prev_3d",
    "7d": "7d_vs_prev_7d",
    "14d": "14d_vs_prev_14d",
    "30d": "30d_vs_prev_30d",
    "90d": "90d_vs_prev_90d",
    "180d": "180d_vs_prev_180d",
    "365d": "365d_vs_prev_365d",
}

COMPARABLE_CALENDAR: dict[str, str] = {
    "month_to_date": "mtd_vs_prev_mtd",
    "quarter_to_date": "qtd_vs_prev_qtd",
    "year_to_date": "ytd_vs_prev_ytd",
}

CHANGE_METRICS: tuple[str, ...] = (
    "views_sum",
    "clicks_sum",
    "add_to_cart_sum",
    "orders_sum",
    "spend_rub_sum",
    "ctr",
    "conv_views_to_cart",
    "conv_cart_to_order",
    "conv_views_to_order",
    "cpo_rub",
    "cpm_mean",
    "cpc_mean",
    "cluster_avg_pos_mean",
    "cluster_avg_pos_start",
    "cluster_avg_pos_end",
    "cluster_avg_pos_delta",
    "cluster_avg_pos_best",
    "cluster_avg_pos_worst",
)

RATE_METRICS: frozenset[str] = frozenset(
    {
        "ctr",
        "conv_views_to_cart",
        "conv_cart_to_order",
        "conv_views_to_order",
    }
)


@dataclass(frozen=True, slots=True)
class WindowSpec:
    """Resolved window bounds."""

    window_id: str
    start: date
    end: date
    comparator_kind: ComparatorKind = ComparatorKind.NONE
    requested_days: int = 0


def _identity_key(row: KeywordDailyRowV1) -> tuple[int, int, int, str, KeywordLegRole]:
    return (row.adv_id, row.nmid, row.adv_setting_id or -1, row.norm_query, row.leg_role)


def _window_identity_key(w: KeywordWindowRowV1) -> tuple[int, int, str, KeywordLegRole]:
    return (w.adv_id, w.nmid, w.norm_query, w.leg_role)


def _rolling_bounds(end: date, days: int) -> tuple[date, date, int]:
    start = end - timedelta(days=days - 1)
    return start, end, days


def _month_start(d: date) -> date:
    return date(d.year, d.month, 1)


def _quarter_start(d: date) -> date:
    q_month = ((d.month - 1) // 3) * 3 + 1
    return date(d.year, q_month, 1)


def _year_start(d: date) -> date:
    return date(d.year, 1, 1)


def _prev_month_comparable(end: date) -> tuple[date, date]:
    """Elapsed-day aligned previous month comparable (for keyword_changes only)."""
    prev_month = end.month - 1 or 12
    prev_year = end.year - 1 if end.month == 1 else end.year
    prev_start = date(prev_year, prev_month, 1)
    last_day = calendar.monthrange(prev_year, prev_month)[1]
    comparable_end = date(prev_year, prev_month, min(end.day, last_day))
    return prev_start, comparable_end


def _prev_quarter_comparable(end: date) -> tuple[date, date]:
    """Elapsed-day aligned previous quarter comparable."""
    q = (end.month - 1) // 3
    if q == 0:
        prev_q_start = date(end.year - 1, 10, 1)
        prev_q_end_month = 12
        prev_year = end.year - 1
    else:
        prev_q_month = (q - 1) * 3 + 1
        prev_q_start = date(end.year, prev_q_month, 1)
        prev_q_end_month = prev_q_month + 2
        prev_year = end.year
    last_day = calendar.monthrange(prev_year, prev_q_end_month)[1]
    comparable_end = date(prev_year, prev_q_end_month, min(end.day, last_day))
    return prev_q_start, comparable_end


def _prev_year_comparable(end: date) -> tuple[date, date]:
    """Elapsed-day aligned previous year comparable (leap-year safe)."""
    prev_year = end.year - 1
    prev_start = date(prev_year, 1, 1)
    try:
        comparable_end = date(prev_year, end.month, end.day)
    except ValueError:
        comparable_end = date(prev_year, end.month, 28)
    return prev_start, comparable_end


def _previous_month_full(anchor: date) -> tuple[date, date]:
    """Full closed previous calendar month."""
    if anchor.month == 1:
        prev_year, prev_month = anchor.year - 1, 12
    else:
        prev_year, prev_month = anchor.year, anchor.month - 1
    start = date(prev_year, prev_month, 1)
    end = date(prev_year, prev_month, calendar.monthrange(prev_year, prev_month)[1])
    return start, end


def _previous_quarter_full(anchor: date) -> tuple[date, date]:
    """Full closed previous calendar quarter."""
    q = (anchor.month - 1) // 3
    if q == 0:
        prev_year = anchor.year - 1
        start = date(prev_year, 10, 1)
        end = date(prev_year, 12, 31)
    else:
        prev_q_month = (q - 1) * 3 + 1
        start = date(anchor.year, prev_q_month, 1)
        end_month = prev_q_month + 2
        end = date(anchor.year, end_month, calendar.monthrange(anchor.year, end_month)[1])
    return start, end


def _previous_year_full(anchor: date) -> tuple[date, date]:
    """Full Jan 1..Dec 31 previous calendar year."""
    prev_year = anchor.year - 1
    return date(prev_year, 1, 1), date(prev_year, 12, 31)


def _days_in_year(year: int) -> int:
    return 366 if calendar.isleap(year) else 365


def _open_period_spec(
    window_id: str,
    period_start: date,
    last_closed: date,
) -> WindowSpec:
    """OPEN MTD/QTD/YTD ending at last_closed; empty when anchor precedes period."""
    if last_closed < period_start:
        empty_end = period_start - timedelta(days=1)
        return WindowSpec(window_id, period_start, empty_end, requested_days=0)
    requested = (last_closed - period_start).days + 1
    return WindowSpec(window_id, period_start, last_closed, requested_days=requested)


def build_window_catalog(
    cutoff: PackageCutoff,
    first_available: date | None,
    last_available: date | None,
) -> list[WindowSpec]:
    """Full ready window catalog per Owner D-007."""
    end = cutoff.last_closed_calendar_day
    anchor = cutoff.package_cutoff_date
    specs: list[WindowSpec] = []

    for window_id, days in ROLLING_WINDOWS.items():
        start, wend, req = _rolling_bounds(end, days)
        specs.append(WindowSpec(window_id, start, wend, requested_days=req))
        if window_id in COMPARABLE_PREV:
            prev_end = start - timedelta(days=1)
            prev_start = prev_end - timedelta(days=days - 1)
            specs.append(
                WindowSpec(
                    f"prev_{window_id}",
                    prev_start,
                    prev_end,
                    ComparatorKind.PREVIOUS_PERIOD,
                    requested_days=days,
                )
            )

    mtd_start = _month_start(anchor)
    specs.append(_open_period_spec("month_to_date", mtd_start, end))

    prev_m_start, prev_m_end = _previous_month_full(anchor)
    specs.append(
        WindowSpec(
            "previous_month",
            prev_m_start,
            prev_m_end,
            ComparatorKind.PREVIOUS_CALENDAR,
            requested_days=(prev_m_end - prev_m_start).days + 1,
        )
    )

    qtd_start = _quarter_start(anchor)
    specs.append(_open_period_spec("quarter_to_date", qtd_start, end))

    pq_start, pq_end = _previous_quarter_full(anchor)
    specs.append(
        WindowSpec(
            "previous_quarter",
            pq_start,
            pq_end,
            ComparatorKind.PREVIOUS_CALENDAR,
            requested_days=(pq_end - pq_start).days + 1,
        )
    )

    ytd_start = _year_start(anchor)
    specs.append(_open_period_spec("year_to_date", ytd_start, end))

    py_start, py_end = _previous_year_full(anchor)
    specs.append(
        WindowSpec(
            "previous_year",
            py_start,
            py_end,
            ComparatorKind.PREVIOUS_CALENDAR,
            requested_days=_days_in_year(py_start.year),
        )
    )

    ybp_year = anchor.year - 2
    ybp_start = date(ybp_year, 1, 1)
    ybp_end = date(ybp_year, 12, 31)
    specs.append(
        WindowSpec(
            "year_before_previous",
            ybp_start,
            ybp_end,
            ComparatorKind.PREVIOUS_CALENDAR,
            requested_days=_days_in_year(ybp_year),
        )
    )

    if first_available is not None and last_available is not None:
        bounded_last = min(last_available, cutoff.package_cutoff_date)
        specs.append(
            WindowSpec(
                "all_available",
                first_available,
                bounded_last,
                requested_days=(bounded_last - first_available).days + 1,
            )
        )
    return specs


def _rows_in_window(
    daily: Iterable[KeywordDailyRowV1],
    start: date,
    end: date,
) -> list[KeywordDailyRowV1]:
    result: list[KeywordDailyRowV1] = []
    for row in daily:
        d = date.fromisoformat(row.date)
        if start <= d <= end:
            result.append(row)
    return result


def _aggregate_window(
    rows: list[KeywordDailyRowV1],
    spec: WindowSpec,
    identity: KeywordDailyRowV1,
) -> KeywordWindowRowV1:
    observed_days = len({r.date for r in rows})
    requested = max(spec.requested_days, 0)
    missing_days = max(requested - observed_days, 0) if requested else 0
    partial = observed_days < requested if requested else False

    views_sum = _sum_int(r.views for r in rows)
    clicks_sum = _sum_int(r.clicks for r in rows)
    cart_sum = _sum_int(r.add_to_cart for r in rows)
    orders_sum = _sum_int(r.orders for r in rows)

    spend_values = [
        r.spend_rub
        for r in rows
        if r.spend_rub is not None and r.query_spend_status == QuerySpendStatus.FACTUAL
    ]
    all_days_factual = len(spend_values) == observed_days and observed_days > 0
    spend_sum = sum(spend_values) if spend_values else None
    if observed_days == 0:
        spend_status = WindowSpendStatus.UNAVAILABLE
        spend_sum = None
    elif all_days_factual:
        spend_status = WindowSpendStatus.FACTUAL
    elif spend_values:
        spend_status = WindowSpendStatus.PARTIAL_UNAVAILABLE
        spend_sum = None
    else:
        spend_status = WindowSpendStatus.UNAVAILABLE
        spend_sum = None

    sorted_rows = sorted(rows, key=lambda r: r.date)
    positions_chrono = [
        (r.date, r.cluster_avg_pos)
        for r in sorted_rows
        if r.cluster_avg_pos is not None
    ]
    pos_start = positions_chrono[0][1] if positions_chrono else None
    pos_end = positions_chrono[-1][1] if positions_chrono else None
    pos_best = min(p for _, p in positions_chrono) if positions_chrono else None
    pos_worst = max(p for _, p in positions_chrono) if positions_chrono else None
    pos_delta = (
        float(pos_end) - float(pos_start)
        if pos_start is not None and pos_end is not None
        else None
    )
    positions = [pos for _, pos in positions_chrono]
    position_observed_days = len({day for day, _ in positions_chrono})
    position_missing_days = (
        max(requested - position_observed_days, 0) if requested else 0
    )
    weighted_mean = _position_mean(rows, positions_chrono)
    median_pos = statistics.median(positions) if positions else None

    clicks_for_ctr, views_for_ctr = _sum_aligned_int(rows, "clicks", "views")
    cart_for_conv, views_for_cart = _sum_aligned_int(rows, "add_to_cart", "views")
    orders_for_cart_conv, cart_for_order = _sum_aligned_int(rows, "orders", "add_to_cart")
    orders_for_view_conv, views_for_order = _sum_aligned_int(rows, "orders", "views")
    spend_for_cpm, views_for_cpm = _sum_factual_spend_aligned(rows, "views")
    spend_for_cpc, clicks_for_cpc = _sum_factual_spend_aligned(rows, "clicks")
    spend_for_cpo, orders_for_cpo = _sum_factual_spend_aligned(rows, "orders")

    cpm_mean = None
    cpc_mean = None
    if spend_status == WindowSpendStatus.FACTUAL:
        if spend_for_cpm is not None and views_for_cpm is not None and views_for_cpm > 0:
            cpm_mean = spend_for_cpm / views_for_cpm * 1000.0
        if spend_for_cpc is not None and clicks_for_cpc is not None and clicks_for_cpc > 0:
            cpc_mean = spend_for_cpc / clicks_for_cpc

    return KeywordWindowRowV1(
        shop_id=identity.shop_id,
        adv_setting_id=identity.adv_setting_id,
        adv_id=identity.adv_id,
        leg_role=identity.leg_role,
        nmid=identity.nmid,
        norm_query=identity.norm_query,
        window_id=spec.window_id,
        window_start=spec.start.isoformat(),
        window_end=spec.end.isoformat(),
        comparator_kind=spec.comparator_kind,
        observed_days=observed_days,
        missing_days=missing_days,
        requested_days=requested,
        partial=partial,
        views_sum=views_sum,
        clicks_sum=clicks_sum,
        add_to_cart_sum=cart_sum,
        orders_sum=orders_sum,
        spend_rub_sum=spend_sum,
        spend_status=spend_status,
        ctr=safe_ratio(clicks_for_ctr, views_for_ctr),
        conv_views_to_cart=safe_ratio(cart_for_conv, views_for_cart),
        conv_cart_to_order=safe_ratio(orders_for_cart_conv, cart_for_order),
        conv_views_to_order=safe_ratio(orders_for_view_conv, views_for_order),
        cpo_rub=safe_cpo(
            spend_for_cpo,
            orders_for_cpo,
            spend_factual=spend_status == WindowSpendStatus.FACTUAL,
        ),
        cpm_mean=cpm_mean,
        cpc_mean=cpc_mean,
        cluster_avg_pos_mean=weighted_mean,
        cluster_avg_pos_median=median_pos,
        cluster_avg_pos_start=pos_start,
        cluster_avg_pos_end=pos_end,
        cluster_avg_pos_delta=pos_delta,
        cluster_avg_pos_best=pos_best,
        cluster_avg_pos_worst=pos_worst,
        position_observed_days=position_observed_days,
        position_missing_days=position_missing_days,
        window_coverage={
            "partial": partial,
            "observed_days": observed_days,
            "missing_days": missing_days,
            "position_observed_days": position_observed_days,
            "position_missing_days": position_missing_days,
            "position_mean_mode": (
                "views_weighted"
                if any(
                    r.cluster_avg_pos is not None
                    and r.views is not None
                    and r.views > 0
                    for r in rows
                )
                else ("unweighted" if positions else "none")
            ),
        },
    )


def compute_windows(
    daily_rows: list[KeywordDailyRowV1],
    cutoff: PackageCutoff,
    first_available: date | None,
    last_available: date | None,
) -> list[KeywordWindowRowV1]:
    """Compute all window rows per identity."""
    grouped: dict[tuple[int, int, int, str, KeywordLegRole], list[KeywordDailyRowV1]] = (
        defaultdict(list)
    )
    for row in daily_rows:
        grouped[_identity_key(row)].append(row)

    catalog = build_window_catalog(cutoff, first_available, last_available)
    export_specs = [s for s in catalog if not s.window_id.startswith("prev_")]
    windows: list[KeywordWindowRowV1] = []
    for _group_key, rows in sorted(grouped.items()):
        identity = rows[0]
        for spec in export_specs:
            in_window = _rows_in_window(rows, spec.start, spec.end)
            windows.append(_aggregate_window(in_window, spec, identity))
    return windows


def _resolve_previous_window(
    *,
    window_map: dict[str, KeywordWindowRowV1],
    daily_rows: list[KeywordDailyRowV1],
    identity: KeywordDailyRowV1,
    prev_window_id: str,
    prev_start: date,
    prev_end: date,
) -> KeywordWindowRowV1 | None:
    """Lookup prev window aggregate; compute from daily when absent."""
    prev = window_map.get(prev_window_id)
    if prev is not None:
        return prev
    if prev_start > prev_end:
        return None
    prev_rows = _rows_in_window(daily_rows, prev_start, prev_end)
    spec = WindowSpec(
        prev_window_id,
        prev_start,
        prev_end,
        ComparatorKind.PREVIOUS_PERIOD,
        requested_days=(prev_end - prev_start).days + 1 if prev_end >= prev_start else 0,
    )
    return _aggregate_window(prev_rows, spec, identity)


def compute_changes(
    windows: list[KeywordWindowRowV1],
    daily_rows: list[KeywordDailyRowV1],
    cutoff: PackageCutoff,
) -> list[KeywordChangeRowV1]:
    """Comparable prev window deltas (facts only, no AI labels)."""
    by_identity: dict[tuple[int, int, str, KeywordLegRole], dict[str, KeywordWindowRowV1]] = (
        defaultdict(dict)
    )
    daily_by_identity: dict[tuple[int, int, int, str, KeywordLegRole], list[KeywordDailyRowV1]] = (
        defaultdict(list)
    )
    for row in daily_rows:
        daily_by_identity[_identity_key(row)].append(row)

    identity_template: dict[tuple[int, int, str, KeywordLegRole], KeywordDailyRowV1] = {}
    for w in windows:
        key = _window_identity_key(w)
        by_identity[key][w.window_id] = w
        if key not in identity_template:
            identity_template[key] = KeywordDailyRowV1(
                shop_id=w.shop_id,
                adv_setting_id=w.adv_setting_id,
                adv_id=w.adv_id,
                leg_role=w.leg_role,
                nmid=w.nmid,
                norm_query=w.norm_query,
                date=w.window_end,
            )

    changes: list[KeywordChangeRowV1] = []
    end = cutoff.last_closed_calendar_day

    for comp_days, change_id in COMPARABLE_PREV.items():
        cur_id = comp_days
        prev_start, prev_end, _ = _rolling_bounds(
            end - timedelta(days=ROLLING_WINDOWS[comp_days]), ROLLING_WINDOWS[comp_days]
        )
        prev_id = f"prev_{comp_days}"
        for identity_key, window_map in sorted(by_identity.items()):
            current = window_map.get(cur_id)
            if current is None:
                continue
            template = identity_template[identity_key]
            daily_key = (
                template.adv_id,
                template.nmid,
                template.adv_setting_id or -1,
                template.norm_query,
                template.leg_role,
            )
            prev = _resolve_previous_window(
                window_map=window_map,
                daily_rows=daily_by_identity.get(daily_key, []),
                identity=template,
                prev_window_id=prev_id,
                prev_start=prev_start,
                prev_end=prev_end,
            )
            if prev is None:
                continue
            changes.extend(
                _change_rows_for_window(current, prev, change_id, prev_id, cur_id)
            )

    comparable_bounds: dict[str, tuple[date, date]] = {
        "month_to_date": _prev_month_comparable(end),
        "quarter_to_date": _prev_quarter_comparable(end),
        "year_to_date": _prev_year_comparable(end),
    }
    for cur_id, change_id in COMPARABLE_CALENDAR.items():
        prev_start, prev_end = comparable_bounds[cur_id]
        prev_id = f"prev_{cur_id}"
        for identity_key, window_map in sorted(by_identity.items()):
            current = window_map.get(cur_id)
            if current is None:
                continue
            template = identity_template[identity_key]
            daily_key = (
                template.adv_id,
                template.nmid,
                template.adv_setting_id or -1,
                template.norm_query,
                template.leg_role,
            )
            prev = _resolve_previous_window(
                window_map=window_map,
                daily_rows=daily_by_identity.get(daily_key, []),
                identity=template,
                prev_window_id=prev_id,
                prev_start=prev_start,
                prev_end=prev_end,
            )
            if prev is None:
                continue
            changes.extend(
                _change_rows_for_window(current, prev, change_id, prev_id, cur_id)
            )
    return changes


def _change_rows_for_window(
    current: KeywordWindowRowV1,
    previous: KeywordWindowRowV1,
    change_id: str,
    prev_window_id: str,
    cur_window_id: str,
) -> list[KeywordChangeRowV1]:
    rows: list[KeywordChangeRowV1] = []
    for metric in CHANGE_METRICS:
        rows.extend(
            _change_rows_for_metric(
                current, previous, change_id, metric, prev_window_id, cur_window_id
            )
        )
    return rows


def _change_rows_for_metric(
    current: KeywordWindowRowV1,
    previous: KeywordWindowRowV1,
    change_id: str,
    metric_name: str,
    prev_window_id: str,
    cur_window_id: str,
) -> list[KeywordChangeRowV1]:
    cur_val = getattr(current, metric_name)
    prev_val = getattr(previous, metric_name)
    abs_delta = None
    rel_delta = None
    pp_delta = None
    ranking_delta = None
    if cur_val is not None and prev_val is not None:
        abs_delta = float(cur_val) - float(prev_val)
        if prev_val != 0:
            rel_delta = abs_delta / float(prev_val)
        if metric_name in RATE_METRICS:
            pp_delta = abs_delta * 100.0
        if metric_name.startswith("cluster_avg_pos"):
            ranking_delta = abs_delta
    return [
        KeywordChangeRowV1(
            shop_id=current.shop_id,
            adv_setting_id=current.adv_setting_id,
            adv_id=current.adv_id,
            leg_role=current.leg_role,
            nmid=current.nmid,
            norm_query=current.norm_query,
            change_id=change_id,
            current_window_id=cur_window_id,
            previous_window_id=prev_window_id,
            current_start=current.window_start,
            current_end=current.window_end,
            previous_start=previous.window_start,
            previous_end=previous.window_end,
            metric_name=metric_name,
            current_value=float(cur_val) if cur_val is not None else None,
            previous_value=float(prev_val) if prev_val is not None else None,
            absolute_delta=abs_delta,
            relative_delta=rel_delta,
            pp_delta=pp_delta,
            ranking_delta=ranking_delta,
            spend_status_current=current.spend_status,
            spend_status_previous=previous.spend_status,
            coverage_current={"observed_days": current.observed_days, "partial": current.partial},
            coverage_previous={
                "observed_days": previous.observed_days,
                "partial": previous.partial,
            },
        )
    ]


def _sum_int(values: Iterable[int | None]) -> int | None:
    nums = [v for v in values if v is not None]
    if not nums:
        return None
    return sum(nums)


def _sum_aligned_int(
    rows: list[KeywordDailyRowV1],
    numerator: str,
    denominator: str,
) -> tuple[int | None, int | None]:
    """Sum numerator/denominator only on rows where both metrics are non-null."""
    num_total = 0
    denom_total = 0
    paired = False
    for row in rows:
        num_val = getattr(row, numerator)
        denom_val = getattr(row, denominator)
        if num_val is None or denom_val is None:
            continue
        paired = True
        num_total += int(num_val)
        denom_total += int(denom_val)
    if not paired:
        return None, None
    return num_total, denom_total


def _sum_factual_spend_aligned(
    rows: list[KeywordDailyRowV1],
    companion: str,
) -> tuple[float | None, int | None]:
    """Sum FACTUAL spend only on rows where companion metric is also non-null."""
    spend_total = 0.0
    companion_total = 0
    paired = False
    for row in rows:
        if row.query_spend_status != QuerySpendStatus.FACTUAL or row.spend_rub is None:
            continue
        companion_val = getattr(row, companion)
        if companion_val is None:
            continue
        paired = True
        spend_total += float(row.spend_rub)
        companion_total += int(companion_val)
    if not paired:
        return None, None
    return spend_total, companion_total


def _position_mean(
    rows: list[KeywordDailyRowV1],
    positions_chrono: list[tuple[str, float]],
) -> float | None:
    """Weighted mean by views when available; unweighted fallback with honest coverage."""
    if not positions_chrono:
        return None
    by_date: dict[str, float] = {}
    for day, pos in positions_chrono:
        by_date[day] = pos
    weighted_num = 0.0
    weighted_den = 0
    for row in rows:
        if row.cluster_avg_pos is None:
            continue
        weight = row.views
        if weight is None or weight <= 0:
            continue
        weighted_num += float(row.cluster_avg_pos) * weight
        weighted_den += weight
    if weighted_den > 0:
        return weighted_num / weighted_den
    return statistics.mean(by_date.values())
