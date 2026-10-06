"""Window engine: calendar vs rolling, CTR, partial coverage, golden bounds (S14-S17,S15,S20,S21)."""

from __future__ import annotations

from datetime import date, timedelta

import pytest

from app.modules.ai_package_v1.keyword_performance.domain.cutoff import PackageCutoff
from app.modules.ai_package_v1.keyword_performance.domain.enums import (
    KeywordLegRole,
    QuerySpendStatus,
)
from app.modules.ai_package_v1.keyword_performance.domain.models import KeywordDailyRowV1
from app.modules.ai_package_v1.keyword_performance.export.current_state import (
    compute_current_state,
)
from app.modules.ai_package_v1.keyword_performance.windows.engine import (
    build_window_catalog,
    compute_changes,
    compute_windows,
)

pytestmark = pytest.mark.unit

GENERATED_AT_OCT5 = "2026-10-05T15:00:00Z"


def _daily_row(
    *,
    shop_id: str = "1",
    adv_setting_id: int | None = 101,
    adv_id: int = 111,
    leg_role: KeywordLegRole = KeywordLegRole.AUTO,
    nmid: int = 500,
    norm_query: str = "q",
    date: str = "2026-01-03",
    views: int | None = 100,
    clicks: int | None = 10,
    orders: int | None = 2,
    spend_rub: float | None = 50.0,
    query_spend_status: QuerySpendStatus = QuerySpendStatus.FACTUAL,
) -> KeywordDailyRowV1:
    return KeywordDailyRowV1(
        shop_id=shop_id,
        adv_setting_id=adv_setting_id,
        adv_id=adv_id,
        leg_role=leg_role,
        nmid=nmid,
        norm_query=norm_query,
        date=date,
        views=views,
        clicks=clicks,
        orders=orders,
        spend_rub=spend_rub,
        query_spend_status=query_spend_status,
    )


def test_rolling_vs_calendar_year_bounds() -> None:
    cutoff = PackageCutoff.from_generated_at(GENERATED_AT_OCT5)
    catalog = build_window_catalog(
        cutoff, date(2025, 1, 1), date(2026, 10, 4)
    )
    ids = {s.window_id for s in catalog}
    assert "365d" in ids
    assert "previous_year" in ids
    rolling = next(s for s in catalog if s.window_id == "365d")
    prev_year = next(s for s in catalog if s.window_id == "previous_year")
    assert rolling.start != prev_year.start or rolling.end != prev_year.end


def test_golden_calendar_bounds_oct5() -> None:
    """Golden: generated_at Oct 5 UTC → full calendar previous windows."""
    cutoff = PackageCutoff.from_generated_at(GENERATED_AT_OCT5)
    catalog = build_window_catalog(cutoff, date(2025, 1, 1), date(2026, 10, 4))
    by_id = {s.window_id: s for s in catalog}

    prev_month = by_id["previous_month"]
    assert prev_month.start == date(2026, 9, 1)
    assert prev_month.end == date(2026, 9, 30)

    prev_quarter = by_id["previous_quarter"]
    assert prev_quarter.start == date(2026, 7, 1)
    assert prev_quarter.end == date(2026, 9, 30)

    prev_year = by_id["previous_year"]
    assert prev_year.start == date(2025, 1, 1)
    assert prev_year.end == date(2025, 12, 31)

    rolling_7d = by_id["7d"]
    assert rolling_7d.start == date(2026, 9, 28)
    assert rolling_7d.end == date(2026, 10, 4)


def test_jan1_empty_mtd_qtd_ytd() -> None:
    """First-day anchor: MTD/QTD/YTD empty when last_closed precedes period start."""
    cutoff = PackageCutoff.from_generated_at("2026-01-01T12:00:00Z")
    catalog = build_window_catalog(cutoff, date(2025, 1, 1), date(2025, 12, 31))
    by_id = {s.window_id: s for s in catalog}
    mtd = by_id["month_to_date"]
    assert mtd.requested_days == 0
    assert mtd.start == date(2026, 1, 1)
    assert mtd.end == date(2025, 12, 31)
    qtd = by_id["quarter_to_date"]
    assert qtd.requested_days == 0
    ytd = by_id["year_to_date"]
    assert ytd.requested_days == 0


def test_leap_year_prev_ytd_comparable() -> None:
    """Feb 29 leap end → prev year comparable capped at Feb 28."""
    cutoff = PackageCutoff.from_generated_at("2024-03-01T12:00:00Z")
    end = cutoff.last_closed_calendar_day
    assert end == date(2024, 2, 29)
    windows = compute_windows([], cutoff, date(2023, 1, 1), end)
    assert windows == []
    rows = [_daily_row(date=end.isoformat(), views=1)]
    windows = compute_windows(rows, cutoff, date(2023, 1, 1), end)
    changes = compute_changes(windows, rows, cutoff)
    ytd_change = next(c for c in changes if c.change_id == "ytd_vs_prev_ytd" and c.metric_name == "views_sum")
    assert ytd_change.previous_start == "2023-01-01"
    assert ytd_change.previous_end == "2023-02-28"


def test_prev7d_alignment() -> None:
    """S15: real prev 7d aggregate — prev 700, current 70, delta -630."""
    cutoff = PackageCutoff.from_generated_at(GENERATED_AT_OCT5)
    end = cutoff.last_closed_calendar_day
    rows: list[KeywordDailyRowV1] = []
    prev_start = end - timedelta(days=13)
    for i in range(7):
        d = (prev_start + timedelta(days=i)).isoformat()
        rows.append(_daily_row(date=d, views=100))
    cur_start = end - timedelta(days=6)
    for i in range(7):
        d = (cur_start + timedelta(days=i)).isoformat()
        rows.append(_daily_row(date=d, views=10))

    windows = compute_windows(rows, cutoff, prev_start, end)
    changes = compute_changes(windows, rows, cutoff)
    views_change = next(
        c for c in changes if c.change_id == "7d_vs_prev_7d" and c.metric_name == "views_sum"
    )
    assert views_change.previous_value is not None
    assert abs(views_change.previous_value - 700.0) < 1e-9
    assert views_change.current_value is not None
    assert abs(views_change.current_value - 70.0) < 1e-9
    assert views_change.absolute_delta is not None
    assert abs(views_change.absolute_delta - (-630.0)) < 1e-9
    assert views_change.previous_start == date(2026, 9, 21).isoformat()
    assert views_change.previous_end == date(2026, 9, 27).isoformat()


def test_window_ctr_sum_ratio() -> None:
    cutoff = PackageCutoff.from_generated_at(GENERATED_AT_OCT5)
    end = cutoff.last_closed_calendar_day
    start = end - timedelta(days=1)
    rows = [
        _daily_row(date=end.isoformat(), views=100, clicks=10),
        _daily_row(date=start.isoformat(), views=200, clicks=30),
    ]
    windows = compute_windows(rows, cutoff, start, end)
    w7 = next(w for w in windows if w.window_id == "7d")
    assert w7.ctr is not None
    assert abs(w7.ctr - (40 / 300)) < 1e-9


def test_partial_7d_coverage() -> None:
    cutoff = PackageCutoff.from_generated_at("2026-01-10T12:00:00Z")
    rows = [_daily_row(date="2026-01-08")]
    windows = compute_windows(rows, cutoff, date(2026, 1, 1), date(2026, 1, 8))
    w7 = next(w for w in windows if w.window_id == "7d")
    assert w7.partial is True
    assert w7.observed_days == 1


def test_current_state_deterministic() -> None:
    cutoff = PackageCutoff.from_generated_at(GENERATED_AT_OCT5)
    rows = [
        _daily_row(date="2026-01-01", views=1),
        _daily_row(date="2026-01-05", views=99),
    ]
    current = compute_current_state(rows, cutoff=cutoff)
    assert len(current) == 1
    assert current[0].views == 99
    assert current[0].freshness_status != "UNKNOWN"


def test_changes_no_ai_labels() -> None:
    cutoff = PackageCutoff.from_generated_at(GENERATED_AT_OCT5)
    rows = [_daily_row()]
    windows = compute_windows(rows, cutoff, date(2026, 1, 1), date(2026, 10, 4))
    changes = compute_changes(windows, rows, cutoff)
    for ch in changes:
        assert "GOOD" not in ch.change_id
        assert "INCREASE_BID" not in ch.metric_name


def test_window_rates_disjoint_cohort_conservative_null() -> None:
    """CTR null when clicks/views exist only on disjoint days (aligned cohort)."""
    cutoff = PackageCutoff.from_generated_at(GENERATED_AT_OCT5)
    end = cutoff.last_closed_calendar_day
    start = end - timedelta(days=1)
    rows = [
        _daily_row(date=end.isoformat(), views=100, clicks=None),
        _daily_row(date=start.isoformat(), views=None, clicks=10),
    ]
    windows = compute_windows(rows, cutoff, start, end)
    w7 = next(w for w in windows if w.window_id == "7d")
    assert w7.ctr is None
    assert w7.clicks_sum == 10
    assert w7.views_sum == 100


def test_window_cpm_aligned_spend_views_cohort() -> None:
    """cpm_mean null when FACTUAL spend exists but no row has both spend and views."""
    cutoff = PackageCutoff.from_generated_at(GENERATED_AT_OCT5)
    end = cutoff.last_closed_calendar_day
    start = end - timedelta(days=1)
    rows = [
        _daily_row(
            date=end.isoformat(),
            views=None,
            clicks=None,
            spend_rub=50.0,
            query_spend_status=QuerySpendStatus.FACTUAL,
        ),
        _daily_row(
            date=start.isoformat(),
            views=None,
            clicks=None,
            spend_rub=25.0,
            query_spend_status=QuerySpendStatus.FACTUAL,
        ),
    ]
    windows = compute_windows(rows, cutoff, start, end)
    w7 = next(w for w in windows if w.window_id == "7d")
    assert w7.spend_status.value == "FACTUAL"
    assert w7.cpm_mean is None
    assert w7.cpc_mean is None


def test_window_cpo_requires_aligned_factual_orders() -> None:
    """CPO null when spend and orders are not on the same FACTUAL rows."""
    cutoff = PackageCutoff.from_generated_at(GENERATED_AT_OCT5)
    end = cutoff.last_closed_calendar_day
    rows = [
        _daily_row(
            date=end.isoformat(),
            orders=None,
            spend_rub=100.0,
            query_spend_status=QuerySpendStatus.FACTUAL,
        ),
    ]
    windows = compute_windows(rows, cutoff, end, end)
    w1 = next(w for w in windows if w.window_id == "1d")
    assert w1.cpo_rub is None


def test_position_missing_days_counts_absent_requested_days() -> None:
    """position_missing_days = requested - distinct position dates, not observed-position delta."""
    cutoff = PackageCutoff.from_generated_at(GENERATED_AT_OCT5)
    end = cutoff.last_closed_calendar_day
    start = end - timedelta(days=6)
    rows = [
        _daily_row(date=end.isoformat(), views=10),
        _daily_row(date=(end - timedelta(days=3)).isoformat(), views=10),
    ]
    rows[0] = rows[0].model_copy(update={"cluster_avg_pos": 5.0})
    rows[1] = rows[1].model_copy(update={"cluster_avg_pos": 6.0})
    windows = compute_windows(rows, cutoff, start, end)
    w7 = next(w for w in windows if w.window_id == "7d")
    assert w7.observed_days == 2
    assert w7.position_observed_days == 2
    assert w7.position_missing_days == 5


def test_position_mean_unweighted_when_views_missing() -> None:
    """Known positions without views → unweighted mean with honest metadata."""
    cutoff = PackageCutoff.from_generated_at(GENERATED_AT_OCT5)
    end = cutoff.last_closed_calendar_day
    rows = [
        _daily_row(date=end.isoformat(), views=None, clicks=1),
    ]
    rows[0] = rows[0].model_copy(update={"cluster_avg_pos": 4.0})
    windows = compute_windows(rows, cutoff, end, end)
    w1 = next(w for w in windows if w.window_id == "1d")
    assert w1.cluster_avg_pos_mean == 4.0
    assert w1.window_coverage["position_mean_mode"] == "unweighted"


def test_mtd_vs_prev_mtd_change_rows() -> None:
    cutoff = PackageCutoff.from_generated_at(GENERATED_AT_OCT5)
    rows = [_daily_row(date="2026-10-01", views=5), _daily_row(date="2026-09-01", views=3)]
    windows = compute_windows(rows, cutoff, date(2026, 9, 1), date(2026, 10, 4))
    changes = compute_changes(windows, rows, cutoff)
    assert any(c.change_id == "mtd_vs_prev_mtd" for c in changes)
