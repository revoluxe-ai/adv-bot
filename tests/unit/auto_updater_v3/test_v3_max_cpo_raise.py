"""Unit: in-memory V3 Raise MAX."""

from __future__ import annotations

from types import SimpleNamespace

import pytest

from app.modules.shop_runner.service_manager.services.auto_updater_v3.not_full_target_place import (
    campaign_overspend_from_plan_fact,
)
from app.modules.shop_runner.service_manager.services.auto_updater_v3.v3_max_cpo_raise import (
    apply_v3_max_cpo_raise_if_needed,
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


@pytest.mark.unit
def test_no_raise_when_fact_equals_db_max() -> None:
    adv = SimpleNamespace(max_price_for_order=120.0)
    assert not apply_v3_max_cpo_raise_if_needed(
        adv,
        fact_pay_for_order=120.0,
        toggle_enabled=True,
    )
    assert adv.max_price_for_order == 120.0


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
def test_raise_max_no_overspend_when_fact_within_operative_max() -> None:
    """После Raise operative max = fact → overspend false (не DB snapshot)."""
    adv = SimpleNamespace(max_price_for_order=500.0)
    fact_pfo = 800.0
    apply_v3_max_cpo_raise_if_needed(
        adv,
        fact_pay_for_order=fact_pfo,
        toggle_enabled=True,
    )
    operative_max = float(adv.max_price_for_order)
    assert operative_max == 800.0
    assert not campaign_overspend_from_plan_fact(fact_pfo, operative_max)


@pytest.mark.unit
def test_v3_raised_max_display_label() -> None:
    adv = SimpleNamespace(
        max_price_for_order=120.0,
        v3_substitute_fact_cpo_for_max=True,
    )
    assert v3_raised_max_display_label(adv, fact_pay_for_order=150.0) == "120 → 150"
    assert v3_raised_max_display_label(adv, fact_pay_for_order=100.0) is None


@pytest.mark.unit
def test_v3_raised_max_display_label_uses_original_max_cpo() -> None:
    adv = SimpleNamespace(
        max_price_for_order=800.0,
        v3_substitute_fact_cpo_for_max=True,
    )
    assert v3_raised_max_display_label(
        adv,
        fact_pay_for_order=800.0,
        original_max_cpo=500.0,
    ) == "500 → 800"
