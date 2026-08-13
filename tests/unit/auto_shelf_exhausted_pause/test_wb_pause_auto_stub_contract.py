"""Stub-contract + boundary shape for ASEP WB ``pause_auto_campaign``.

Shared ContractCase: ``wb_pause_auto_contract``. Production thin end:
``WBModifier.pause_auto_campaign`` → AdvType.AUTO.
"""

from __future__ import annotations

import inspect

import pytest

from app.core.mp.wb.api.managers.wb_promotion_manager.wb_promotion_manager import (
    WBModifier,
)
from app.shared.domains.wb.enums import AdvType
from tests.unit.auto_shelf_exhausted_pause.wb_pause_auto_contract import (
    CONTRACT_ID,
    WB_PAUSE_AUTO_CASES,
    RecordingWbAutoLifecycle,
)


@pytest.mark.unit
def test_wb_pause_auto_contract_cases_cover_allowed_forbidden() -> None:
    """Shared ContractCase set for ASEP Auto pause thin end."""
    assert CONTRACT_ID == "asep.wb.pause_auto_lifecycle.v1"
    by_id = {c.case_id: c for c in WB_PAUSE_AUTO_CASES}
    assert by_id["pause_auto_allowed"].expect_called is True
    assert by_id["pause_auto_allowed"].routes_adv_type == AdvType.AUTO
    assert by_id["pause_auction_forbidden"].expect_called is False
    assert by_id["pause_auction_forbidden"].allowed_for_shelf_exhausted is False


@pytest.mark.unit
def test_recording_fake_pause_auto_signature_matches_wb_modifier() -> None:
    """Boundary adapter: fake call shape = production ``pause_auto_campaign``.

    Production method is a thin awaitable with one positional ``complex_adv``.
    """
    fake_sig = inspect.signature(RecordingWbAutoLifecycle.pause_auto_campaign)
    fake_params = [p for p in fake_sig.parameters if p not in ("self",)]
    assert fake_params == ["complex_adv"]
    assert callable(WBModifier.pause_auto_campaign)
    assert inspect.iscoroutinefunction(RecordingWbAutoLifecycle.pause_auto_campaign)
    assert inspect.iscoroutinefunction(WBModifier.pause_auto_campaign)


@pytest.mark.unit
@pytest.mark.asyncio
async def test_recording_fake_matches_pause_auto_allowed_case() -> None:
    """Fake call shape parity with ContractCase pause_auto_allowed."""
    case = next(c for c in WB_PAUSE_AUTO_CASES if c.case_id == "pause_auto_allowed")
    fake = RecordingWbAutoLifecycle()
    adv = object()
    await fake.pause_auto_campaign(adv)
    fake.assert_matches_case(case, complex_adv=adv)
    forbidden = next(
        c for c in WB_PAUSE_AUTO_CASES if c.case_id == "pause_auction_forbidden"
    )
    fake.assert_matches_case(forbidden)
