"""Unit tests for rec_system bid recommendation view-models."""

from __future__ import annotations

from app.domain.rec_system_bid_math.view_models import (
    build_rec_bid_recommendation_view,
)


def test_build_rec_bid_recommendation_view_filters_extra_fields_and_keeps_order() -> None:
    result = {
        "diagnostics": {
            "bucket_count": 10,
            "hour_observation_count": 4,
            "bid_count": 2,
            "hour_count": 1,
            "extra_diagnostic": "drop-me",
        },
        "best_expected_bid": 35000,
        "best_plan_bid": 12000,
        "bid_result": {
            "expected_ranked": [
                {
                    "bid": 35000,
                    "expected_daily_impressions": 115847.18,
                    "confidence": 0.2,
                    "uncertainty": 92735.11,
                    "own_anchor": 0.0037,
                    "main_score": 69479.62,
                    "test_score": 185398.51,
                    "drop_me": "extra-expected",
                },
                {
                    "bid": 12000,
                    "expected_daily_impressions": 30182.81,
                    "confidence": 0.9,
                    "uncertainty": 2904.16,
                    "own_anchor": 0.3713,
                    "main_score": 28730.73,
                    "test_score": 32360.94,
                    "drop_me": "extra-expected-2",
                },
            ]
        },
        "plan_ranked": [
            {
                "bid": 12000,
                "ctr": 0.024,
                "expected_impressions": 30182.81,
                "expected_clicks": 748.0,
                "expected_orders": 25.43,
                "expected_cost_rub": 3621.94,
                "expected_order_cost_rub": 142.41,
                "resolved_order_cost_rub": 590.0,
                "projected_sales": 75.43,
                "sales_gap": -314.57,
                "abs_sales_gap": 314.57,
                "order_cost_overlimit_rub": 0.0,
                "sales_dist": 0.92,
                "order_cost_overlimit_dist": 0.0,
                "plan_distance_score": 0.92,
                "drop_me": "extra-plan",
            },
            {
                "bid": 35000,
                "ctr": 0.017,
                "expected_impressions": 115847.18,
                "expected_clicks": 2032.0,
                "expected_orders": 69.08,
                "expected_cost_rub": 40546.51,
                "expected_order_cost_rub": 586.94,
                "resolved_order_cost_rub": 590.0,
                "projected_sales": 119.08,
                "sales_gap": -270.92,
                "abs_sales_gap": 270.92,
                "order_cost_overlimit_rub": 0.0,
                "sales_dist": 0.79,
                "order_cost_overlimit_dist": 0.0,
                "plan_distance_score": 0.79,
                "drop_me": "extra-plan-2",
            },
        ],
        "extra_root": "drop-me",
    }

    view = build_rec_bid_recommendation_view(result)

    assert view == {
        "diagnostics": {
            "bucket_count": 10,
            "hour_observation_count": 4,
            "bid_count": 2,
            "hour_count": 1,
        },
        "best_expected_bid": 35000,
        "best_plan_bid": 12000,
        "expected_ranked": [
            {
                "bid": 35000,
                "expected_daily_impressions": 115847.18,
                "confidence": 0.2,
                "uncertainty": 92735.11,
                "own_anchor": 0.0037,
                "main_score": 69479.62,
                "test_score": 185398.51,
            },
            {
                "bid": 12000,
                "expected_daily_impressions": 30182.81,
                "confidence": 0.9,
                "uncertainty": 2904.16,
                "own_anchor": 0.3713,
                "main_score": 28730.73,
                "test_score": 32360.94,
            },
        ],
        "plan_ranked": [
            {
                "bid": 12000,
                "ctr": 0.024,
                "expected_impressions": 30182.81,
                "expected_clicks": 748.0,
                "expected_orders": 25.43,
                "expected_cost_rub": 3621.94,
                "expected_order_cost_rub": 142.41,
                "expected_daily_impressions": 30182.81,
                "expected_daily_clicks": 748.0,
                "expected_daily_orders": 25.43,
                "cpo_rub": 142.41,
                "resolved_order_cost_rub": 590.0,
                "projected_sales": 75.43,
                "sales_gap": -314.57,
                "abs_sales_gap": 314.57,
                "order_cost_overlimit_rub": 0.0,
                "sales_dist": 0.92,
                "order_cost_overlimit_dist": 0.0,
                "plan_distance_score": 0.92,
            },
            {
                "bid": 35000,
                "ctr": 0.017,
                "expected_impressions": 115847.18,
                "expected_clicks": 2032.0,
                "expected_orders": 69.08,
                "expected_cost_rub": 40546.51,
                "expected_order_cost_rub": 586.94,
                "expected_daily_impressions": 115847.18,
                "expected_daily_clicks": 2032.0,
                "expected_daily_orders": 69.08,
                "cpo_rub": 586.94,
                "resolved_order_cost_rub": 590.0,
                "projected_sales": 119.08,
                "sales_gap": -270.92,
                "abs_sales_gap": 270.92,
                "order_cost_overlimit_rub": 0.0,
                "sales_dist": 0.79,
                "order_cost_overlimit_dist": 0.0,
                "plan_distance_score": 0.79,
            },
        ],
    }
