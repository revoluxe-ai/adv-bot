"""Mock-only regression for leg-CPO CH seed helper window math."""

from __future__ import annotations

from datetime import datetime

import pytest

from tests.support.leg_cpo_ch_seed import (
    LEG_CPO_FIXED_DAYS,
    LEG_CPO_FIXED_NOW,
    leg_cpo_seed_dates,
    resolve_leg_cpo_window,
)

pytestmark = pytest.mark.unit


def test_resolve_leg_cpo_window_matches_production_inclusive_days() -> None:
    """Inclusive calendar-day окно совпадает с ``leg_cpo.resolve_leg_cpo_window``."""
    start, end = resolve_leg_cpo_window(now=LEG_CPO_FIXED_NOW, days=LEG_CPO_FIXED_DAYS)
    assert start == datetime(2026, 9, 28, 12, 0, 0)
    assert end == LEG_CPO_FIXED_NOW


def test_leg_cpo_seed_dates_cover_full_window() -> None:
    """Seed dates включают обе границы observation window."""
    dates = leg_cpo_seed_dates(now=LEG_CPO_FIXED_NOW, days=LEG_CPO_FIXED_DAYS)
    assert dates == (datetime(2026, 9, 28).date(), datetime(2026, 9, 29).date())
