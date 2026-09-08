"""Unit tests for the strict factual A1 read-only ZIP collector."""

from __future__ import annotations

import json
from datetime import date, datetime

from scripts import a1_strict_read_only_contract_collect as collector


def test_closed_dates_are_closed_only() -> None:
    """Closed window ends on yesterday and never includes the open day."""
    assert collector._closed_dates(date(2026, 9, 7), 3) == {
        "2026-09-05",
        "2026-09-06",
        "2026-09-07",
    }


def test_aggregate_day_rows_uses_campaign_totals_once() -> None:
    """Spend comes from day totals, not the nested nm-level spend."""
    raw = [
        {
            "advertId": 39900256,
            "days": [
                {
                    "date": "2026-09-07T00:00:00Z",
                    "views": 100,
                    "clicks": 10,
                    "sum": 25.5,
                    "apps": [
                        {
                            "nms": [
                                {
                                    "nmId": 837395782,
                                    "sum": 12.0,
                                    "views": 80,
                                }
                            ]
                        }
                    ],
                },
                {
                    "date": "2026-09-08T00:00:00Z",
                    "views": 500,
                    "clicks": 50,
                    "sum": 100.0,
                },
            ],
        }
    ]

    rows = collector._aggregate_day_rows(raw, date(2026, 9, 7))

    assert rows[(39900256, "2026-09-07")] == {
        "adv_id": 39900256,
        "date": "2026-09-07",
        "views": 100,
        "clicks": 10,
        "spend": 25.5,
    }
    assert (39900256, "2026-09-08") not in rows


def test_campaign_metrics_split_direct_and_associated() -> None:
    """Campaign direct attribution uses promoted nmIDs; others stay associated."""
    day_rows = {
        (39900256, "2026-09-07"): {
            "adv_id": 39900256,
            "date": "2026-09-07",
            "views": 100,
            "clicks": 10,
            "spend": 25.5,
        }
    }
    nm_rows = {
        (39900256, "2026-09-07", 837395782): {
            "adv_id": 39900256,
            "date": "2026-09-07",
            "nm_id": 837395782,
            "views": 1,
            "clicks": 1,
            "carts": 2,
            "orders": 3,
            "gmv": 300.0,
        },
        (39900256, "2026-09-07", 14824677): {
            "adv_id": 39900256,
            "date": "2026-09-07",
            "nm_id": 14824677,
            "views": 1,
            "clicks": 1,
            "carts": 1,
            "orders": 2,
            "gmv": 200.0,
        },
    }

    metrics = collector._campaign_window_metrics(
        {39900256},
        {"2026-09-07"},
        day_rows,
        nm_rows,
        promoted_nmids_by_campaign={39900256: {837395782}},
    )

    assert metrics["direct_orders"] == 3
    assert metrics["associated_orders"] == 2
    assert metrics["direct_gmv"] == 300.0
    assert metrics["associated_gmv"] == 200.0


def test_promo_snapshot_preserves_fresh_cashback_fields() -> None:
    """Balance conversion keeps the requested fields and checked timestamp."""
    snapshot = collector._promo_snapshot(
        {"cashbacks": [{"sum": 42800, "percent": 50, "expiration_date": "2026-09-11"}]},
        datetime(2026, 9, 8, 18, 0, tzinfo=collector.MSK),
    )

    assert snapshot["cashback_sum"] == 42800
    assert snapshot["cashback_percent"] == 50
    assert snapshot["expiration_date"] == "2026-09-11"
    assert snapshot["checked_at_msk"].endswith("+03:00")


def test_primary_layout_is_exact(tmp_path) -> None:
    """Primary root contains only the declared files and raw directory."""
    root = tmp_path / "package"
    root.mkdir()
    for filename in collector.PRIMARY_FILES:
        (root / filename).write_text("", encoding="utf-8")
    (root / "raw").mkdir()

    collector._validate_layout(root)


def test_manifest_write_counts_are_zero() -> None:
    """Every declared production write counter remains zero."""
    assert set(collector.SAFETY_WRITE_COUNTS) == {
        "WB_API_WRITES",
        "CAMPAIGN_WRITES",
        "STATUS_WRITES",
        "BID_WRITES",
        "BUDGET_WRITES",
        "TOPUP_WRITES",
        "CPO_WRITES",
        "AGGRESSION_WRITES",
        "EXCEL_WRITES",
        "POSTGRES_WRITES",
        "CLICKHOUSE_WRITES",
        "REDIS_WRITES",
    }
    assert all(value == 0 for value in collector.SAFETY_WRITE_COUNTS.values())


def test_promo_json_is_json_serializable() -> None:
    """Promo snapshot contains no model objects that bypass JSON encoding."""
    payload = collector._promo_snapshot({"cashbacks": []}, datetime.now(collector.MSK))

    json.dumps(payload, ensure_ascii=False)
