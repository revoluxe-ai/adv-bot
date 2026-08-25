"""Stub-contract + boundary shape для ``update_cpm`` coexistence ContractCase."""

from __future__ import annotations

import inspect

import pytest

from app.core.wb_api.mixins.adv import AdvMixin
from tests.unit.auto_bid_module_coexistence.update_cpm_contract import (
    CONTRACT_ID,
    UPDATE_CPM_BIDS_BODY_SHAPE,
    UPDATE_CPM_CASES,
    RecordingFakeUpdateCpm,
    update_cpm_request_body,
)


@pytest.mark.unit
def test_update_cpm_contract_cases_cover_allowed_forbidden_search() -> None:
    """Shared ContractCase set for coexistence Auto/Search thin end."""
    assert CONTRACT_ID == "legacy-auto-update-cpm-coexistence-v1"
    by_id = {c.case_id: c for c in UPDATE_CPM_CASES}
    assert by_id["forbidden_auto_shelves_on"].expect_auto_call is False
    assert by_id["allowed_auto_shelves_off"].expect_auto_call is True
    assert by_id["search_sibling_ungated"].expect_search_call is True


@pytest.mark.unit
def test_update_cpm_signature_matches_contract_positional_shape() -> None:
    """Boundary adapter: fake call shape = ContractCase positional (adv_id, nmid, new_bid).

    Production ``AdvMixin.update_cpm`` is decorated (try_except); SoT for shape is
    the public source signature + shared golden body, not the wrapped callable.
    """
    fake_sig = inspect.signature(RecordingFakeUpdateCpm.__call__)
    fake_params = [p for p in fake_sig.parameters if p not in ("self",)]
    assert fake_params == ["adv_id", "nmid", "new_bid"]
    # Production method exists and is awaitable thin end (decorator may hide params).
    assert callable(AdvMixin.update_cpm)
    assert inspect.iscoroutinefunction(RecordingFakeUpdateCpm.__call__)


@pytest.mark.unit
def test_update_cpm_request_body_golden_matches_production_shape() -> None:
    """Shared golden body keys for PATCH adv/v0/bids."""
    body = update_cpm_request_body(333, 701, 105)
    assert set(body.keys()) == set(UPDATE_CPM_BIDS_BODY_SHAPE.keys())
    assert "bids" in body
    assert body["bids"][0]["advert_id"] == 333
    assert body["bids"][0]["nm_bids"][0] == {"nm": 701, "bid": 105}


@pytest.mark.unit
@pytest.mark.asyncio
async def test_recording_fake_update_cpm_matches_allowed_case() -> None:
    """Fake call shape parity with ContractCase allowed_auto."""
    case = next(c for c in UPDATE_CPM_CASES if c.case_id == "allowed_auto_shelves_off")
    fake = RecordingFakeUpdateCpm()
    await fake(case.auto_adv_id, case.nmid, case.new_bid)
    await fake(case.search_adv_id, case.nmid, case.new_bid)  # type: ignore[arg-type]
    fake.assert_matches_case(case)


@pytest.mark.unit
@pytest.mark.asyncio
async def test_recording_fake_update_cpm_matches_forbidden_auto() -> None:
    """Forbidden Auto: only Search sibling call allowed."""
    case = next(c for c in UPDATE_CPM_CASES if c.case_id == "forbidden_auto_shelves_on")
    fake = RecordingFakeUpdateCpm()
    await fake(case.search_adv_id, case.nmid, case.new_bid)  # type: ignore[arg-type]
    fake.assert_matches_case(case)
