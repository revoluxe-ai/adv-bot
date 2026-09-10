"""Учёт common-pool и per-campaign promo remaining.

Common pool — live ``cashbacks[]``. Campaign remaining — FEFO по verified
allocation ``WBAutoBudgetTopUp`` минус ``WBCampaignPromoSpend``.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from decimal import Decimal
from collections.abc import Sequence
from typing import Any

from app.shared.domains.wb.exceptions import NotEnoughBalanceOnShopError
from app.shared.domains.wb.utils.balance_source import (
    CashbackTopup,
    select_topup_balance_decision,
)
from app.shared.domains.wb.utils.promo_plan_multiplier import promo_fraction_from_amounts

_ZERO = Decimal("0")

# WB OpenAPI v1: Keshbek; v4/v5: Кэшбэк. Оба — spend history, не pool.
# Не принимать произвольный английский ``cashback``: paymentType должен
# соответствовать documented WB values, иначе обычный spend может попасть в
# promo ledger.
_PROMO_PAYMENT_TYPES = frozenset(
    {
        "keshbek",
        "кэшбэк",
    }
)


def is_promo_payment_type(value: object) -> bool:
    """True, если UPD paymentType соответствует documented кэшбэк-списанию."""
    if value is None:
        return False
    text = str(value).strip().lower()
    if not text:
        return False
    return text in _PROMO_PAYMENT_TYPES


def parse_expiration(value: str | datetime | None) -> datetime | None:
    """Разобрать ISO expiry в aware UTC datetime."""
    if value is None:
        return None
    if isinstance(value, datetime):
        if value.tzinfo is None:
            return value.replace(tzinfo=timezone.utc)
        return value.astimezone(timezone.utc)
    text = str(value).strip()
    if not text:
        return None
    try:
        parsed = datetime.fromisoformat(text.replace("Z", "+00:00"))
    except ValueError:
        return None
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    return parsed.astimezone(timezone.utc)


def is_expired(expires_at: datetime | None, *, now: datetime) -> bool:
    """Expired только при известном expires_at <= now. Undated не истекает."""
    if expires_at is None:
        return False
    aware_now = now if now.tzinfo else now.replace(tzinfo=timezone.utc)
    aware_exp = expires_at if expires_at.tzinfo else expires_at.replace(tzinfo=timezone.utc)
    return aware_exp <= aware_now.astimezone(aware_exp.tzinfo)


@dataclass(frozen=True, slots=True)
class PromoAllocationTranche:
    """Verified promo credit на кампании."""

    topup_id: int
    advert_id: int
    promo_amount: int
    amount: int
    expires_at: datetime | None
    created_at: datetime
    budget_after: float | None = None


@dataclass(frozen=True, slots=True)
class PromoSpendRow:
    """Persisted UPD cashback spend."""

    fingerprint: str
    advert_id: int
    upd_sum: int
    upd_time: datetime | None


@dataclass(frozen=True, slots=True)
class CampaignPromoLedger:
    """Per-campaign allocated/spent/remaining."""

    advert_id: int
    allocated: int
    spent: int
    remaining: int
    expires_at: datetime | None
    reference_budget: int | None
    fraction: Decimal
    usable: bool


@dataclass(frozen=True, slots=True)
class PromoAvailability:
    """OR-active / AND-stop состояние для одной кампании."""

    pool_usable: bool
    pool_amount: int
    pool_fraction: Decimal
    campaign_usable: bool
    campaign_remaining: int
    campaign_fraction: Decimal
    campaign_expires_at: datetime | None
    fraction: Decimal
    usable: bool

    @property
    def stop_on_exhaustion(self) -> bool:
        """True только когда оба источника нулевые."""
        return not self.pool_usable and not self.campaign_usable


def _tranche_sort_key(tranche: PromoAllocationTranche) -> tuple[int, datetime, int]:
    exp = tranche.expires_at
    undated = 1 if exp is None else 0
    exp_key = exp if exp is not None else datetime.max.replace(tzinfo=timezone.utc)
    return (undated, exp_key, tranche.topup_id)


@dataclass
class _LeftoverRow:
    """Mutable FEFO leftover для apply_spend_fefo."""

    leftover: int
    expires_at: datetime | None
    budget_after: float | None
    amount: int
    package_promo: int


def _live_package_fraction(
    leftovers: Sequence[_LeftoverRow],
    *,
    now: datetime,
) -> Decimal:
    """Max package percent среди live leftover с положительным остатком."""
    package_fraction = _ZERO
    for row in leftovers:
        if row.leftover <= 0:
            continue
        if is_expired(row.expires_at, now=now):
            continue
        if row.amount <= 0:
            continue
        tranche_fraction = promo_fraction_from_amounts(
            promo_amount=row.package_promo,
            total_amount=row.amount,
        )
        if tranche_fraction > package_fraction:
            package_fraction = tranche_fraction
    return package_fraction


def _apply_spend_fefo_state(
    tranches: Sequence[PromoAllocationTranche],
    spend_rows: Sequence[PromoSpendRow],
    *,
    now: datetime,
) -> tuple[
    list[_LeftoverRow],
    int,
    int,
    int,
    datetime | None,
    int | None,
    Decimal,
]:
    """FEFO leftover state plus allocated/spent/remaining aggregates."""
    leftovers: list[_LeftoverRow] = []
    allocated = 0
    for tranche in sorted(tranches, key=_tranche_sort_key):
        if tranche.promo_amount <= 0:
            continue
        allocated += tranche.promo_amount
        leftovers.append(
            _LeftoverRow(
                leftover=tranche.promo_amount,
                expires_at=tranche.expires_at,
                budget_after=tranche.budget_after,
                amount=tranche.amount,
                package_promo=tranche.promo_amount,
            )
        )

    total_spend = sum(max(0, row.upd_sum) for row in spend_rows)
    remaining_spend = total_spend
    for item in leftovers:
        if is_expired(item.expires_at, now=now):
            continue
        take = min(item.leftover, remaining_spend)
        item.leftover -= take
        remaining_spend -= take
        if remaining_spend <= 0:
            break

    usable_remaining = 0
    nearest_exp: datetime | None = None
    reference_budget: int | None = None
    for row in leftovers:
        if row.leftover <= 0:
            continue
        if is_expired(row.expires_at, now=now):
            continue
        usable_remaining += row.leftover
        if row.expires_at is not None and (
            nearest_exp is None or row.expires_at < nearest_exp
        ):
            nearest_exp = row.expires_at
        if row.amount > 0:
            reference_budget = row.amount

    applied_spend = min(total_spend, allocated)
    package_fraction = _live_package_fraction(leftovers, now=now)
    return (
        leftovers,
        allocated,
        applied_spend,
        usable_remaining,
        nearest_exp,
        reference_budget,
        package_fraction,
    )


def apply_spend_fefo(
    tranches: Sequence[PromoAllocationTranche],
    spend_rows: Sequence[PromoSpendRow],
    *,
    now: datetime,
) -> tuple[int, int, int, datetime | None, int | None]:
    """Вернуть allocated, spent, remaining, nearest remaining expiry, top-up unit.

    Spend применяется FEFO только к non-expired leftover: expired leftover
    пропускается в цикле списания и не поглощает spend. Порядок FEFO среди
    live leftover сохраняется. Expired leftover не usable, даже если
    локальная сумма ещё положительна. ``reference_budget`` — top-up unit
    (``tranche.amount``) последнего live leftover, не ``budget_after``.

    Args:
        tranches: verified promo credits кампании.
        spend_rows: persisted UPD cashback spend.
        now: момент оценки expiry (aware UTC предпочтителен).

    Returns:
        Кортеж (allocated, applied_spend, usable_remaining,
        nearest_remaining_expiry, reference_budget).
    """
    (
        _leftovers,
        allocated,
        applied_spend,
        usable_remaining,
        nearest_exp,
        reference_budget,
        _package_fraction,
    ) = _apply_spend_fefo_state(tranches, spend_rows, now=now)
    return allocated, applied_spend, usable_remaining, nearest_exp, reference_budget


def campaign_ledger_from_rows(
    advert_id: int,
    tranches: Sequence[PromoAllocationTranche],
    spend_rows: Sequence[PromoSpendRow],
    *,
    now: datetime,
    campaign_budget_total: int | None = None,
) -> CampaignPromoLedger:
    """Собрать ledger одной кампании.

    Overlay fraction ``f`` берётся из package percent live leftover
    (``tranche.promo_amount / tranche.amount``), не из
    ``remaining / last_tranche.amount``. ``reference_budget`` — top-up unit
    последнего live leftover для диагностики; в mix не участвует.
    ``campaign_budget_total`` в сигнатуре для ``load_campaign_ledgers`` и
    в mix не участвует.

    Args:
        advert_id: идентификатор кампании.
        tranches: verified promo credits.
        spend_rows: persisted UPD cashback spend.
        now: момент оценки expiry.
        campaign_budget_total: потолок/кошелёк кампании; не знаменатель mix.

    Returns:
        ``CampaignPromoLedger`` с ``fraction = package percent``.
    """
    del campaign_budget_total
    (
        _leftovers,
        allocated,
        spent,
        remaining,
        expires_at,
        reference,
        fraction,
    ) = _apply_spend_fefo_state(tranches, spend_rows, now=now)
    if remaining <= 0:
        fraction = _ZERO
    usable = remaining > 0
    return CampaignPromoLedger(
        advert_id=advert_id,
        allocated=allocated,
        spent=spent,
        remaining=remaining,
        expires_at=expires_at,
        reference_budget=reference,
        fraction=fraction,
        usable=usable,
    )


def pool_usable_from_pick(
    cashback: CashbackTopup | None,
    *,
    topup_amount: int,
    now: datetime,
) -> tuple[bool, int, Decimal]:
    """Рассчитать долю следующего top-up из уже согласованного live-пакета.

    Args:
        cashback: Пакет, который уже прошёл top-up pairing.
        topup_amount: Полная сумма следующего пополнения.
        now: Момент проверки срока действия пакета.

    Returns:
        Кортеж ``(usable, cashback_amount, fraction)``.
    """
    if cashback is None or cashback.cashback_sum <= 0 or topup_amount <= 0:
        return False, 0, _ZERO
    if is_expired(parse_expiration(cashback.expiration_date), now=now):
        return False, 0, _ZERO
    fraction = promo_fraction_from_amounts(
        promo_amount=cashback.cashback_sum,
        total_amount=topup_amount,
    )
    return True, int(cashback.cashback_sum), fraction


def resolve_promo_availability(
    *,
    pool_response: Any | None,
    topup_amount: int,
    campaign_ledger: CampaignPromoLedger | None,
    now: datetime,
) -> PromoAvailability:
    """Определить OR-active pool/campaign с общей проверкой top-up pairing.

    Pool считается usable только если общий selector top-up сохранил
    cashback-пакет после проверки ordinary source на ``topup_amount -
    cashback_sum``. Если обычного источника недостаточно и selector не может
    выбрать обычный top-up, pool остаётся unusable; campaign leftover при этом
    продолжает участвовать в OR-логике.

    Args:
        pool_response: Ответ WB с балансами и live cashback-пакетами.
        topup_amount: Полная сумма следующего пополнения.
        campaign_ledger: Verified leftover конкретной кампании.
        now: Момент проверки сроков действия.

    Returns:
        Согласованное состояние pool/campaign и итоговой promo-доли.
    """
    cashback = None
    if pool_response is not None and topup_amount > 0:
        try:
            balance_decision = select_topup_balance_decision(
                pool_response,
                topup_amount=topup_amount,
                now=now,
            )
        except NotEnoughBalanceOnShopError:
            balance_decision = None
        if balance_decision is not None:
            cashback = balance_decision.cashback
    pool_usable, pool_amount, pool_fraction = pool_usable_from_pick(
        cashback, topup_amount=topup_amount, now=now
    )
    campaign_usable = bool(campaign_ledger and campaign_ledger.usable)
    campaign_remaining = campaign_ledger.remaining if campaign_ledger else 0
    campaign_fraction = campaign_ledger.fraction if campaign_ledger else _ZERO
    campaign_expires_at = campaign_ledger.expires_at if campaign_ledger else None
    fraction = pool_fraction
    if campaign_fraction > fraction:
        fraction = campaign_fraction
    usable = pool_usable or campaign_usable
    if not usable:
        fraction = _ZERO
    return PromoAvailability(
        pool_usable=pool_usable,
        pool_amount=pool_amount,
        pool_fraction=pool_fraction,
        campaign_usable=campaign_usable,
        campaign_remaining=campaign_remaining,
        campaign_fraction=campaign_fraction,
        campaign_expires_at=campaign_expires_at,
        fraction=fraction,
        usable=usable,
    )


def spend_fingerprint(
    *,
    advert_id: int,
    upd_num: int | None,
    upd_time: str | None,
    upd_sum: int,
    payment_type: str,
    duplicate_index: int | None = None,
) -> str:
    """Стабильный ключ строки UPD с fallback для отсутствующего ``upd_num``.

    Основной legacy-формат сохраняется для совместимости с уже записанными
    PG-строками. Если WB не прислал ``updNum`` и в одном ответе есть несколько
    полностью одинаковых строк, ``duplicate_index`` различает их начиная со
    второй строки; индекс ``0`` намеренно оставляет старый fingerprint.

    Это не создаёт ложной уникальности между двумя API-строками, для которых
    WB не передал ни ``updNum``, ни иного идентификатора: в таком случае
    различить их по содержимому невозможно. Но одинаковые строки в одном
    batch больше не схлопываются в одну PG-запись.
    """
    fingerprint = "|".join(
        (
            str(advert_id),
            str(upd_num if upd_num is not None else ""),
            str(upd_time or ""),
            str(upd_sum),
            str(payment_type),
        )
    )
    if upd_num is None and duplicate_index is not None and duplicate_index > 0:
        return f"{fingerprint}|duplicate:{duplicate_index}"
    return fingerprint
