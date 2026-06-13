"""Unit: in-memory V3 Raise MAX."""

from __future__ import annotations

from types import SimpleNamespace

import pytest

from app.modules.shop_runner.service_manager.services.auto_updater_v3.v3_max_cpo_raise import (
    V3_MAX_PRICE_FOR_ORDER_DB_ATTR,
    apply_v3_max_cpo_raise_if_needed,
    v3_max_raise_db_value,
    v3_raised_max_display_label,
)


@pytest.mark.unit
def test_raise_when_fact_above_db_max() -> None:
    adv = SimpleNamespace(max_price_for_order=120.0)
    assert apply_v3_max_cpo_raise_if_needed(
        adv,
        fact_pay_for_order=150.0,
        toggle_enabled=True,
    )
    assert adv.max_price_for_order == 150.0
    assert getattr(adv, V3_MAX_PRICE_FOR_ORDER_DB_ATTR) == 120.0
    assert v3_max_raise_db_value(adv) == 120.0


@pytest.mark.unit
def test_no_raise_when_fact_equals_db_max() -> None:
    adv = SimpleNamespace(max_price_for_order=120.0)
    assert not apply_v3_max_cpo_raise_if_needed(
        adv,
        fact_pay_for_order=120.0,
        toggle_enabled=True,
    )
    assert adv.max_price_for_order == 120.0
    assert v3_max_raise_db_value(adv) is None


@pytest.mark.unit
def test_no_raise_when_toggle_off() -> None:
    adv = SimpleNamespace(max_price_for_order=120.0)
    assert not apply_v3_max_cpo_raise_if_needed(
        adv,
        fact_pay_for_order=150.0,
        toggle_enabled=False,
    )
    assert adv.max_price_for_order == 120.0


@pytest.mark.unit
def test_v3_raised_max_display_label() -> None:
    adv = SimpleNamespace(
        max_price_for_order=120.0,
        v3_substitute_fact_cpo_for_max=True,
    )
    assert v3_raised_max_display_label(adv, fact_pay_for_order=150.0) == "120 → 150"
    assert v3_raised_max_display_label(adv, fact_pay_for_order=100.0) is None
