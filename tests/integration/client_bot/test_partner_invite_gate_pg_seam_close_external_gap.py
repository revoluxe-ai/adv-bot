"""Integration coverage for partner / invite / admin-id / gate PG seams.

Live ``async_session`` + re-read persisted state. Authored under
``/opsx-close-external-gap``; do not run live without
``AUTHORIZE_ONE_LIVE_RUN`` + independent re-audit.
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from decimal import Decimal
from types import SimpleNamespace
from unittest.mock import MagicMock

import pytest
from sqlalchemy import select

from app.client_bot.middlewars.gate import resolve_user_in_session
from app.client_bot.user_interface.handlers.admin_panel import (
    get_admin_user_db_id_in_session,
)
from app.client_bot.user_interface.handlers.invite_show import (
    _resolve_active_invite,
)
from app.modules.partner_program.partner_stats import (
    _get_partner_stats_in_session,
    create_partner_payout_in_session,
    list_partner_stats_in_session,
)
from app.utils.db.models import (
    Invite,
    InviteStatus,
    PartnerPayout,
    User,
    UserBalancePayment,
)

pytestmark = [
    pytest.mark.integration,
    pytest.mark.asyncio,
    pytest.mark.destructive_local,
]


async def _make_user(
    async_session,
    *,
    telegram_id: int,
    username: str,
) -> User:
    """Persist a Telegram user for partner/invite/gate seams."""
    user = User(
        user_telegram_id=telegram_id,
        username=username,
        passed_gate=True,
    )
    async_session.add(user)
    await async_session.commit()
    await async_session.refresh(user)
    return user


@pytest.mark.asyncio
async def test_get_partner_stats_in_session_empty_invites(
    async_session,
) -> None:
    """PURE_READ child returns zeroed stats for a partner without invites."""
    partner = await _make_user(
        async_session, telegram_id=881100001, username="partner_empty"
    )
    stats = await _get_partner_stats_in_session(async_session, partner.id)
    assert stats.partner_user_id == partner.id
    assert stats.invite_count == 0
    assert stats.earned_amount == Decimal("0.00")
    assert stats.available_to_payout == Decimal("0.00")


@pytest.mark.asyncio
async def test_list_partner_stats_in_session_includes_invite_issuer(
    async_session,
) -> None:
    """PURE_READ list seam returns a row for users who issued invites."""
    partner = await _make_user(
        async_session, telegram_id=881100002, username="partner_list"
    )
    now = datetime.now(timezone.utc).replace(tzinfo=None)
    invite = Invite(
        code="CLOSEPG001",
        issued_to_user_id=partner.id,
        issued_at=now,
        expires_at=now + timedelta(days=7),
        status=InviteStatus.ACTIVE,
    )
    async_session.add(invite)
    await async_session.commit()

    rows = await list_partner_stats_in_session(async_session)
    matched = [row for row in rows if row.partner_user_id == partner.id]
    assert len(matched) == 1
    assert matched[0].user_telegram_id == 881100002
    assert matched[0].invite_count == 1


@pytest.mark.asyncio
async def test_create_partner_payout_in_session_persists_row(
    async_session,
) -> None:
    """WRITE payout seam persists PartnerPayout when available balance > 0."""
    partner = await _make_user(
        async_session, telegram_id=881100003, username="partner_pay"
    )
    admin = await _make_user(
        async_session, telegram_id=881100004, username="admin_pay"
    )
    invited = await _make_user(
        async_session, telegram_id=881100013, username="invited_pay"
    )
    now = datetime.now(timezone.utc).replace(tzinfo=None)
    invite = Invite(
        code="CLOSEPG002",
        issued_to_user_id=partner.id,
        issued_at=now,
        expires_at=now + timedelta(days=7),
        status=InviteStatus.USED,
        used_by_user_id=invited.id,
        used_at=now,
    )
    payment = UserBalancePayment(
        user_id=invited.id,
        amount=100.0,
        operation_type="add",
        description="Пополнение через telegram",
    )
    async_session.add(invite)
    async_session.add(payment)
    await async_session.commit()

    payout = await create_partner_payout_in_session(
        async_session,
        partner_user_id=partner.id,
        admin_user_id=admin.id,
        amount="5.00",
        comment="close-gap",
    )
    reread = await async_session.scalar(
        select(PartnerPayout).where(PartnerPayout.id == payout.id)
    )
    assert reread is not None
    assert float(reread.amount) == 5.0
    assert reread.comment == "close-gap"


@pytest.mark.asyncio
async def test_get_admin_user_db_id_in_session_resolves_id(
    async_session,
) -> None:
    """PURE_READ admin id seam resolves telegram id → User.id."""
    admin = await _make_user(
        async_session, telegram_id=881100005, username="admin_id"
    )
    resolved = await get_admin_user_db_id_in_session(async_session, 881100005)
    assert resolved == admin.id


@pytest.mark.asyncio
async def test_resolve_active_invite_creates_and_persists(
    async_session,
) -> None:
    """WRITE invite resolve creates ACTIVE invite; re-select proves status."""
    user = await _make_user(
        async_session, telegram_id=881100006, username="invite_user"
    )
    now = datetime.now(timezone.utc).replace(tzinfo=None)
    invite = await _resolve_active_invite(
        session=async_session,
        user=user,
        now_utc=now,
    )
    assert invite is not None
    assert invite.status == InviteStatus.ACTIVE
    reread = await async_session.scalar(
        select(Invite).where(Invite.id == invite.id)
    )
    assert reread is not None
    assert reread.issued_to_user_id == user.id
    assert reread.status == InviteStatus.ACTIVE


@pytest.mark.asyncio
async def test_resolve_user_in_session_creates_missing_user(
    async_session,
) -> None:
    """WRITE gate seam creates User when telegram id is unknown."""
    telegram_id = 881100007
    from aiogram.types import Message

    message = MagicMock(spec=Message)
    message.from_user = SimpleNamespace(username="gate_new", id=telegram_id)
    message.chat = SimpleNamespace(id=telegram_id)

    created = await resolve_user_in_session(async_session, message, telegram_id)
    assert created.user_telegram_id == telegram_id
    reread = await async_session.scalar(
        select(User).where(User.user_telegram_id == telegram_id)
    )
    assert reread is not None
    assert reread.id == created.id


class _LiveSessionMaker:
    """Yield a live async_session from parent ``sm(read_only=…)`` calls."""

    def __init__(self, session) -> None:
        self.session = session
        self.last_read_only: bool | None = None

    def __call__(self, *, read_only: bool = False) -> "_LiveSessionMaker":
        self.last_read_only = read_only
        return self

    async def __aenter__(self):
        return self.session

    async def __aexit__(self, *args: object) -> None:
        return None


@pytest.mark.asyncio
async def test_get_partner_stats_parent_live_sm(async_session, monkeypatch) -> None:
    """Parent ``get_partner_stats`` opens live sm and returns persisted stats."""
    import app.modules.partner_program.partner_stats as partner_stats

    partner = await _make_user(
        async_session, telegram_id=881100021, username="partner_parent"
    )
    live_sm = _LiveSessionMaker(async_session)
    monkeypatch.setattr(partner_stats, "_sm", live_sm)

    stats = await partner_stats.get_partner_stats(partner.id)
    assert live_sm.last_read_only is True
    assert stats.partner_user_id == partner.id
    assert stats.invite_count == 0


@pytest.mark.asyncio
async def test_list_partner_stats_parent_live_sm(async_session, monkeypatch) -> None:
    """Parent ``list_partner_stats`` reads invite issuers via live sm."""
    import app.modules.partner_program.partner_stats as partner_stats

    partner = await _make_user(
        async_session, telegram_id=881100022, username="partner_list_parent"
    )
    now = datetime.now(timezone.utc).replace(tzinfo=None)
    async_session.add(
        Invite(
            code="CLOSEPG021",
            issued_to_user_id=partner.id,
            issued_at=now,
            expires_at=now + timedelta(days=7),
            status=InviteStatus.ACTIVE,
        )
    )
    await async_session.commit()

    live_sm = _LiveSessionMaker(async_session)
    monkeypatch.setattr(partner_stats, "_sm", live_sm)
    rows = await partner_stats.list_partner_stats()
    assert live_sm.last_read_only is True
    matched = [row for row in rows if row.partner_user_id == partner.id]
    assert len(matched) == 1


@pytest.mark.asyncio
async def test_create_partner_payout_parent_live_sm(async_session, monkeypatch) -> None:
    """Parent ``create_partner_payout`` persists payout via live write sm."""
    import app.modules.partner_program.partner_stats as partner_stats

    partner = await _make_user(
        async_session, telegram_id=881100023, username="partner_pay_parent"
    )
    admin = await _make_user(
        async_session, telegram_id=881100024, username="admin_pay_parent"
    )
    invited = await _make_user(
        async_session, telegram_id=881100025, username="invited_pay_parent"
    )
    now = datetime.now(timezone.utc).replace(tzinfo=None)
    async_session.add(
        Invite(
            code="CLOSEPG022",
            issued_to_user_id=partner.id,
            issued_at=now,
            expires_at=now + timedelta(days=7),
            status=InviteStatus.USED,
            used_by_user_id=invited.id,
            used_at=now,
        )
    )
    async_session.add(
        UserBalancePayment(
            user_id=invited.id,
            amount=100.0,
            operation_type="add",
            description="Пополнение через telegram",
        )
    )
    await async_session.commit()

    live_sm = _LiveSessionMaker(async_session)
    monkeypatch.setattr(partner_stats, "_sm", live_sm)
    payout = await partner_stats.create_partner_payout(
        partner_user_id=partner.id,
        admin_user_id=admin.id,
        amount="4.00",
        comment="parent-live",
    )
    assert live_sm.last_read_only is False
    reread = await async_session.scalar(
        select(PartnerPayout).where(PartnerPayout.id == payout.id)
    )
    assert reread is not None
    assert float(reread.amount) == 4.0


@pytest.mark.asyncio
async def test_get_admin_user_db_id_parent_live_sm(async_session, monkeypatch) -> None:
    """Parent ``_get_admin_user_db_id`` resolves id via live read sm."""
    import app.client_bot.user_interface.handlers.admin_panel as admin_panel

    admin = await _make_user(
        async_session, telegram_id=881100026, username="admin_parent"
    )
    live_sm = _LiveSessionMaker(async_session)
    monkeypatch.setattr(admin_panel, "_sm", live_sm)
    resolved = await admin_panel._get_admin_user_db_id(881100026)
    assert live_sm.last_read_only is True
    assert resolved == admin.id


@pytest.mark.asyncio
async def test_resolve_user_parent_live_sm(async_session, monkeypatch) -> None:
    """Parent ``_resolve_user`` creates User via live write sm."""
    import app.client_bot.middlewars.gate as gate_mod
    from aiogram.types import Message

    telegram_id = 881100027
    live_sm = _LiveSessionMaker(async_session)
    monkeypatch.setattr(gate_mod, "_sm", live_sm)
    message = MagicMock(spec=Message)
    message.from_user = SimpleNamespace(username="gate_parent", id=telegram_id)
    message.chat = SimpleNamespace(id=telegram_id)

    created = await gate_mod._resolve_user(message, telegram_id)
    assert live_sm.last_read_only is False
    reread = await async_session.scalar(
        select(User).where(User.user_telegram_id == telegram_id)
    )
    assert reread is not None
    assert reread.id == created.id


@pytest.mark.asyncio
async def test_load_user_by_telegram_id_in_session_reads(
    async_session,
) -> None:
    """PURE_READ invite child loads User by telegram id."""
    from app.client_bot.user_interface.handlers.invite_show import (
        load_user_by_telegram_id_in_session,
    )

    user = await _make_user(
        async_session, telegram_id=881100028, username="invite_load"
    )
    loaded = await load_user_by_telegram_id_in_session(async_session, 881100028)
    assert loaded is not None
    assert loaded.id == user.id


@pytest.mark.asyncio
async def test_invite_show_handler_parent_live_sm(async_session, monkeypatch) -> None:
    """Parent ``invite_show_handler`` creates invite via live write sm."""
    from decimal import Decimal
    from unittest.mock import AsyncMock

    import app.client_bot.user_interface.handlers.invite_show as invite_show
    from app.modules.partner_program.partner_stats import PartnerStats

    user = await _make_user(
        async_session, telegram_id=881100029, username="invite_handler"
    )
    live_sm = _LiveSessionMaker(async_session)
    monkeypatch.setattr(invite_show, "_sm", live_sm)
    monkeypatch.setattr(
        invite_show,
        "get_partner_stats",
        AsyncMock(
            return_value=PartnerStats(
                partner_user_id=user.id,
                invite_count=0,
                used_invite_count=0,
                invited_users_count=0,
                paid_users_count=0,
                clients_paid_sum=Decimal("0.00"),
                earned_amount=Decimal("0.00"),
                paid_out_amount=Decimal("0.00"),
                available_to_payout=Decimal("0.00"),
            )
        ),
    )

    callback = MagicMock()
    callback.message = SimpleNamespace(chat=SimpleNamespace(id=881100029))
    callback.from_user = SimpleNamespace(id=881100029)
    bot = AsyncMock()

    await invite_show.invite_show_handler(callback, bot)

    assert live_sm.last_read_only is False
    reread = await async_session.scalar(
        select(Invite).where(Invite.issued_to_user_id == user.id)
    )
    assert reread is not None
    assert reread.status == InviteStatus.ACTIVE
    bot.send_message.assert_awaited()
