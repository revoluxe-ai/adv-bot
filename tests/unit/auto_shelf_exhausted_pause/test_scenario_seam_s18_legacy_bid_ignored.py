"""Scenario seam S18: shelves ON ⇒ legacy Auto bid path ignored (ASEP).

Reuses coexistence ContractCase ``forbidden_auto_shelves_on`` + production
bidder gate (orth L* coexistence). Not name-similarity only.
"""

from __future__ import annotations

import pytest

from tests.unit.auto_bid_module_coexistence.test_legacy_vs_shelf_bid_coexistence import (
    _case_update,
    _run_legacy_bidder_with_contract,
)
from tests.unit.auto_bid_module_coexistence.update_cpm_contract import CONTRACT_ID


@pytest.mark.unit
@pytest.mark.asyncio
async def test_s18_shelves_on_legacy_auto_bid_path_still_ignored(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """S18 scenario_seam: shelves ON → legacy Auto ``update_cpm`` not applied.

    Production entry: ``run_bidder_process_for_adv`` coexistence gate.
    Contract: ``legacy-auto-update-cpm-coexistence-v1`` /
    ``forbidden_auto_shelves_on``.
    """
    assert CONTRACT_ID == "legacy-auto-update-cpm-coexistence-v1"
    case = _case_update("forbidden_auto_shelves_on")
    assert case.shelves_on is True
    assert case.expect_auto_call is False
    update_cpm = await _run_legacy_bidder_with_contract(monkeypatch, case)
    update_cpm.assert_matches_case(case)
