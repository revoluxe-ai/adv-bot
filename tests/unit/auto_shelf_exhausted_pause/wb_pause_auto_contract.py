"""ContractCase + recording fake for WB Auto pause (ASEP S03/S04).

Spec: ``auto-shelf-exhausted-pause`` — Exhausted → pause_auto_campaign;
FORBIDDEN pause_auction_campaign (Search sibling).

Shared executable source for scenario_seam stubs and stub_contract / boundary
parity vs ``WBModifier.pause_auto_campaign``.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Literal

from app.shared.domains.wb.enums import AdvType

WbAutoLifecycleMethod = Literal[
    "pause_auto_campaign",
    "start_auto_campaign",
    "pause_auction_campaign",
    "start_auction_campaign",
]

CONTRACT_ID = "asep.wb.pause_auto_lifecycle.v1"


@dataclass(frozen=True)
class WbPauseAutoContractCase:
    """Ожидаемый thin-end вызов WB lifecycle для shelf-exhausted Auto pause."""

    case_id: str
    method: WbAutoLifecycleMethod
    routes_adv_type: AdvType | None
    """Для pause_auto — AUTO; для forbidden auction — SEARCH."""

    allowed_for_shelf_exhausted: bool
    """False для pause_auction_campaign (FORBIDDEN adapter)."""

    expect_called: bool
    """True если scenario_seam MUST вызвать method; False — must not."""


WB_PAUSE_AUTO_CASES: tuple[WbPauseAutoContractCase, ...] = (
    WbPauseAutoContractCase(
        case_id="pause_auto_allowed",
        method="pause_auto_campaign",
        routes_adv_type=AdvType.AUTO,
        allowed_for_shelf_exhausted=True,
        expect_called=True,
    ),
    WbPauseAutoContractCase(
        case_id="pause_auction_forbidden",
        method="pause_auction_campaign",
        routes_adv_type=AdvType.SEARCH,
        allowed_for_shelf_exhausted=False,
        expect_called=False,
    ),
    WbPauseAutoContractCase(
        case_id="start_auto_not_on_enter",
        method="start_auto_campaign",
        routes_adv_type=AdvType.AUTO,
        allowed_for_shelf_exhausted=True,
        expect_called=False,
    ),
    WbPauseAutoContractCase(
        case_id="start_auto_forbidden_other_blocker",
        method="start_auto_campaign",
        routes_adv_type=AdvType.AUTO,
        allowed_for_shelf_exhausted=True,
        expect_called=False,
    ),
    WbPauseAutoContractCase(
        case_id="start_auto_after_clear_only_our_block",
        method="start_auto_campaign",
        routes_adv_type=AdvType.AUTO,
        allowed_for_shelf_exhausted=True,
        expect_called=True,
    ),
)


@dataclass
class RecordingWbAutoLifecycle:
    """Thin-end fake после causal boundary activity-control.

    Сигнатуры совпадают с WBModifier: один позиционный ``complex_adv``.
    """

    calls: list[tuple[str, Any]] = field(default_factory=list)

    async def pause_auto_campaign(self, complex_adv: Any) -> None:
        """Как WBModifier.pause_auto_campaign(complex_adv)."""
        self.calls.append(("pause_auto_campaign", complex_adv))

    async def start_auto_campaign(self, complex_adv: Any) -> None:
        """Как WBModifier.start_auto_campaign(complex_adv)."""
        self.calls.append(("start_auto_campaign", complex_adv))

    async def pause_auction_campaign(self, complex_adv: Any) -> None:
        """FORBIDDEN sibling для ASEP Auto pause."""
        self.calls.append(("pause_auction_campaign", complex_adv))

    async def start_auction_campaign(self, complex_adv: Any) -> None:
        """Ортогональный Search start — не вызывается на enter pause."""
        self.calls.append(("start_auction_campaign", complex_adv))

    def methods_called(self) -> list[str]:
        """Имена методов в порядке вызовов."""
        return [name for name, _ in self.calls]

    def assert_matches_case(
        self,
        case: WbPauseAutoContractCase,
        *,
        complex_adv: Any | None = None,
    ) -> None:
        """Проверка parity: expect_called ↔ (method, optional same complex_adv)."""
        matched = [
            (name, adv)
            for name, adv in self.calls
            if name == case.method
            and (complex_adv is None or adv is complex_adv)
        ]
        if case.expect_called:
            assert matched, (
                f"{case.case_id}: expected {case.method} call; got {self.calls!r}"
            )
        else:
            assert not matched, (
                f"{case.case_id}: FORBIDDEN {case.method}; got {self.calls!r}"
            )
