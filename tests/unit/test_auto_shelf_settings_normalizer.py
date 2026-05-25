"""Unit-тесты нормализации legacy settings/state auto_shelf bid control."""

from __future__ import annotations

from datetime import datetime, timezone
from types import SimpleNamespace

import pytest

from app.modules.shop_runner.service_manager.services.auto_shelf_bid_control_manager.settings_normalizer import (
    compute_settings_repair,
    repair_max_bid_minor,
    repair_min_bid_distance_minor,
    repair_state_test_bid_minor,
)


def _settings(*, max_bid: int, distance: int = 100) -> SimpleNamespace:
    return SimpleNamespace(max_bid_minor=max_bid, min_bid_distance_minor=distance)


@pytest.mark.unit
def test_repair_max_legacy_500_to_50000() -> None:
    """max=500 при min WB 12000 → 50000 коп (500 ₽)."""
    fixed = repair_max_bid_minor(
        500,
        min_bid_minor=12_000,
        actual_bid_minor=20_000,
    )
    assert fixed == 50_000


@pytest.mark.unit
def test_repair_max_already_kopecks_unchanged() -> None:
    fixed = repair_max_bid_minor(
        50_000,
        min_bid_minor=12_000,
        actual_bid_minor=20_000,
    )
    assert fixed == 50_000


@pytest.mark.unit
def test_compute_settings_repair_changes_legacy() -> None:
    settings = _settings(max_bid=500, distance=1)
    result = compute_settings_repair(
        settings,  # type: ignore[arg-type]
        min_bid_minor=12_000,
        actual_bid_minor=20_000,
    )
    assert result.changed is True
    assert result.max_bid_minor == 50_000
    assert result.min_bid_distance_minor == 100


@pytest.mark.unit
def test_repair_state_test_bid_out_of_range_to_actual() -> None:
    state = SimpleNamespace(
        current_test_bid_minor=310,
        last_reason="invalid_bid_range",
    )
    changed = repair_state_test_bid_minor(
        state,  # type: ignore[arg-type]
        min_bid_minor=12_000,
        max_bid_minor=50_000,
        actual_bid_minor=20_000,
    )
    assert changed is True
    assert state.current_test_bid_minor == 20_000
    assert state.last_reason == "settings_units_repaired"


@pytest.mark.unit
def test_repair_state_test_bid_in_range_unchanged() -> None:
    state = SimpleNamespace(
        current_test_bid_minor=20_000,
        last_reason="initialized",
    )
    changed = repair_state_test_bid_minor(
        state,  # type: ignore[arg-type]
        min_bid_minor=12_000,
        max_bid_minor=50_000,
        actual_bid_minor=20_000,
    )
    assert changed is False
