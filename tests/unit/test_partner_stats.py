"""Unit tests for partner-program statistics and payout service."""

from __future__ import annotations

from contextlib import asynccontextmanager
from datetime import UTC, datetime, timedelta
from decimal import Decimal
from unittest.mock import AsyncMock

import pytest

from app.modules.common_slaves.wildberries.models.models import (
    WBBalancePayment,
    WBUserCabinet,
)
from app.modules.partner_program.partner_stats import (
    PartnerStats,
    _resolve_cabinet_payment_user_id,
    calculate_partner_stats_from_records,
    create_partner_payout,
    is_real_external_balance_payment,
)
from app.utils.db.models import Invite, InviteStatus, PartnerPayout, User, UserBalancePayment


def _now() -> datetime:
    """Return a naive UTC timestamp matching current invite handlers."""
    return datetime.now(UTC).replace(tzinfo=None)


def _invite(
    *,
    code: str,
    issued_to_user_id: int,
    used_by_user_id: int | None = None,
) -> Invite:
    """Create an invite test fixture object."""
    now = _now()
    return Invite(
        code=code,
        issued_to_user_id=issued_to_user_id,
        issued_at=now,
        expires_at=now + timedelta(days=1),
        status=InviteStatus.USED if used_by_user_id is not None else InviteStatus.ACTIVE,
        used_by_user_id=used_by_user_id,
        used_at=now if used_by_user_id is not None else None,
    )


def _user_balance_payment(
    *,
    user_id: int,
    amount: float,
    operation_type: str = "add",
    description: str = "Пополнение личного баланса через Telegram",
) -> UserBalancePayment:
    """Create a user-balance payment fixture object."""
    return UserBalancePayment(
        user_id=user_id,
        amount=amount,
        operation_type=operation_type,
        description=description,
        transaction_date_time=_now(),
    )


def _wb_balance_payment(
    *,
    wb_cabinet_id: int,
    amount: float,
    operation_type: str = "add",
    description: str = "Пополнение баланса через Telegram",
) -> WBBalancePayment:
    """Create a cabinet-balance payment fixture object."""
    return WBBalancePayment(
        wb_cabinet_id=wb_cabinet_id,
        amount=amount,
        operation_type=operation_type,
        description=description,
        transaction_date_time=_now(),
    )


def _wb_user_cabinet(*, user_id: int, wb_cabinet_id: int, name: str) -> WBUserCabinet:
    """Create a user-cabinet mapping fixture object."""
    return WBUserCabinet(user_id=user_id, wb_cabinet_id=wb_cabinet_id, name=name)


def _partner_payout(*, partner_user_id: int, amount: float) -> PartnerPayout:
    """Create a partner payout fixture object."""
    return PartnerPayout(
        partner_user_id=partner_user_id,
        amount=amount,
        created_by_admin_user_id=99,
        comment=None,
    )


def test_is_real_external_balance_payment_filters_internal_and_admin_records() -> None:
    """Only Telegram top-ups should pass the MVP external-payment heuristic."""
    assert is_real_external_balance_payment(
        _user_balance_payment(user_id=10, amount=100)
    )
    assert is_real_external_balance_payment(
        _wb_balance_payment(wb_cabinet_id=11, amount=250)
    )
    assert not is_real_external_balance_payment(
        _user_balance_payment(
            user_id=10,
            amount=100,
            description="Пополнение администратором.",
        )
    )
    assert not is_real_external_balance_payment(
        _user_balance_payment(
            user_id=10,
            amount=100,
            operation_type="transfer_to_cabinet",
            description="Перевод на кабинет (tg:1)",
        )
    )
    assert not is_real_external_balance_payment(
        _wb_balance_payment(
            wb_cabinet_id=11,
            amount=-50,
            operation_type="subtract",
            description="Пополнение баланса через Telegram",
        )
    )


def test_resolve_cabinet_payment_user_id_picks_single_owner_for_shared_cabinet() -> None:
    """Shared cabinet must map to one invited user, not every linked owner."""
    assert _resolve_cabinet_payment_user_id({10, 11}) == 10
    assert _resolve_cabinet_payment_user_id({11}) == 11
    assert _resolve_cabinet_payment_user_id(set()) is None


def test_calculate_partner_stats_from_records_does_not_double_count_shared_cabinet() -> None:
    """One cabinet top-up must not inflate partner totals for every linked user."""
    partner_user_id = 1
    invites = [
        _invite(code="INV-1", issued_to_user_id=partner_user_id, used_by_user_id=10),
        _invite(code="INV-2", issued_to_user_id=partner_user_id, used_by_user_id=11),
    ]
    wb_user_cabinets = [
        _wb_user_cabinet(user_id=10, wb_cabinet_id=100, name="Shared"),
        _wb_user_cabinet(user_id=11, wb_cabinet_id=100, name="Shared"),
    ]
    wb_balance_payments = [_wb_balance_payment(wb_cabinet_id=100, amount=100)]

    stats = calculate_partner_stats_from_records(
        partner_user_id=partner_user_id,
        invites=invites,
        user_balance_payments=[],
        wb_balance_payments=wb_balance_payments,
        wb_user_cabinets=wb_user_cabinets,
        partner_payouts=[],
    )

    assert stats.clients_paid_sum == Decimal("100.00")
    assert stats.earned_amount == Decimal("15.00")
    assert stats.paid_users_count == 1


def test_calculate_partner_stats_from_records_counts_invites_distinct_users_and_money() -> None:
    """Partner stats should use distinct invited users and only real payments."""
    partner_user_id = 1
    invites = [
        _invite(code="INV-1", issued_to_user_id=partner_user_id, used_by_user_id=10),
        _invite(code="INV-2", issued_to_user_id=partner_user_id, used_by_user_id=11),
        _invite(code="INV-3", issued_to_user_id=partner_user_id, used_by_user_id=10),
        _invite(code="INV-4", issued_to_user_id=partner_user_id, used_by_user_id=None),
    ]
    user_balance_payments = [
        _user_balance_payment(user_id=10, amount=100),
        _user_balance_payment(user_id=10, amount=25),
        _user_balance_payment(
            user_id=10,
            amount=40,
            description="Пополнение администратором.",
        ),
        _user_balance_payment(
            user_id=10,
            amount=30,
            operation_type="transfer_to_cabinet",
            description="Перевод на кабинет (cabinet_id=100, tg=10)",
        ),
        _user_balance_payment(
            user_id=11,
            amount=15,
            description="Компенсация за инцидент",
        ),
    ]
    wb_user_cabinets = [
        _wb_user_cabinet(user_id=11, wb_cabinet_id=100, name="Cabinet A"),
        _wb_user_cabinet(user_id=11, wb_cabinet_id=101, name="Cabinet B"),
    ]
    wb_balance_payments = [
        _wb_balance_payment(wb_cabinet_id=100, amount=50),
        _wb_balance_payment(
            wb_cabinet_id=101,
            amount=70,
            description="Пополнение баланса администратором.",
        ),
    ]
    partner_payouts = [
        _partner_payout(partner_user_id=partner_user_id, amount=6.25),
        _partner_payout(partner_user_id=partner_user_id, amount=5),
    ]

    stats = calculate_partner_stats_from_records(
        partner_user_id=partner_user_id,
        invites=invites,
        user_balance_payments=user_balance_payments,
        wb_balance_payments=wb_balance_payments,
        wb_user_cabinets=wb_user_cabinets,
        partner_payouts=partner_payouts,
    )

    assert stats.invite_count == 4
    assert stats.used_invite_count == 3
    assert stats.invited_users_count == 2
    assert stats.paid_users_count == 2
    assert stats.clients_paid_sum == Decimal("175.00")
    assert stats.earned_amount == Decimal("26.25")
    assert stats.paid_out_amount == Decimal("11.25")
    assert stats.available_to_payout == Decimal("15.00")


class _FakeSession:
    """Minimal async session stub for payout-creation tests."""

    def __init__(
        self,
        *,
        partner_user: User | None,
        admin_user: User | None,
    ) -> None:
        self._partner_user = partner_user
        self._admin_user = admin_user
        self.added: list[PartnerPayout] = []
        self.flush = AsyncMock()
        self.commit = AsyncMock()

    async def get(self, model: type[User], ident: int) -> User | None:
        if ident == (self._partner_user.id if self._partner_user is not None else None):
            return self._partner_user
        if ident == (self._admin_user.id if self._admin_user is not None else None):
            return self._admin_user
        return None

    def add(self, obj: PartnerPayout) -> None:
        self.added.append(obj)


@pytest.mark.asyncio
async def test_create_partner_payout_creates_record_when_amount_is_available(monkeypatch: pytest.MonkeyPatch) -> None:
    """A valid payout should create a PartnerPayout row and commit it."""
    partner_user = User(id=1, username="partner")  # type: ignore[call-arg]
    admin_user = User(id=2, username="admin")  # type: ignore[call-arg]
    session = _FakeSession(partner_user=partner_user, admin_user=admin_user)

    @asynccontextmanager
    async def session_cm(read_only: bool = False):
        yield session

    monkeypatch.setattr("app.modules.partner_program.partner_stats._sm", session_cm)
    monkeypatch.setattr(
        "app.modules.partner_program.partner_stats._get_partner_stats_in_session",
        AsyncMock(
            return_value=PartnerStats(
                partner_user_id=1,
                invite_count=0,
                used_invite_count=0,
                invited_users_count=0,
                paid_users_count=0,
                clients_paid_sum=Decimal("100.00"),
                earned_amount=Decimal("15.00"),
                paid_out_amount=Decimal("5.00"),
                available_to_payout=Decimal("10.00"),
            )
        ),
    )

    payout = await create_partner_payout(
        partner_user_id=1,
        admin_user_id=2,
        amount="10.00",
        comment="June payout",
    )

    assert payout.partner_user_id == 1
    assert payout.created_by_admin_user_id == 2
    assert payout.amount == 10.0
    assert payout.comment == "June payout"
    assert len(session.added) == 1
    session.flush.assert_awaited_once()
    session.commit.assert_awaited_once()


@pytest.mark.asyncio
async def test_create_partner_payout_rejects_amount_above_available(monkeypatch: pytest.MonkeyPatch) -> None:
    """Payouts larger than available earnings must be rejected."""
    partner_user = User(id=1, username="partner")  # type: ignore[call-arg]
    admin_user = User(id=2, username="admin")  # type: ignore[call-arg]
    session = _FakeSession(partner_user=partner_user, admin_user=admin_user)

    @asynccontextmanager
    async def session_cm(read_only: bool = False):
        yield session

    monkeypatch.setattr("app.modules.partner_program.partner_stats._sm", session_cm)
    monkeypatch.setattr(
        "app.modules.partner_program.partner_stats._get_partner_stats_in_session",
        AsyncMock(
            return_value=PartnerStats(
                partner_user_id=1,
                invite_count=0,
                used_invite_count=0,
                invited_users_count=0,
                paid_users_count=0,
                clients_paid_sum=Decimal("100.00"),
                earned_amount=Decimal("15.00"),
                paid_out_amount=Decimal("12.00"),
                available_to_payout=Decimal("3.00"),
            )
        ),
    )

    with pytest.raises(ValueError, match="available partner payout balance"):
        await create_partner_payout(
            partner_user_id=1,
            admin_user_id=2,
            amount="5.00",
        )


@pytest.mark.asyncio
async def test_create_partner_payout_rejects_non_positive_amount() -> None:
    """Zero and negative payouts are invalid."""
    with pytest.raises(ValueError, match="greater than zero"):
        await create_partner_payout(
            partner_user_id=1,
            admin_user_id=2,
            amount="0",
        )


@pytest.mark.asyncio
async def test_create_partner_payout_raises_for_missing_partner_or_admin(monkeypatch: pytest.MonkeyPatch) -> None:
    """Missing partner/admin user is a service invariant violation."""
    admin_user = User(id=2, username="admin")  # type: ignore[call-arg]
    session_missing_partner = _FakeSession(partner_user=None, admin_user=admin_user)

    @asynccontextmanager
    async def missing_partner_cm(read_only: bool = False):
        yield session_missing_partner

    monkeypatch.setattr(
        "app.modules.partner_program.partner_stats._sm",
        missing_partner_cm,
    )

    with pytest.raises(RuntimeError, match="Partner user 1 was not found"):
        await create_partner_payout(
            partner_user_id=1,
            admin_user_id=2,
            amount="1.00",
        )

    partner_user = User(id=1, username="partner")  # type: ignore[call-arg]
    session_missing_admin = _FakeSession(partner_user=partner_user, admin_user=None)

    @asynccontextmanager
    async def missing_admin_cm(read_only: bool = False):
        yield session_missing_admin

    monkeypatch.setattr(
        "app.modules.partner_program.partner_stats._sm",
        missing_admin_cm,
    )

    with pytest.raises(RuntimeError, match="Admin user 2 was not found"):
        await create_partner_payout(
            partner_user_id=1,
            admin_user_id=2,
            amount="1.00",
        )
