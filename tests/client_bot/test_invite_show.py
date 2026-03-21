"""Тесты выдачи инвайтов V1 (invite:show)."""

import datetime
from datetime import UTC, timedelta
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.client_bot.user_interface.handlers.invite_show import invite_show_handler
from app.utils.db.models import Invite, InviteStatus, User


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
    inv = MagicMock(spec=Invite)
    inv.code = code
    inv.status = status
    inv.issued_to_user_id = issued_to_user_id
    inv.expires_at = expires_at or (
        datetime.datetime.now(UTC).replace(tzinfo=None) + timedelta(days=5)
    )
    inv.id = 1
    return inv


async def test_invite_show_active_not_expired_returns_same_code():
    """ACTIVE и не истёк → возвращается тот же код."""
    user = _make_user(id=1, telegram_id=3001)
    invite = _make_invite(
        code="SAME-CODE",
        status=InviteStatus.ACTIVE,
        issued_to_user_id=1,
    )

    session = AsyncMock()
    session.execute = AsyncMock()
    session.commit = AsyncMock()

    call_count = [0]

    async def execute_side_effect(stmt):
        call_count[0] += 1
        res = MagicMock()
        if call_count[0] == 1:
            res.scalar_one_or_none.return_value = user
        elif call_count[0] == 2:
            res.scalar_one_or_none.return_value = invite
        else:
            res.scalar_one_or_none.return_value = None
        return res

    session.execute.side_effect = execute_side_effect

    class MockSessionCM:
        async def __aenter__(self):
            return session

        async def __aexit__(self, *args):
            pass

    with patch(
        "app.client_bot.user_interface.handlers.invite_show._sm",
        lambda read_only=False: MockSessionCM(),
    ):
        callback = MagicMock()
        callback.message = MagicMock()
        callback.message.chat.id = 3001
        callback.from_user = MagicMock(id=3001)
        callback.bot = AsyncMock()
        callback.bot.send_message = AsyncMock()
        callback.answer = AsyncMock()

        await invite_show_handler(callback, callback.bot)

        callback.bot.send_message.assert_called_once()
        args = callback.bot.send_message.call_args[0]
        kwargs = callback.bot.send_message.call_args[1]
        text = kwargs.get("text", args[1] if len(args) > 1 else "")
        assert "Ваш инвайт:" in text
        assert "SAME-CODE" in text


async def test_invite_show_cooldown_zero_allows_new_invite_without_wait_message():
    """При нулевом кулдауне после недавней выдачи можно сразу получить новый инвайт."""
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
        res = MagicMock()
        if call_count[0] == 1:
            res.scalar_one_or_none.return_value = user
        elif call_count[0] == 2:
            res.scalar_one_or_none.return_value = None
        else:
            res.scalar_one_or_none.return_value = None
        return res

    session.execute.side_effect = execute_side_effect

    class MockSessionCM:
        async def __aenter__(self):
            return session

        async def __aexit__(self, *args):
            pass

    with patch(
        "app.client_bot.user_interface.handlers.invite_show._sm",
        lambda read_only=False: MockSessionCM(),
    ):
        callback = MagicMock()
        callback.message = MagicMock()
        callback.message.chat.id = 3002
        callback.from_user = MagicMock(id=3002)
        callback.bot = AsyncMock()
        callback.bot.send_message = AsyncMock()
        callback.answer = AsyncMock()

        await invite_show_handler(callback, callback.bot)

        callback.bot.send_message.assert_called_once()
        text = callback.bot.send_message.call_args[1].get(
            "text",
            callback.bot.send_message.call_args[0][1]
            if len(callback.bot.send_message.call_args[0]) > 1
            else "",
        )
        assert "Ваш инвайт:" in text
        assert "доступен после" not in text
