"""ContractCase + recording fake для WB Search pause/start (empty-keywords).

Spec ``pause-on-empty-keywords`` / INC-PAUSE-02.
Зачем: общий executable source для scenario_seam stubs и boundary_adapter
parity (``pause_auction_campaign`` / ``start_auction_campaign`` → AdvType.SEARCH).
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Literal

from app.shared.domains.wb.enums import AdvType

WbSearchLifecycleMethod = Literal[
    "pause_auction_campaign",
    "start_auction_campaign",
    "pause_auto_campaign",
    "start_auto_campaign",
]

CONTRACT_ID = "empty-keywords-wb-search-lifecycle-v1"


@dataclass(frozen=True)
class WbSearchLifecycleContractCase:
    """Ожидаемый thin-end вызов WB lifecycle для empty-keywords path."""

    case_id: str
    method: WbSearchLifecycleMethod
    """Имя метода на WBModifier / recording fake."""

    routes_adv_type: AdvType | None
    """Для auction methods — SEARCH; для Auto — AUTO; None если non-call assert."""

    allowed_for_empty_keywords: bool
    """False для pause_auto_campaign (FORBIDDEN adapter)."""


# Shared cases: scenario fake assertions + WBModifier boundary_adapter.
WB_SEARCH_LIFECYCLE_CASES: tuple[WbSearchLifecycleContractCase, ...] = (
    WbSearchLifecycleContractCase(
        case_id="pause_search_allowed",
        method="pause_auction_campaign",
        routes_adv_type=AdvType.SEARCH,
        allowed_for_empty_keywords=True,
    ),
    WbSearchLifecycleContractCase(
        case_id="start_search_recheck",
        method="start_auction_campaign",
        routes_adv_type=AdvType.SEARCH,
        allowed_for_empty_keywords=True,
    ),
    WbSearchLifecycleContractCase(
        case_id="pause_auto_forbidden",
        method="pause_auto_campaign",
        routes_adv_type=AdvType.AUTO,
        allowed_for_empty_keywords=False,
    ),
)


@dataclass
class RecordingWbLifecycleModifier:
    """Thin-end fake после causal boundary activity-control.

    Записывает (method, complex_adv). Сигнатуры совпадают с WBModifier:
    один позиционный ``complex_adv``, return None (awaitable).
    """

    calls: list[tuple[str, Any]] = field(default_factory=list)

    async def pause_auction_campaign(self, complex_adv: Any) -> None:
        """Как WBModifier.pause_auction_campaign(complex_adv)."""
        self.calls.append(("pause_auction_campaign", complex_adv))

    async def start_auction_campaign(self, complex_adv: Any) -> None:
        """Как WBModifier.start_auction_campaign(complex_adv)."""
        self.calls.append(("start_auction_campaign", complex_adv))

    async def pause_auto_campaign(self, complex_adv: Any) -> None:
        """Как WBModifier.pause_auto_campaign — Forbidden для EMPTY_KEYWORDS."""
        self.calls.append(("pause_auto_campaign", complex_adv))

    async def start_auto_campaign(self, complex_adv: Any) -> None:
        """Как WBModifier.start_auto_campaign (ортогонален empty-keywords Search)."""
        self.calls.append(("start_auto_campaign", complex_adv))

    def methods_called(self) -> list[str]:
        """Список имён методов в порядке вызовов."""
        return [name for name, _ in self.calls]

    def assert_matches_case(
        self,
        case: WbSearchLifecycleContractCase,
        *,
        complex_adv: Any,
        must_have_been_called: bool,
    ) -> None:
        """Проверка parity: call shape = (method, same complex_adv instance)."""
        matched = [
            adv for name, adv in self.calls if name == case.method and adv is complex_adv
        ]
        if must_have_been_called:
            assert matched, (
                f"ContractCase {case.case_id}: expected {case.method}({complex_adv!r})"
            )
        else:
            assert not matched, (
                f"ContractCase {case.case_id}: forbidden {case.method} was called"
            )
