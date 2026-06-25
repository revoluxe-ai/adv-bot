"""Stable UI view-models for rec_system bid recommendations."""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any, cast

_EXPECTED_RANKED_FIELDS: tuple[str, ...] = (
    "bid",
    "expected_daily_impressions",
    "confidence",
    "uncertainty",
    "own_anchor",
    "main_score",
    "test_score",
)

_PLAN_RANKED_FIELDS: tuple[str, ...] = (
    "bid",
    "ctr",
    "expected_impressions",
    "expected_clicks",
    "expected_orders",
    "expected_cost_rub",
    "expected_order_cost_rub",
    "resolved_order_cost_rub",
    "projected_sales",
    "sales_gap",
    "abs_sales_gap",
    "order_cost_overlimit_rub",
    "sales_dist",
    "order_cost_overlimit_dist",
    "plan_distance_score",
)

_PLAN_RANKED_ALIASES: tuple[tuple[str, str], ...] = (
    ("expected_daily_impressions", "expected_impressions"),
    ("expected_daily_clicks", "expected_clicks"),
    ("expected_daily_orders", "expected_orders"),
    ("cpo_rub", "expected_order_cost_rub"),
)

_DIAGNOSTICS_FIELDS: tuple[str, ...] = (
    "bucket_count",
    "hour_observation_count",
    "bid_count",
    "hour_count",
)


def _pick_fields(row: dict[str, Any], fields: tuple[str, ...]) -> dict[str, Any]:
    """Return a stable field subset preserving declared order."""
    return {field: row.get(field) for field in fields}


def _build_plan_ranked_view_row(row: dict[str, Any]) -> dict[str, Any]:
    """Build a Telegram-facing plan row with forecast aliases.

    The UI reads concise forecast labels, while the ranking engine keeps its
    original internal keys for compatibility with analytical tests.
    """
    view_row = _pick_fields(row, _PLAN_RANKED_FIELDS)
    for alias, source in _PLAN_RANKED_ALIASES:
        alias_value = row.get(alias)
        view_row[alias] = alias_value if alias_value is not None else row.get(source)
    return view_row


def build_rec_bid_recommendation_view(result: Mapping[str, object]) -> dict[str, Any]:
    """Build a stable UI view from get_rec_bid_recommendations/debug result."""
    diagnostics = cast(dict[str, Any], result.get("diagnostics", {}))
    bid_result = cast(dict[str, Any], result.get("bid_result", {}))
    expected_ranked = cast(list[dict[str, Any]], bid_result.get("expected_ranked", []))
    plan_ranked = cast(list[dict[str, Any]], result.get("plan_ranked", []))

    return {
        "diagnostics": _pick_fields(diagnostics, _DIAGNOSTICS_FIELDS),
        "best_expected_bid": result.get("best_expected_bid"),
        "best_plan_bid": result.get("best_plan_bid"),
        "expected_ranked": [
            _pick_fields(row, _EXPECTED_RANKED_FIELDS) for row in expected_ranked
        ],
        "plan_ranked": [_build_plan_ranked_view_row(row) for row in plan_ranked],
    }
