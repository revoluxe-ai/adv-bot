"""Unit: decision-table ad spend dedupes shared advert_id across contour legs."""

from __future__ import annotations

import pytest

pytestmark = pytest.mark.unit

from scripts.a1_glue_topology_web_review_collect import (
    WINDOWS,
    _decision_spend_for_contours,
    _unique_contour_adv_ids,
)

DATES_28 = {f"2026-08-{d:02d}" for d in range(9, 36)}  # 28 closed days


def _day_rows(adv_id: int, spend_per_day: float) -> list[dict]:
    return [
        {
            "advert_id": adv_id,
            "date": day,
            "day_spend": spend_per_day,
            "day_views": 0,
            "day_clicks": 0,
            "day_orders": 0,
            "day_sum_price": 0.0,
        }
        for day in DATES_28
    ]


def _sum_from_08_like(adv_ids: set[int], day_rows: list[dict], dates: set[str]) -> float:
    """Aggregate spend once per advert_id — mirrors 08_ADV_PERFORMANCE_WINDOWS semantics."""
    total = 0.0
    for adv_id in adv_ids:
        total += sum(
            r["day_spend"] for r in day_rows if r["advert_id"] == adv_id and r["date"] in dates
        )
    return round(total, 2)


def test_unique_contour_adv_ids_dedupes_shared_advert() -> None:
    """Same advert_id on search leg of contour A and auto leg of contour B counts once."""
    contours = [
        {"adv_setting_id": 1151722151, "auto_adv_id": 111, "search_adv_id": 39900211},
        {"adv_setting_id": 1151722152, "auto_adv_id": 39900211, "search_adv_id": None},
    ]
    assert _unique_contour_adv_ids(contours) == {111, 39900211}


def test_decision_spend_matches_08_unique_adv_aggregation() -> None:
    """Decision spend must not double-count when advert_id spans multiple contour legs."""
    shared_adv = 39900211
    other_adv = 222
    spend_per_day = 10.0
    day_rows = _day_rows(shared_adv, spend_per_day) + _day_rows(other_adv, spend_per_day / 2)
    contours = [
        {"adv_setting_id": 1, "auto_adv_id": other_adv, "search_adv_id": shared_adv},
        {"adv_setting_id": 2, "auto_adv_id": shared_adv, "search_adv_id": None},
    ]
    dates_7 = set(sorted(DATES_28)[-7:])
    dates_14 = set(sorted(DATES_28)[-14:])
    spend = _decision_spend_for_contours(contours, day_rows, (dates_7, dates_14, DATES_28))
    unique = _unique_contour_adv_ids(contours)
    for window, dates in zip(WINDOWS, (dates_7, dates_14, DATES_28)):
        expected = _sum_from_08_like(unique, day_rows, dates)
        assert spend[window] == expected
    # Without dedup, shared_adv would be counted twice on 28d window.
    inflated = sum(
        sum(r["day_spend"] for r in day_rows if r["advert_id"] == shared_adv and r["date"] in DATES_28)
        for _ in contours
        if shared_adv in (contours[0].get("search_adv_id"), contours[1].get("auto_adv_id"))
    )
    assert spend[28] < inflated
