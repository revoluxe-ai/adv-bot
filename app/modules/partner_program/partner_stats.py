"""Partner-program statistics and payout service.

The service keeps only payout facts in the database. Partner earnings are
calculated dynamically from invite usage and real external balance top-ups.
"""

from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass
from decimal import Decimal, InvalidOperation, ROUND_HALF_UP
from typing import TypeAlias

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.common_slaves.wildberries.models.models import (
    WBBalancePayment,
    WBUserCabinet,
)
from app.utils.db.models import Invite, PartnerPayout, User, UserBalancePayment
from app.utils.db.session_maker import get_async_session_maker

MoneyValue: TypeAlias = Decimal | int | float | str

_sm = get_async_session_maker

PARTNER_RATE = Decimal("0.15")
MONEY_QUANT = Decimal("0.01")
_REAL_EXTERNAL_PAYMENT_INCLUDE_MARKERS = ("через telegram",)
_REAL_EXTERNAL_PAYMENT_EXCLUDE_MARKERS = (
    "администратор",
    "пополнение администратором",
    "перевод на кабинет",
    "transfer_to_cabinet",
    "компенсац",
)


@dataclass(frozen=True, slots=True)
class PartnerStats:
    """Computed partner statistics for one partner user."""

    partner_user_id: int
    invite_count: int
    used_invite_count: int
    invited_users_count: int
    paid_users_count: int
    clients_paid_sum: Decimal
    earned_amount: Decimal
    paid_out_amount: Decimal
    available_to_payout: Decimal


@dataclass(frozen=True, slots=True)
class PartnerAdminStatsRow:
    """Partner statistics row for the admin list view."""

    partner_user_id: int
    user_telegram_id: int | None
    username: str | None
    phone: str | None
    invite_count: int
    used_invite_count: int
    invited_users_count: int
    paid_users_count: int
    clients_paid_sum: Decimal
    earned_amount: Decimal
    paid_out_amount: Decimal
    available_to_payout: Decimal


def _to_decimal_money(value: MoneyValue | None) -> Decimal:
    """Convert a persisted money value to Decimal with project-wide rounding."""
    if value is None:
        return Decimal("0.00")
    return Decimal(str(value)).quantize(MONEY_QUANT, rounding=ROUND_HALF_UP)


def _normalize_payment_amount(amount: MoneyValue) -> Decimal:
    """Validate and normalize payout input amount."""
    try:
        normalized = Decimal(str(amount)).quantize(
            MONEY_QUANT,
            rounding=ROUND_HALF_UP,
        )
    except (InvalidOperation, ValueError, TypeError) as exc:
        raise ValueError("Payout amount must be a valid number.") from exc
    if normalized <= 0:
        raise ValueError("Payout amount must be greater than zero.")
    return normalized


def _normalize_description(description: str | None) -> str:
    """Normalize payment description for external-payment heuristics."""
    return (description or "").strip().lower()


def is_real_external_balance_payment(
    payment: UserBalancePayment | WBBalancePayment,
) -> bool:
    """Return whether a balance payment looks like a real external top-up.

    Current schema has no explicit payment source, so the logic is centralized
    here and can later be replaced with a strict source/provider flag.
    Empty or whitespace-only descriptions are not counted as external.
    """
    amount = _to_decimal_money(getattr(payment, "amount", None))
    if amount <= 0:
        return False

    operation_type = getattr(payment, "operation_type", None)
    if operation_type is not None and str(operation_type).strip().lower() != "add":
        return False

    description = _normalize_description(getattr(payment, "description", None))
    if description and any(
        marker in description for marker in _REAL_EXTERNAL_PAYMENT_EXCLUDE_MARKERS
    ):
        return False
    if description:
        return any(
            marker in description for marker in _REAL_EXTERNAL_PAYMENT_INCLUDE_MARKERS
        )
    return False


def _resolve_cabinet_payment_user_id(
    owner_ids: set[int],
) -> int | None:
    """Pick the single invited user who receives credit for a cabinet top-up.

    ``WBBalancePayment`` stores only ``wb_cabinet_id``, not payer ``user_id``.
    When several invited users share one cabinet, the same payment must not
    inflate partner totals — credit exactly one user (lowest internal id).
    """
    if not owner_ids:
        return None
    return min(owner_ids)


def _build_user_payment_totals(
    *,
    invited_user_ids: set[int],
    user_balance_payments: list[UserBalancePayment],
    wb_balance_payments: list[WBBalancePayment],
    wb_user_cabinets: list[WBUserCabinet],
) -> dict[int, Decimal]:
    """Aggregate real external payments per invited user (user-scoped, no double count)."""
    totals: dict[int, Decimal] = {
        user_id: Decimal("0.00") for user_id in invited_user_ids
    }

    for payment in user_balance_payments:
        if payment.user_id not in invited_user_ids:
            continue
        if not is_real_external_balance_payment(payment):
            continue
        totals[payment.user_id] += _to_decimal_money(payment.amount)

    invited_owners_by_cabinet_id: dict[int, set[int]] = defaultdict(set)
    for wb_user_cabinet in wb_user_cabinets:
        if wb_user_cabinet.user_id in invited_user_ids:
            invited_owners_by_cabinet_id[wb_user_cabinet.wb_cabinet_id].add(
                wb_user_cabinet.user_id
            )

    for payment in wb_balance_payments:
        if not is_real_external_balance_payment(payment):
            continue
        owner_ids = invited_owners_by_cabinet_id.get(payment.wb_cabinet_id, set())
        owner_id = _resolve_cabinet_payment_user_id(owner_ids)
        if owner_id is None:
            continue
        totals[owner_id] += _to_decimal_money(payment.amount)

    return {
        user_id: total.quantize(MONEY_QUANT, rounding=ROUND_HALF_UP)
        for user_id, total in totals.items()
    }


def calculate_partner_stats_from_records(
    *,
    partner_user_id: int,
    invites: list[Invite],
    user_balance_payments: list[UserBalancePayment],
    wb_balance_payments: list[WBBalancePayment],
    wb_user_cabinets: list[WBUserCabinet],
    partner_payouts: list[PartnerPayout],
) -> PartnerStats:
    """Calculate partner statistics from preloaded ORM records."""
    partner_invites = [
        invite for invite in invites if invite.issued_to_user_id == partner_user_id
    ]
    used_partner_invites = [
        invite for invite in partner_invites if invite.used_by_user_id is not None
    ]
    invited_user_ids = {
        int(invite.used_by_user_id)
        for invite in used_partner_invites
        if invite.used_by_user_id is not None
    }
    user_payment_totals = _build_user_payment_totals(
        invited_user_ids=invited_user_ids,
        user_balance_payments=user_balance_payments,
        wb_balance_payments=wb_balance_payments,
        wb_user_cabinets=wb_user_cabinets,
    )
    clients_paid_sum = sum(user_payment_totals.values(), Decimal("0.00")).quantize(
        MONEY_QUANT,
        rounding=ROUND_HALF_UP,
    )
    paid_users_count = sum(1 for total in user_payment_totals.values() if total > 0)
    earned_amount = (clients_paid_sum * PARTNER_RATE).quantize(
        MONEY_QUANT,
        rounding=ROUND_HALF_UP,
    )
    paid_out_amount = sum(
        (
            _to_decimal_money(payout.amount)
            for payout in partner_payouts
            if payout.partner_user_id == partner_user_id
        ),
        Decimal("0.00"),
    ).quantize(MONEY_QUANT, rounding=ROUND_HALF_UP)
    available_to_payout = (earned_amount - paid_out_amount).quantize(
        MONEY_QUANT,
        rounding=ROUND_HALF_UP,
    )
    return PartnerStats(
        partner_user_id=partner_user_id,
        invite_count=len(partner_invites),
        used_invite_count=len(used_partner_invites),
        invited_users_count=len(invited_user_ids),
        paid_users_count=paid_users_count,
        clients_paid_sum=clients_paid_sum,
        earned_amount=earned_amount,
        paid_out_amount=paid_out_amount,
        available_to_payout=available_to_payout,
    )


async def _load_partner_stats_records(
    session: AsyncSession,
    partner_user_id: int,
) -> tuple[
    User,
    list[Invite],
    list[UserBalancePayment],
    list[WBBalancePayment],
    list[WBUserCabinet],
    list[PartnerPayout],
]:
    """Load the full record set required for one partner statistics snapshot."""
    partner_user = await session.get(User, partner_user_id)
    if partner_user is None:
        raise RuntimeError(f"Partner user {partner_user_id} was not found.")

    invites = list(
        (
            await session.execute(
                select(Invite).where(Invite.issued_to_user_id == partner_user_id)
            )
        )
        .scalars()
        .all()
    )
    invited_user_ids = sorted(
        {
            int(invite.used_by_user_id)
            for invite in invites
            if invite.used_by_user_id is not None
        }
    )

    user_balance_payments: list[UserBalancePayment] = []
    wb_user_cabinets: list[WBUserCabinet] = []
    wb_balance_payments: list[WBBalancePayment] = []
    if invited_user_ids:
        user_balance_payments = list(
            (
                await session.execute(
                    select(UserBalancePayment).where(
                        UserBalancePayment.user_id.in_(invited_user_ids)
                    )
                )
            )
            .scalars()
            .all()
        )
        wb_user_cabinets = list(
            (
                await session.execute(
                    select(WBUserCabinet).where(WBUserCabinet.user_id.in_(invited_user_ids))
                )
            )
            .scalars()
            .all()
        )
        cabinet_ids = sorted(
            {wb_user_cabinet.wb_cabinet_id for wb_user_cabinet in wb_user_cabinets}
        )
        if cabinet_ids:
            wb_balance_payments = list(
                (
                    await session.execute(
                        select(WBBalancePayment).where(
                            WBBalancePayment.wb_cabinet_id.in_(cabinet_ids)
                        )
                    )
                )
                .scalars()
                .all()
            )

    partner_payouts = list(
        (
            await session.execute(
                select(PartnerPayout).where(
                    PartnerPayout.partner_user_id == partner_user_id
                )
            )
        )
        .scalars()
        .all()
    )
    return (
        partner_user,
        invites,
        user_balance_payments,
        wb_balance_payments,
        wb_user_cabinets,
        partner_payouts,
    )


async def _get_partner_stats_in_session(
    session: AsyncSession,
    partner_user_id: int,
) -> PartnerStats:
    """Calculate one partner statistics snapshot within an existing session."""
    (
        _partner_user,
        invites,
        user_balance_payments,
        wb_balance_payments,
        wb_user_cabinets,
        partner_payouts,
    ) = await _load_partner_stats_records(session, partner_user_id)
    return calculate_partner_stats_from_records(
        partner_user_id=partner_user_id,
        invites=invites,
        user_balance_payments=user_balance_payments,
        wb_balance_payments=wb_balance_payments,
        wb_user_cabinets=wb_user_cabinets,
        partner_payouts=partner_payouts,
    )


async def get_partner_stats(partner_user_id: int) -> PartnerStats:
    """Calculate statistics for a single partner user.

    Parent PURE_READ seam: ``sm(read_only=True)`` →
    :func:`_get_partner_stats_in_session`.
    """
    async with _sm(read_only=True) as session:
        return await _get_partner_stats_in_session(session, partner_user_id)


async def list_partner_stats_in_session(
    session: AsyncSession,
) -> list[PartnerAdminStatsRow]:
    """Calculate partner admin rows within an existing PURE_READ session.

    Caller opens ``sm(read_only=True)`` and passes the session here.
    """
    invite_partner_ids = list(
        (
            await session.execute(
                select(Invite.issued_to_user_id).where(
                    Invite.issued_to_user_id.is_not(None)
                )
            )
        )
        .scalars()
        .all()
    )
    payout_partner_ids = list(
        (await session.execute(select(PartnerPayout.partner_user_id))).scalars().all()
    )
    partner_ids = sorted(
        {
            int(partner_id)
            for partner_id in invite_partner_ids + payout_partner_ids
            if partner_id is not None
        }
    )
    if not partner_ids:
        return []

    users = {
        user.id: user
        for user in (
            await session.execute(select(User).where(User.id.in_(partner_ids)))
        )
        .scalars()
        .all()
    }

    invites = list(
        (
            await session.execute(
                select(Invite).where(Invite.issued_to_user_id.in_(partner_ids))
            )
        )
        .scalars()
        .all()
    )
    invited_user_ids = sorted(
        {
            int(invite.used_by_user_id)
            for invite in invites
            if invite.used_by_user_id is not None
        }
    )
    user_balance_payments: list[UserBalancePayment] = []
    wb_user_cabinets: list[WBUserCabinet] = []
    wb_balance_payments: list[WBBalancePayment] = []
    if invited_user_ids:
        user_balance_payments = list(
            (
                await session.execute(
                    select(UserBalancePayment).where(
                        UserBalancePayment.user_id.in_(invited_user_ids)
                    )
                )
            )
            .scalars()
            .all()
        )
        wb_user_cabinets = list(
            (
                await session.execute(
                    select(WBUserCabinet).where(
                        WBUserCabinet.user_id.in_(invited_user_ids)
                    )
                )
            )
            .scalars()
            .all()
        )
        cabinet_ids = sorted(
            {wb_user_cabinet.wb_cabinet_id for wb_user_cabinet in wb_user_cabinets}
        )
        if cabinet_ids:
            wb_balance_payments = list(
                (
                    await session.execute(
                        select(WBBalancePayment).where(
                            WBBalancePayment.wb_cabinet_id.in_(cabinet_ids)
                        )
                    )
                )
                .scalars()
                .all()
            )
    partner_payouts = list(
        (
            await session.execute(
                select(PartnerPayout).where(
                    PartnerPayout.partner_user_id.in_(partner_ids)
                )
            )
        )
        .scalars()
        .all()
    )

    rows: list[PartnerAdminStatsRow] = []
    for partner_id in partner_ids:
        user = users.get(partner_id)
        if user is None:
            raise RuntimeError(f"Partner user {partner_id} was not found.")
        stats = calculate_partner_stats_from_records(
            partner_user_id=partner_id,
            invites=invites,
            user_balance_payments=user_balance_payments,
            wb_balance_payments=wb_balance_payments,
            wb_user_cabinets=wb_user_cabinets,
            partner_payouts=partner_payouts,
        )
        rows.append(
            PartnerAdminStatsRow(
                partner_user_id=partner_id,
                user_telegram_id=user.user_telegram_id,
                username=user.username,
                phone=user.phone,
                invite_count=stats.invite_count,
                used_invite_count=stats.used_invite_count,
                invited_users_count=stats.invited_users_count,
                paid_users_count=stats.paid_users_count,
                clients_paid_sum=stats.clients_paid_sum,
                earned_amount=stats.earned_amount,
                paid_out_amount=stats.paid_out_amount,
                available_to_payout=stats.available_to_payout,
            )
        )
    return rows


async def list_partner_stats() -> list[PartnerAdminStatsRow]:
    """Calculate partner statistics rows for the admin list.

    Parent PURE_READ seam: ``sm(read_only=True)`` →
    :func:`list_partner_stats_in_session`.
    """
    async with _sm(read_only=True) as session:
        return await list_partner_stats_in_session(session)


async def create_partner_payout_in_session(
    session: AsyncSession,
    *,
    partner_user_id: int,
    admin_user_id: int,
    amount: MoneyValue,
    comment: str | None = None,
) -> PartnerPayout:
    """Create a partner payout within an existing WRITE session.

    Caller opens ``sm(read_only=False)`` and passes the session here.
    Persists via flush on the injected session; caller owns commit.
    """
    normalized_amount = _normalize_payment_amount(amount)
    partner_user = await session.get(User, partner_user_id)
    if partner_user is None:
        raise RuntimeError(f"Partner user {partner_user_id} was not found.")
    admin_user = await session.get(User, admin_user_id)
    if admin_user is None:
        raise RuntimeError(f"Admin user {admin_user_id} was not found.")

    stats = await _get_partner_stats_in_session(session, partner_user_id)
    if normalized_amount > stats.available_to_payout:
        raise ValueError(
            "Payout amount exceeds the available partner payout balance."
        )

    payout = PartnerPayout(
        partner_user_id=partner_user_id,
        amount=float(normalized_amount),
        created_by_admin_user_id=admin_user_id,
        comment=comment,
    )
    session.add(payout)
    await session.flush()
    return payout


async def create_partner_payout(
    *,
    partner_user_id: int,
    admin_user_id: int,
    amount: MoneyValue,
    comment: str | None = None,
) -> PartnerPayout:
    """Create a partner payout after validating the available amount.

    Parent WRITE seam: ``sm(read_only=False)`` →
    :func:`create_partner_payout_in_session`.
    """
    async with _sm(read_only=False) as session:
        payout = await create_partner_payout_in_session(
            session,
            partner_user_id=partner_user_id,
            admin_user_id=admin_user_id,
            amount=amount,
            comment=comment,
        )
        await session.commit()
        return payout
