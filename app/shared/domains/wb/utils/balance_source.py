from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Protocol, runtime_checkable

from app.core.wb_api.data_classes.advs.other_classes import Balances
from app.shared.domains.wb.exceptions import NotEnoughBalanceOnShopError


@dataclass
class BalanceSnapshot:
    balance: int
    net: int
    bonus: int

    @classmethod
    def from_balances(cls, balances: Balances) -> "BalanceSnapshot":
        return cls(
            balance=getattr(balances, "balance", 0) or 0,
            net=getattr(balances, "net", 0) or 0,
            bonus=getattr(balances, "bonus", 0) or 0,
        )

    def rows(self) -> list[tuple[int, str]]:
        return [
            (self.balance, "balance"),
            (self.net, "net"),
            (self.bonus, "bonus"),
        ]


@runtime_checkable
class BalanceResponse(Protocol):
    balance: Any
    net: Any
    bonus: Any


def select_balance_source(
    snapshot: BalanceSnapshot, *, min_required: int = 1000
) -> tuple[int, str]:
    balance_rows = [row for row in snapshot.rows() if row[0] >= min_required]
    if not balance_rows:
        raise NotEnoughBalanceOnShopError()

    _, name = min(balance_rows)

    if name == "balance":
        return 0, name
    if name == "net":
        return 1, name
    if name == "bonus":
        return 3, name

    raise NotEnoughBalanceOnShopError()


def balance_snapshot_from_response(response: BalanceResponse) -> BalanceSnapshot:
    return BalanceSnapshot(
        balance=getattr(response, "balance", 0) or 0,
        net=getattr(response, "net", 0) or 0,
        bonus=getattr(response, "bonus", 0) or 0,
    )


def select_balance_source_from_response(
    response: BalanceResponse,
    *,
    min_required: int = 1000,
) -> tuple[int, str]:
    snapshot = balance_snapshot_from_response(response)
    return select_balance_source(snapshot, min_required=min_required)
