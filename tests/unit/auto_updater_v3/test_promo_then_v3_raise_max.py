"""Unit: V3 Raise MAX применяется после promo-effective max."""

from __future__ import annotations

from dataclasses import replace

import pytest

from app.modules.shop_runner.service_manager.services.auto_updater_v3.keyword_dto.dto.adv_state import (
    AdvState,
)


@pytest.mark.unit
def test_v3_raise_max_uses_promo_effective_plan_max() -> None:
    """Сначала PromoMaxCPO, затем max(fact, effective max)."""
    promo_max = 625.0
    fact = 800.0
    adv = replace(
        AdvState.empty(),
        max_pay_for_order=promo_max,
        fact_pay_for_order=fact,
        v3_substitute_fact_cpo_for_max=True,
    )
    assert adv.raise_cpo_ceiling == 800.0

    below = replace(
        AdvState.empty(),
        max_pay_for_order=promo_max,
        fact_pay_for_order=500.0,
        v3_substitute_fact_cpo_for_max=True,
    )
    assert below.raise_cpo_ceiling == 625.0


@pytest.mark.unit
def test_v3_and_promo_stay_independent_without_global_two_x_cap() -> None:
    """Owner-requested independent flags may compose above the base max."""
    adv = replace(
        AdvState.empty(),
        max_pay_for_order=1000.0,
        fact_pay_for_order=1500.0,
        v3_substitute_fact_cpo_for_max=True,
    )

    assert adv.raise_cpo_ceiling == 1500.0
