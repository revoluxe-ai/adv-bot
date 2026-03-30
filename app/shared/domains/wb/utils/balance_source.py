from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
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


@dataclass
class CashbackTopup:
    cashback_sum: int
    cashback_percent: int
    expiration_date: str | None


@dataclass
class CashbackSummary:
    total: int
    earliest_expiration_date: str | None
    best_percent: int | None


@dataclass
class TopUpBalanceDecision:
    balance_type: int
    balance_name: str
    cashback: CashbackTopup | None = None


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


def _select_non_bonus_source(
    snapshot: BalanceSnapshot, *, min_required: int
) -> tuple[int, str] | None:
    rows = [
        (snapshot.balance, "balance"),
        (snapshot.net, "net"),
    ]
    candidates = [row for row in rows if row[0] >= min_required]
    if not candidates:
        return None
    _, name = min(candidates)
    if name == "balance":
        return 0, name
    return 1, name


def _parse_iso_dt(value: str | None) -> datetime | None:
    if not value:
        return None
    try:
        return datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return None


def _iter_cashback_rows(response: BalanceResponse) -> list[tuple[int, int, str | None]]:
    raw_cashbacks = getattr(response, "cashbacks", None)
    if raw_cashbacks is None:
        return []
    if not isinstance(raw_cashbacks, list):
        return []
    rows: list[tuple[int, int, str | None]] = []
    for item in raw_cashbacks:
        if isinstance(item, dict):
            sum_raw = item.get("sum", 0)
            percent_raw = item.get("percent", 0)
            exp_raw = item.get("expiration_date")
        else:
            sum_raw = getattr(item, "sum_", 0)
            percent_raw = getattr(item, "percent", 0)
            exp_raw = getattr(item, "expiration_date", None)
        try:
            sum_int = int(sum_raw)
            percent_int = int(percent_raw)
        except (TypeError, ValueError):
            continue
        if sum_int <= 0 or percent_int <= 0:
            continue
        exp = str(exp_raw) if exp_raw else None
        rows.append((sum_int, percent_int, exp))
    return rows


def cashback_summary_from_response(response: BalanceResponse) -> CashbackSummary:
    rows = _iter_cashback_rows(response)
    if not rows:
        return CashbackSummary(total=0, earliest_expiration_date=None, best_percent=None)
    total = sum(row[0] for row in rows)
    best_percent = max(row[1] for row in rows)
    earliest: str | None = None
    dated_rows = [row for row in rows if _parse_iso_dt(row[2]) is not None]
    if dated_rows:
        earliest = min(dated_rows, key=lambda row: _parse_iso_dt(row[2]))[2]
    return CashbackSummary(
        total=total,
        earliest_expiration_date=earliest,
        best_percent=best_percent,
    )


def pick_cashback_for_topup(
    response: BalanceResponse, *, topup_amount: int
) -> CashbackTopup | None:
    if topup_amount <= 0:
        return None
    rows = _iter_cashback_rows(response)
    if not rows:
        return None
    # First spend expiring cashback; undated rows are treated as the least urgent.
    rows_sorted = sorted(
        rows,
        key=lambda row: (_parse_iso_dt(row[2]) is None, _parse_iso_dt(row[2]) or datetime.max.replace(tzinfo=timezone.utc)),
    )
    for cashback_sum, cashback_percent, expiration_date in rows_sorted:
        max_by_percent = int(topup_amount * cashback_percent / 100)
        payable = min(max_by_percent, cashback_sum)
        if payable > 0:
            return CashbackTopup(
                cashback_sum=payable,
                cashback_percent=cashback_percent,
                expiration_date=expiration_date,
            )
    return None


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


def select_topup_balance_decision(
    response: BalanceResponse,
    *,
    topup_amount: int,
    min_required: int = 1000,
) -> TopUpBalanceDecision:
    cashback = pick_cashback_for_topup(response, topup_amount=topup_amount)
    snapshot = balance_snapshot_from_response(response)
    if cashback:
        non_bonus = _select_non_bonus_source(snapshot, min_required=min_required)
        if non_bonus is not None:
            balance_type, balance_name = non_bonus
            return TopUpBalanceDecision(
                balance_type=balance_type,
                balance_name=balance_name,
                cashback=cashback,
            )
    balance_type, balance_name = select_balance_source(
        snapshot, min_required=min_required
    )
    return TopUpBalanceDecision(
        balance_type=balance_type,
        balance_name=balance_name,
        cashback=None,
    )
