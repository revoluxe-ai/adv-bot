"""Stub-contract: shelf set_bid ContractCase ↔ AutoShelfBidSetter boundary."""

from __future__ import annotations

from types import SimpleNamespace

import pytest

from app.modules.shop_runner.service_manager.services.auto_shelf_bid_control_manager.auto_shelf_bid_setter import (
    AutoShelfBidControlWriteBlockedError,
    AutoShelfBidSetter,
)
from tests.unit.auto_bid_module_coexistence.shelf_set_bid_contract import (
    CONTRACT_ID,
    SHELF_SET_BID_CASES,
    RecordingPatchAutoAdvBids,
)


@pytest.mark.unit
def test_shelf_set_bid_contract_cases_cover_on_off() -> None:
    """Shared ContractCase: shelves ON may write; OFF must not."""
    assert CONTRACT_ID == "auto-shelf-set-bid-coexistence-v1"
    by_id = {c.case_id: c for c in SHELF_SET_BID_CASES}
    assert by_id["shelves_on_may_write"].expect_patch_call is True
    assert by_id["shelves_off_must_not"].expect_patch_call is False


@pytest.mark.unit
@pytest.mark.asyncio
async def test_autoshelf_setter_boundary_matches_shelves_on_contract(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Boundary: AutoShelfBidSetter.set_bid → patch shape = ContractCase."""
    case = next(c for c in SHELF_SET_BID_CASES if c.case_id == "shelves_on_may_write")
    monkeypatch.setenv("AUTO_SHELF_BID_CONTROL_DRY_RUN", "false")
    patch_fake = RecordingPatchAutoAdvBids()
    setter = AutoShelfBidSetter(wb_modifier=patch_fake)
    adv = SimpleNamespace(
        auto_adv_id=case.auto_adv_id,
        nmids=[case.nmid],
        bot_active=True,
        auto_shelf_bid_control_enabled=case.shelves_on,
    )
    await setter.set_bid(adv, bid_minor=case.bid_minor, currency=case.currency)
    patch_fake.assert_matches_case(case)


@pytest.mark.unit
@pytest.mark.asyncio
async def test_autoshelf_setter_boundary_blocks_inactive_bot(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """bot_active=False MUST block shelf write (TARGET write guard)."""
    case = next(c for c in SHELF_SET_BID_CASES if c.case_id == "shelves_on_may_write")
    monkeypatch.setenv("AUTO_SHELF_BID_CONTROL_DRY_RUN", "false")
    patch_fake = RecordingPatchAutoAdvBids()
    setter = AutoShelfBidSetter(wb_modifier=patch_fake)
    adv = SimpleNamespace(
        auto_adv_id=case.auto_adv_id,
        nmids=[case.nmid],
        bot_active=False,
        auto_shelf_bid_control_enabled=True,
    )
    with pytest.raises(AutoShelfBidControlWriteBlockedError):
        await setter.set_bid(adv, bid_minor=case.bid_minor, currency=case.currency)
    assert patch_fake.calls == []


@pytest.mark.unit
@pytest.mark.asyncio
async def test_autoshelf_setter_boundary_matches_shelves_off_contract(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """shelves_off: paid bot_active but shelf control disabled → no patch."""
    case = next(c for c in SHELF_SET_BID_CASES if c.case_id == "shelves_off_must_not")
    monkeypatch.setenv("AUTO_SHELF_BID_CONTROL_DRY_RUN", "false")
    patch_fake = RecordingPatchAutoAdvBids()
    setter = AutoShelfBidSetter(wb_modifier=patch_fake)
    adv = SimpleNamespace(
        auto_adv_id=case.auto_adv_id,
        nmids=[case.nmid],
        bot_active=True,
        auto_shelf_bid_control_enabled=case.shelves_on,
    )
    await setter.set_bid(adv, bid_minor=case.bid_minor, currency=case.currency)
    patch_fake.assert_matches_case(case)
