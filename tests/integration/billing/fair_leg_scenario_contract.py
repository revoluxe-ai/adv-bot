"""ContractCase для fair leg-pause billing scenario_seam (S4, S7, S9, S10).

Shared executable source: scenario_seam assertions ↔ Pricer / billing charge seam.
Spec: ``billing-fair-leg-pause`` (change ``fair-leg-pause-billing``).
"""

from __future__ import annotations

from dataclasses import dataclass

from app.modules.billing.pricer.tariffs import tariffs_for_auto_setting

CONTRACT_ID = "fair_leg.billing.metering_scenario.v1"


@dataclass(frozen=True)
class FairLegScenarioContractCase:
    """Ожидаемые effective_count и слоты для scenario_seam integration."""

    case_id: str
    scenario_label: str
    expected_effective_count: float
    expect_search_slot: bool
    """True когда Search-строка резолвится в паре; False для unresolved / absent link."""
    expected_billable_leg: str | None
    """``auto_leg`` | ``search_leg`` | None — единственная AdvPayment при charge 0.5."""
    tier_bracket_units: float | None = None
    """Для S10: ступень тарифа по сумме слотов (1.0 → bracket[1])."""


FAIR_LEG_SCENARIO_CASES: tuple[FairLegScenarioContractCase, ...] = (
    FairLegScenarioContractCase(
        case_id="s04_unresolved_search_link",
        scenario_label="Setup without Search link — anchor only",
        expected_effective_count=0.5,
        expect_search_slot=False,
        expected_billable_leg="auto_leg",
    ),
    FairLegScenarioContractCase(
        case_id="s07_only_search_started",
        scenario_label="Only Search leg started — half tariff",
        expected_effective_count=0.5,
        expect_search_slot=True,
        expected_billable_leg="search_leg",
    ),
    FairLegScenarioContractCase(
        case_id="s09_no_search_anchor_half",
        scenario_label="No Search leg but anchor in work — half tariff",
        expected_effective_count=0.5,
        expect_search_slot=False,
        expected_billable_leg="auto_leg",
    ),
    FairLegScenarioContractCase(
        case_id="s10_two_half_units_one_tier",
        scenario_label="Two half-units equal one tier unit",
        expected_effective_count=1.0,
        expect_search_slot=True,
        expected_billable_leg=None,
        tier_bracket_units=1.0,
    ),
)


def tier_price_for_units(units: float) -> float:
    """Месячный тариф AUTO для заданного effective_count (ступень bracket)."""
    bracket = max(1, int(units) if units == int(units) else int(units) + 1)
    return float(tariffs_for_auto_setting[bracket])


def legacy_full_active_day_total() -> float:
    """Дневная сумма за один full-active комплект (legacy baseline)."""
    from app.modules.billing.pricer.pricer import Pricer

    return Pricer.get_tariff_for_day(float(tariffs_for_auto_setting[1]))
