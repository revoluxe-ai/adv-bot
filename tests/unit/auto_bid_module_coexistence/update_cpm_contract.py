"""ContractCase + recording fake для ``WBApi.update_cpm`` (legacy Auto vs shelves).

Change: pin-legacy-autobidder-vs-shelf-coexistence / GAP COEXIST-01.
Общий executable source: scenario_seam assertions ↔ stub_contract ↔ boundary
shape ``update_cpm(adv_id, nmid, new_bid) -> None`` (PATCH adv/v0/bids body).
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Literal

CONTRACT_ID = "legacy-auto-update-cpm-coexistence-v1"

UpdateCpmMode = Literal["allowed_auto", "forbidden_auto", "search_sibling"]

# Shared request body shape for adv/v0/bids (matches AdvMixin.__get_update_cpm_data).
UPDATE_CPM_BIDS_BODY_SHAPE: dict[str, Any] = {
    "bids": [
        {
            "advert_id": 0,
            "nm_bids": [{"nm": 0, "bid": 0}],
        }
    ]
}


@dataclass(frozen=True)
class UpdateCpmContractCase:
    """Ожидаемый thin-end вызов ``update_cpm`` при coexistence flags."""

    case_id: str
    mode: UpdateCpmMode
    auto_adv_id: int
    search_adv_id: int | None
    nmid: int
    new_bid: int
    shelves_on: bool
    bidder_for_auto: bool
    expect_auto_call: bool
    expect_search_call: bool


UPDATE_CPM_CASES: tuple[UpdateCpmContractCase, ...] = (
    UpdateCpmContractCase(
        case_id="forbidden_auto_shelves_on",
        mode="forbidden_auto",
        auto_adv_id=333,
        search_adv_id=444,
        nmid=701,
        new_bid=105,
        shelves_on=True,
        bidder_for_auto=True,
        expect_auto_call=False,
        expect_search_call=True,
    ),
    UpdateCpmContractCase(
        case_id="allowed_auto_shelves_off",
        mode="allowed_auto",
        auto_adv_id=333,
        search_adv_id=444,
        nmid=701,
        new_bid=105,
        shelves_on=False,
        bidder_for_auto=True,
        expect_auto_call=True,
        expect_search_call=True,
    ),
    UpdateCpmContractCase(
        case_id="search_sibling_ungated",
        mode="search_sibling",
        auto_adv_id=333,
        search_adv_id=444,
        nmid=701,
        new_bid=105,
        shelves_on=True,
        bidder_for_auto=True,
        expect_auto_call=False,
        expect_search_call=True,
    ),
)


def update_cpm_request_body(adv_id: int, nmid: int, new_bid: int) -> dict[str, Any]:
    """Golden body shape for PATCH adv/v0/bids (production ``__get_update_cpm_data``)."""
    return {
        "bids": [
            {
                "advert_id": adv_id,
                "nm_bids": [{"nm": nmid, "bid": int(new_bid)}],
            }
        ]
    }


@dataclass
class RecordingFakeUpdateCpm:
    """Thin-end fake после coexistence gate: ``async update_cpm(adv_id, nmid, new_bid)``."""

    calls: list[tuple[int, int, int]] = field(default_factory=list)

    async def __call__(self, adv_id: int, nmid: int, new_bid: int) -> None:
        """Сигнатура как ``WBApi.update_cpm``."""
        self.calls.append((int(adv_id), int(nmid), int(new_bid)))

    def auto_calls(self, auto_adv_id: int) -> list[tuple[int, int, int]]:
        """Вызовы только для Auto adv_id."""
        return [c for c in self.calls if c[0] == auto_adv_id]

    def search_calls(self, search_adv_id: int) -> list[tuple[int, int, int]]:
        """Вызовы только для Search adv_id."""
        return [c for c in self.calls if c[0] == search_adv_id]

    def assert_matches_case(self, case: UpdateCpmContractCase) -> None:
        """Executable parity: auto/search call presence per ContractCase."""
        auto = self.auto_calls(case.auto_adv_id)
        if case.expect_auto_call:
            assert len(auto) == 1, f"{case.case_id}: expected Auto update_cpm"
            assert auto[0][0] == case.auto_adv_id
            assert auto[0][1] == case.nmid
            assert isinstance(auto[0][2], int) and auto[0][2] > 0
        else:
            assert auto == [], f"{case.case_id}: forbidden Auto update_cpm {auto}"
        if case.search_adv_id is not None and case.expect_search_call:
            search = self.search_calls(case.search_adv_id)
            assert len(search) >= 1, f"{case.case_id}: expected Search update_cpm"
            assert search[0][0] == case.search_adv_id
            assert search[0][1] == case.nmid
            assert isinstance(search[0][2], int) and search[0][2] > 0
        elif case.search_adv_id is not None and not case.expect_search_call:
            assert self.search_calls(case.search_adv_id) == []
