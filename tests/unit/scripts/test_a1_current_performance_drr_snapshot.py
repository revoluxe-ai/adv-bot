"""Unit: contour PG pick and delta from daily rows (A1 perf/DRR snapshot)."""

from __future__ import annotations

from datetime import date, timedelta

import pytest

pytestmark = pytest.mark.unit

from scripts.a1_current_performance_drr_snapshot import (
    BASELINE_DAY,
    _delta_rows,
    _pick_pg_contour,
)


def test_pick_pg_contour_prefers_adv_setting_id_over_wb_only() -> None:
    contours = [
        {
            "adv_setting_id": None,
            "auto_adv_id": 999,
            "search_adv_id": None,
            "name": "WB_ONLY_UNMAPPED_PG",
            "bot_active": "GAP",
        },
        {
            "adv_setting_id": 1151722151,
            "auto_adv_id": 17906286,
            "search_adv_id": 20646357,
            "bot_active": "True",
            "auto_daily_limit": "200",
        },
    ]
    picked = _pick_pg_contour(contours, {})
    assert picked["adv_setting_id"] == 1151722151
    assert picked["bot_active"] == "True"


def test_pick_pg_contour_merges_pg_by_adv_for_wb_only() -> None:
    contours = [
        {
            "adv_setting_id": None,
            "auto_adv_id": 7974113,
            "search_adv_id": None,
            "name": "WB_ONLY_UNMAPPED_PG",
            "bot_active": "GAP",
        },
    ]
    pg_by_adv = {
        7974113: {
            "id": "42",
            "bot_active": "True",
            "auto_budget_daily_limit": "200",
            "search_auto_budget_daily_limit": "150",
            "strategy": "TARGET_CPO",
        }
    }
    picked = _pick_pg_contour(contours, pg_by_adv)
    assert picked["bot_active"] == "True"
    assert picked["auto_daily_limit"] == "200"
    assert picked["search_daily_limit"] == "150"


def test_delta_rows_from_daily_not_external_zip() -> None:
    closed_end = date(2026, 9, 7)
    sales_daily: dict[str, dict] = {}
    spend_daily: dict[str, dict] = {}
    topup_daily: dict[str, dict] = {}
    d = date(2026, 8, 25)
    while d <= closed_end:
        key = d.isoformat()
        sales_daily[key] = {"factual_order_value": 1000.0}
        spend_daily[key] = {"gross_ad_spend": 100.0}
        topup_daily[key] = {
            "promo_used_on_deposits": 0.0,
            "ordinary_funds_used_on_deposits": 0.0,
        }
        d += timedelta(days=1)

    cur7_from = closed_end - timedelta(days=6)
    current_windows = [
        {
            "window_label": "CURRENT_7D",
            "period_from": cur7_from.isoformat(),
            "period_to": closed_end.isoformat(),
            "factual_order_value": 7000.0,
            "gross_ad_spend": 700.0,
            "gross_drr": 10.0,
        }
    ]
    rows = _delta_rows(
        baseline_end=BASELINE_DAY,
        current_closed_end=closed_end,
        sales_daily=sales_daily,
        spend_daily=spend_daily,
        topup_daily=topup_daily,
        current_windows=current_windows,
        orders=[],
        day_rows=[],
        nmid_category={},
        nm_contours={},
        inventory={},
    )
    store_rows = [r for r in rows if r["metric"] == "store_7d_factual_order_value"]
    assert store_rows
    assert store_rows[0]["baseline_period_to"] == BASELINE_DAY.isoformat()
    assert store_rows[0]["current_period_to"] == closed_end.isoformat()
    assert store_rows[0]["baseline_value"] == 7000.0
    assert store_rows[0]["current_value"] == 7000.0
    assert not any(r.get("note") == "BASELINE_OR_CURRENT_7D_MISSING" for r in rows)
