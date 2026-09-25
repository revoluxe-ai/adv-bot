"""Unit: A1 current-state gap collector CLI defaults."""

from __future__ import annotations

from datetime import date

import pytest

pytestmark = pytest.mark.unit

from scripts.a1_current_state_gap_collect import parse_args, _store_economics


def test_parse_args_defaults() -> None:
    args = parse_args([])
    assert args.closed_start == "2026-09-07"
    assert args.closed_end == "2026-09-13"
    assert args.open_day == "2026-09-14"


def test_store_economics_closed_vs_open() -> None:
    orders = [
        {"date": "2026-09-10", "nmId": 1, "quantity": 2, "totalPrice": 100.0, "srid": "a"},
        {"date": "2026-09-14", "nmId": 1, "quantity": 1, "totalPrice": 50.0, "srid": "b"},
    ]
    out = _store_economics(
        orders,
        [],
        date(2026, 9, 7),
        date(2026, 9, 13),
        date(2026, 9, 14),
    )
    assert out["closed_totals"]["units"] == 2
    assert out["open_day_totals"]["units"] == 1
