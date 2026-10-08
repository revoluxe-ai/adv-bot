"""Missing WB metrics must not become factual zero in raw normalization."""

from __future__ import annotations

import pytest

from app.modules.attribution_facts.ingest.raw_fullstats import fullstats_item_to_raw_rows

pytestmark = pytest.mark.unit


def _item(**nm_fields: object) -> dict[str, object]:
    return {
        "advertId": 1,
        "days": [
            {
                "date": "2026-09-07",
                "orders": 5,
                "sum_price": 100,
                "apps": [
                    {
                        "appType": 1,
                        "nms": [{"nmId": 111, **nm_fields}],
                    }
                ],
            }
        ],
    }


def test_explicit_orders_zero_not_missing() -> None:
    rows = fullstats_item_to_raw_rows(_item(orders=0))
    assert len(rows) == 1
    assert rows[0].orders == 0


def test_orders_missing_stays_none() -> None:
    rows = fullstats_item_to_raw_rows(_item())
    assert len(rows) == 1
    assert rows[0].orders is None


def test_explicit_gmv_zero_not_missing() -> None:
    rows = fullstats_item_to_raw_rows(_item(sum_price=0))
    assert len(rows) == 1
    assert rows[0].gmv_rub is not None
    assert rows[0].gmv_rub == 0


def test_gmv_missing_stays_none() -> None:
    rows = fullstats_item_to_raw_rows(_item(orders=1))
    assert rows[0].gmv_rub is None
