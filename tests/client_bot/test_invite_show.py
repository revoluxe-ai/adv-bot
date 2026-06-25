"""Tests for the partner page opened from the existing invite entry point."""

from __future__ import annotations

import datetime
from datetime import UTC, timedelta
from decimal import Decimal
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.client_bot.user_interface.handlers.invite_show import invite_show_handler
from app.modules.partner_program.partner_stats import PartnerStats
from app.utils.db.models import Invite, InviteStatus, User
from tests.helpers.telegram_message_asserts import (
    assert_keyboard_has_buttons,
    assert_message_contains_required_phrases,
    assert_message_within_telegram_limit,
    assert_no_raw_technical_text,
)

pytestmark = [pytest.mark.asyncio]


def _make_user(
    id: int = 1,
    telegram_id: int = 3001,
    last_invite_issued_at: datetime.datetime | None = None,
) -> User:
    user = MagicMock(spec=User)
    user.id = id
    user.user_telegram_id = telegram_id
    user.last_invite_issued_at = last_invite_issued_at
    return user


def _make_invite(
    code: str = "AB12-CD34",
    status: InviteStatus = InviteStatus.ACTIVE,
    issued_to_user_id: int = 1,
    expires_at: datetime.datetime | None = None,
) -> Invite:
    invite = MagicMock(spec=Invite)
    invite.code = code
    invite.status = status
    invite.issued_to_user_id = issued_to_user_id
    invite.expires_at = expires_at or (
        datetime.datetime.now(UTC).replace(tzinfo=None) + timedelta(days=5)
    )
    invite.id = 1
    return invite


def _partner_stats() -> PartnerStats:
    return PartnerStats(
        partner_user_id=1,
        invite_count=3,
        used_invite_count=2,
        invited_users_count=2,
        paid_users_count=1,
        clients_paid_sum=Decimal("120.00"),
        earned_amount=Decimal("18.00"),
        paid_out_amount=Decimal("5.00"),
        available_to_payout=Decimal("13.00"),
    )


async def test_invite_show_active_not_expired_opens_partner_page() -> None:
    """Existing active invite should open the partner page with stats and payout URL."""
    user = _make_user(id=1, telegram_id=3001)
    invite = _make_invite(code="SAME-CODE", status=InviteStatus.ACTIVE)

    session = AsyncMock()
    session.execute = AsyncMock()
    session.commit = AsyncMock()
    call_count = [0]

    async def execute_side_effect(stmt):
        call_count[0] += 1
        result = MagicMock()
        if call_count[0] == 1:
            result.scalar_one_or_none.return_value = user
        else:
            result.scalar_one_or_none.return_value = invite
        return result

    session.execute.side_effect = execute_side_effect

    class MockSessionCM:
        async def __aenter__(self):
            return session

        async def __aexit__(self, *args):
            pass

    with patch(
        "app.client_bot.user_interface.handlers.invite_show._sm",
        lambda read_only=False: MockSessionCM(),
    ), patch(
        "app.client_bot.user_interface.handlers.invite_show.get_partner_stats",
        new=AsyncMock(return_value=_partner_stats()),
    ):
        callback = MagicMock()
        callback.message = MagicMock()
        callback.message.chat.id = 3001
        callback.from_user = MagicMock(id=3001)
        callback.bot = AsyncMock()
        callback.bot.send_message = AsyncMock()

        await invite_show_handler(callback, callback.bot)

    callback.bot.send_message.assert_awaited_once()
    args = callback.bot.send_message.call_args.args
    kwargs = callback.bot.send_message.call_args.kwargs
    text = kwargs.get("text", args[1] if len(args) > 1 else "")
    assert_message_within_telegram_limit(text)
    assert_message_contains_required_phrases(
        text,
        [
            "Инвайты / партнёрка",
            "Ваш инвайт: SAME-CODE",
            "Создано инвайтов: 3",
            "Использовано: 2",
            "Пришло пользователей: 2",
            "Платных пользователей: 1",
            "Оплаты приглашённых: 120 ₽",
            "Ваши 15%: 18 ₽",
            "Выплачено: 5 ₽",
            "К выплате: 13 ₽",
        ],
    )
    assert_no_raw_technical_text(text)
    keyboard = kwargs["reply_markup"]
    assert_keyboard_has_buttons(keyboard, ["Запросить выплату"])
    assert keyboard.inline_keyboard[0][0].url == "https://t.me/sky_manager_1"


async def test_invite_show_generates_new_invite_and_still_opens_partner_page() -> None:
    """When there is no active invite, the handler should generate one and show stats."""
    user = _make_user(
        id=1,
        telegram_id=3002,
        last_invite_issued_at=datetime.datetime.now(UTC).replace(tzinfo=None)
        - timedelta(hours=1),
    )

    session = AsyncMock()
    session.execute = AsyncMock()
    session.commit = AsyncMock()
    session.add = MagicMock()
    call_count = [0]

    async def execute_side_effect(stmt):
        call_count[0] += 1
        result = MagicMock()
        if call_count[0] == 1:
            result.scalar_one_or_none.return_value = user
        elif call_count[0] == 2:
            result.scalar_one_or_none.return_value = None
        else:
            result.scalar_one_or_none.return_value = None
        return result

    session.execute.side_effect = execute_side_effect

    class MockSessionCM:
        async def __aenter__(self):
            return session

        async def __aexit__(self, *args):
            pass

    with patch(
        "app.client_bot.user_interface.handlers.invite_show._sm",
        lambda read_only=False: MockSessionCM(),
    ), patch(
        "app.client_bot.user_interface.handlers.invite_show.get_partner_stats",
        new=AsyncMock(return_value=_partner_stats()),
    ):
        callback = MagicMock()
        callback.message = MagicMock()
        callback.message.chat.id = 3002
        callback.from_user = MagicMock(id=3002)
        callback.bot = AsyncMock()
        callback.bot.send_message = AsyncMock()

        await invite_show_handler(callback, callback.bot)

    callback.bot.send_message.assert_awaited_once()
    args = callback.bot.send_message.call_args.args
    kwargs = callback.bot.send_message.call_args.kwargs
    text = kwargs.get("text", args[1] if len(args) > 1 else "")
    assert_message_within_telegram_limit(text)
    assert_message_contains_required_phrases(
        text,
        ["Инвайты / партнёрка", "Ваш инвайт:", "Создано инвайтов: 3"],
    )
    assert_no_raw_technical_text(text)
