"""ContractCase + recording fake для shelf ``set_bid`` / ``patch_auto_adv_bids_kopecks``.

Change: pin-legacy-autobidder-vs-shelf-coexistence / GAP COEXIST-02.
Общий source: coexistence scenario ↔ AutoShelfBidSetter boundary.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Literal

CONTRACT_ID = "auto-shelf-set-bid-coexistence-v1"

ShelfBidMode = Literal["shelves_on_may_write", "shelves_off_must_not"]


@dataclass(frozen=True)
class ShelfSetBidContractCase:
    """Ожидание thin-end записи ставки полок при coexistence."""

    case_id: str
    mode: ShelfBidMode
    auto_adv_id: int
    nmid: int
    bid_minor: int
    currency: str
    shelves_on: bool
    expect_patch_call: bool


SHELF_SET_BID_CASES: tuple[ShelfSetBidContractCase, ...] = (
    ShelfSetBidContractCase(
        case_id="shelves_on_may_write",
        mode="shelves_on_may_write",
        auto_adv_id=333,
        nmid=701,
        bid_minor=7000,
        currency="RUB",
        shelves_on=True,
        expect_patch_call=True,
    ),
    ShelfSetBidContractCase(
        case_id="shelves_off_must_not",
        mode="shelves_off_must_not",
        auto_adv_id=333,
        nmid=701,
        bid_minor=7000,
        currency="RUB",
        shelves_on=False,
        expect_patch_call=False,
    ),
)


@dataclass
class RecordingPatchAutoAdvBids:
    """Fake ``wb_modifier.patch_auto_adv_bids_kopecks(auto_adv_id, {nmid: api_bid})``."""

    calls: list[tuple[int, dict[int, int]]] = field(default_factory=list)

    async def patch_auto_adv_bids_kopecks(
        self, auto_adv_id: int, nmid_to_bid: dict[int, int]
    ) -> None:
        """Сигнатура как production WBModifier patch для полок."""
        self.calls.append((int(auto_adv_id), {int(k): int(v) for k, v in nmid_to_bid.items()}))

    def assert_matches_case(self, case: ShelfSetBidContractCase) -> None:
        """Executable parity vs ContractCase."""
        if case.expect_patch_call:
            assert len(self.calls) == 1, f"{case.case_id}: expected patch"
            adv_id, mapping = self.calls[0]
            assert adv_id == case.auto_adv_id
            assert mapping == {case.nmid: case.bid_minor}
        else:
            assert self.calls == [], f"{case.case_id}: forbidden patch {self.calls}"


@dataclass
class RecordingShelfBidSetter:
    """Thin fake ``set_bid(complex_adv, bid_minor, currency)`` для scenario без WB."""

    calls: list[tuple[Any, int, str]] = field(default_factory=list)

    async def set_bid(self, complex_adv: Any, bid_minor: int, currency: str) -> None:
        """Сигнатура как ``AutoShelfBidSetter.set_bid``."""
        self.calls.append((complex_adv, int(bid_minor), str(currency)))

    def assert_matches_case(
        self, case: ShelfSetBidContractCase, *, complex_adv: Any
    ) -> None:
        """Проверка set_bid call shape."""
        matched = [
            c
            for c in self.calls
            if c[0] is complex_adv
            and c[1] == case.bid_minor
            and c[2] == case.currency
        ]
        if case.expect_patch_call:
            assert matched, f"{case.case_id}: expected set_bid"
        else:
            assert not matched, f"{case.case_id}: forbidden set_bid"
