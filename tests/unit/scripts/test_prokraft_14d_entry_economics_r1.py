"""Unit tests for the PROKRAFT_14D_ENTRY_ECONOMICS_R1 pure aggregation seam."""

from __future__ import annotations

from datetime import date

from scripts.prokraft_14d_entry_economics_r1 import (
    _aggregate_orders,
    _build_daily_store_rows,
    _build_entry_rows,
    _build_physical_rows,
    _expand_fullstats,
)


def test_aggregate_orders_deduplicates_and_keeps_missing_gmv_distinct() -> None:
    """Supplier-page duplicates are removed without turning missing GMV into zero."""
    rows = [
        {
            "srid": "order-1",
            "date": "2026-09-05",
            "nmId": 10,
            "quantity": 2,
            "finishedPrice": 100,
        },
        {
            "srid": "order-1",
            "date": "2026-09-05",
            "nmId": 10,
            "quantity": 2,
            "finishedPrice": 100,
        },
        {
            "srid": "order-2",
            "date": "2026-09-06",
            "nmId": 10,
            "quantity": 1,
        },
    ]

    daily, by_nmid, gaps = _aggregate_orders(
        rows, date(2026, 9, 5), date(2026, 9, 18)
    )

    assert daily["2026-09-05"]["factual_orders"] == 1
    assert daily["2026-09-05"]["factual_units"] == 2.0
    assert daily["2026-09-05"]["factual_gmv_rub"] == 100.0
    assert daily["2026-09-06"]["factual_gmv_rub"] is None
    assert by_nmid[10]["factual_orders"] == 2
    assert "SUPPLIER_ORDER_GMV_FIELD_MISSING" in gaps


def test_logical_entry_does_not_double_count_multi_nmid_campaign_spend() -> None:
    """Auto/Search are one logical entry; ambiguous multi-NMID spend is NULL."""
    campaigns = [
        {"id": 11, "nm_settings": [{"nm_id": 10}]},
        {"id": 22, "nm_settings": [{"nm_id": 10}]},
        {"id": 33, "nm_settings": [{"nm_id": 10}, {"nm_id": 20}]},
    ]
    pg_rows = [
        {
            "id": 1,
            "adv_id": 11,
            "_search_adv_id": 22,
            "nmids": "[10]",
            "target_price_for_order": 20,
            "max_price_for_order": 30,
            "auto_budget_daily_limit": 100,
            "search_auto_budget_daily_limit": 100,
        }
    ]
    fullstats = [
        {
            "advertId": 11,
            "days": [
                {
                    "date": "2026-09-05",
                    "sum": 10,
                    "apps": [
                        {
                            "appType": 1,
                            "nms": [
                                {"nmId": 10, "orders": 1, "sum_price": 100},
                                {"nmId": 99, "orders": 1, "sum_price": 50},
                            ],
                        }
                    ],
                }
            ],
        },
        {
            "advertId": 22,
            "days": [
                {
                    "date": "2026-09-05",
                    "sum": 5,
                    "apps": [{"nms": [{"nmId": 10, "orders": 1, "sum_price": 40}]}],
                }
            ],
        },
        {
            "advertId": 33,
            "days": [
                {
                    "date": "2026-09-05",
                    "sum": 7,
                    "apps": [{"nms": [{"nmId": 20, "orders": 1, "sum_price": 30}]}],
                }
            ],
        },
    ]

    campaign_day, campaign_nm = _expand_fullstats(
        fullstats, date(2026, 9, 5), date(2026, 9, 18)
    )
    physical, memberships, physical_gaps = _build_physical_rows(
        campaigns,
        pg_rows,
        campaign_day,
        campaign_nm,
        date(2026, 9, 5),
        date(2026, 9, 18),
    )
    entries, entry_gaps = _build_entry_rows(
        physical,
        memberships,
        {},
        pg_rows,
        date(2026, 9, 5),
        date(2026, 9, 18),
        (10, 20),
    )

    entry_10 = next(row for row in entries if row["nm_id"] == 10)
    entry_20 = next(row for row in entries if row["nm_id"] == 20)
    store_daily = _build_daily_store_rows(
        date(2026, 9, 5),
        date(2026, 9, 18),
        date(2026, 9, 18),
        {},
        physical,
    )

    assert entry_10["physical_campaign_ids"] == [11, 22, 33]
    assert entry_10["spend_rub"] is None
    assert entry_10["spend_known_rub"] == 15.0
    assert entry_10["direct_orders"] == 2
    assert entry_10["associated_orders"] == 1
    assert entry_20["spend_rub"] is None
    assert entry_20["spend_known_rub"] == 0.0
    assert store_daily[0]["physical_spend_rub"] == 22.0
    assert any("MULTI_NMID_CAMPAIGN_SPEND_UNALLOCATED" in gap for gap in entry_gaps)
    assert physical_gaps == []


def test_priority_stop_low_stock_target_is_historical_only() -> None:
    """STOP_LOW_STOCK target remains present without invented current membership."""
    entries, gaps = _build_entry_rows(
        [],
        {},
        {},
        [],
        date(2026, 9, 5),
        date(2026, 9, 18),
        (751657528,),
    )

    assert gaps == []
    assert entries[0]["nm_id"] == 751657528
    assert entries[0]["historical_only"] is True
    assert entries[0]["physical_campaign_ids"] == []
    assert entries[0]["spend_rub"] is None
    assert "STOP_LOW_STOCK_HISTORICAL_ONLY" in entries[0]["evidence_quality"]


def test_zero_denominators_are_null_and_current_day_is_open_partial() -> None:
    """DRR/CPO do not manufacture infinity, and end day is explicitly partial."""
    daily = _build_daily_store_rows(
        date(2026, 9, 5),
        date(2026, 9, 18),
        date(2026, 9, 18),
        {},
        [],
    )

    assert daily[0]["store_drr"] is None
    assert daily[0]["headroom_10_rub"] == 0.0
    assert daily[-1]["day_state"] == "OPEN_PARTIAL"
