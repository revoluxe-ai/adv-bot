"""Stub-contract: recording fake ↔ WBModifier Search lifecycle (empty-keywords).

Доказывает, что scenario_seam ожидания совпадают с thin-end WBModifier:
``pause/start_auction_campaign(complex_adv)`` → ``pause/start_campaign(search_adv_id)``.
"""

from __future__ import annotations

from typing import Any
from unittest.mock import AsyncMock, MagicMock

import pytest

from app.core.mp.wb.api.managers.wb_promotion_manager.wb_promotion_manager import (
    WBModifier,
)
from app.shared.domains.wb.enums import AdvType
from tests.unit.auto_updater_v3.empty_keywords_pause.wb_search_lifecycle_contract import (
    CONTRACT_ID,
    WB_SEARCH_LIFECYCLE_CASES,
    RecordingWbLifecycleModifier,
    WbSearchLifecycleContractCase,
)


class _BoundaryComplexAdv:
    """Минимальный ComplexAdv shape для WBModifier.get_adv_id_by_type."""

    def __init__(self, *, auto_adv_id: int = 9001, search_adv_id: int = 9002) -> None:
        self.auto_adv_id = auto_adv_id
        self.search_adv_id = search_adv_id
        self._search = MagicMock()
        self._search.adv_id = search_adv_id

    @property
    def auction_adv_id(self) -> int:
        return self.search_adv_id

    def get_adv_id_by_type(self, adv_type: AdvType) -> int:
        """Как ComplexAdv: AUTO → auto_adv_id, SEARCH → auction_adv_id."""
        if adv_type == AdvType.AUTO:
            return self.auto_adv_id
        if adv_type == AdvType.SEARCH:
            return self.auction_adv_id
        raise ValueError(adv_type)


def _case(case_id: str) -> WbSearchLifecycleContractCase:
    for case in WB_SEARCH_LIFECYCLE_CASES:
        if case.case_id == case_id:
            return case
    raise KeyError(case_id)


@pytest.mark.unit
def test_contract_cases_cover_search_pause_start_and_forbidden_auto() -> None:
    """Shared ContractCase set: Search pause/start allowed; Auto pause forbidden."""
    assert CONTRACT_ID == "empty-keywords-wb-search-lifecycle-v1"
    by_id = {c.case_id: c for c in WB_SEARCH_LIFECYCLE_CASES}
    assert by_id["pause_search_allowed"].routes_adv_type == AdvType.SEARCH
    assert by_id["start_search_recheck"].routes_adv_type == AdvType.SEARCH
    assert by_id["pause_auto_forbidden"].allowed_for_empty_keywords is False


@pytest.mark.unit
@pytest.mark.asyncio
async def test_recording_fake_matches_pause_search_contract_shape() -> None:
    """Fake call shape = (pause_auction_campaign, same complex_adv)."""
    case = _case("pause_search_allowed")
    adv = _BoundaryComplexAdv()
    fake = RecordingWbLifecycleModifier()
    await fake.pause_auction_campaign(adv)
    fake.assert_matches_case(case, complex_adv=adv, must_have_been_called=True)
    fake.assert_matches_case(
        _case("pause_auto_forbidden"),
        complex_adv=adv,
        must_have_been_called=False,
    )


@pytest.mark.unit
@pytest.mark.asyncio
async def test_wb_modifier_pause_auction_routes_search_adv_id() -> None:
    """boundary_adapter: real WBModifier.pause_auction → pause_campaign(search_id)."""
    case = _case("pause_search_allowed")
    assert case.routes_adv_type == AdvType.SEARCH
    captured: list[int] = []

    async def pause_campaign(adv_id: int) -> None:
        captured.append(adv_id)

    pm: Any = MagicMock()
    pm.pause_campaign = pause_campaign
    pm.start_campaign = AsyncMock()
    modifier = WBModifier(promotion_manager=pm)
    adv = _BoundaryComplexAdv(search_adv_id=9002)

    await modifier.pause_auction_campaign(adv)  # type: ignore[arg-type]

    assert captured == [9002]


@pytest.mark.unit
@pytest.mark.asyncio
async def test_wb_modifier_start_auction_routes_search_adv_id() -> None:
    """boundary_adapter: real WBModifier.start_auction → start_campaign(search_id)."""
    case = _case("start_search_recheck")
    assert case.routes_adv_type == AdvType.SEARCH
    captured: list[int] = []

    async def start_campaign(adv_id: int) -> None:
        captured.append(adv_id)

    pm: Any = MagicMock()
    pm.start_campaign = start_campaign
    pm.pause_campaign = AsyncMock()
    modifier = WBModifier(promotion_manager=pm)
    adv = _BoundaryComplexAdv(search_adv_id=9002)

    await modifier.start_auction_campaign(adv)  # type: ignore[arg-type]

    assert captured == [9002]


@pytest.mark.unit
@pytest.mark.asyncio
async def test_wb_modifier_pause_auto_routes_auto_not_search() -> None:
    """Forbidden path for empty-keywords: pause_auto → Auto id, not Search."""
    case = _case("pause_auto_forbidden")
    assert case.allowed_for_empty_keywords is False
    captured: list[int] = []

    async def pause_campaign(adv_id: int) -> None:
        captured.append(adv_id)

    pm: Any = MagicMock()
    pm.pause_campaign = pause_campaign
    modifier = WBModifier(promotion_manager=pm)
    adv = _BoundaryComplexAdv(auto_adv_id=9001, search_adv_id=9002)

    await modifier.pause_auto_campaign(adv)  # type: ignore[arg-type]

    assert captured == [9001]
    assert 9002 not in captured
