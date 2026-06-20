"""Unit: AdvState.raise_cpo_ceiling и флаг V3 Raise MAX."""

from __future__ import annotations

from dataclasses import replace

import pytest

from app.modules.shop_runner.service_manager.services.auto_updater_v3.keyword_dto.dto.adv_state import (
    AdvState,
)


@pytest.mark.unit
def test_raise_cpo_ceiling_returns_none_without_fact() -> None:
    adv = replace(
        AdvState.empty(),
        max_pay_for_order=500.0,
        v3_substitute_fact_cpo_for_max=True,
    )
    assert adv.raise_cpo_ceiling is None


@pytest.mark.unit
def test_raise_cpo_ceiling_flag_off_uses_plan_max_only() -> None:
    adv = replace(
        AdvState.empty(),
        max_pay_for_order=500.0,
        fact_pay_for_order=800.0,
        v3_substitute_fact_cpo_for_max=False,
    )
    assert adv.raise_cpo_ceiling == 500.0


@pytest.mark.unit
def test_raise_cpo_ceiling_flag_on_uses_max_of_fact_and_plan() -> None:
    adv = replace(
        AdvState.empty(),
        max_pay_for_order=500.0,
        fact_pay_for_order=800.0,
        v3_substitute_fact_cpo_for_max=True,
    )
    assert adv.raise_cpo_ceiling == 800.0


@pytest.mark.unit
def test_raise_cpo_ceiling_flag_on_when_fact_below_plan() -> None:
    adv = replace(
        AdvState.empty(),
        max_pay_for_order=500.0,
        fact_pay_for_order=300.0,
        v3_substitute_fact_cpo_for_max=True,
    )
    assert adv.raise_cpo_ceiling == 500.0
