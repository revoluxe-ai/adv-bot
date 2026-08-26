"""Тесты активации гейта по инвайт-коду (Block B)."""

import datetime
from contextlib import asynccontextmanager
from datetime import UTC, timedelta
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from sqlalchemy.engine.result import Result

from app.client_bot.user_interface.handlers.gate import gate_invite_process_code
from app.utils.db.models import Invite, InviteStatus, User
from app.utils.db.passed_gate_reason import PassedGateReason


pytestmark = [pytest.mark.asyncio]


def _make_user(id: int = 1, telegram_id: int = 2001, passed_gate: bool = False) -> User:
    user = MagicMock(spec=User)
    user.id = id
    user.user_telegram_id = telegram_id
    user.passed_gate = passed_gate
    user.passed_gate_at = None
    user.passed_gate_reason = None
    user.wb_user_cabinets = []
    return user


def _make_invite(
    code: str = "AB12-CD34",
    status: InviteStatus = InviteStatus.ACTIVE,
    expires_at: datetime.datetime | None = None,
    used_by_user_id: int | None = None,
) -> Invite:
    now = datetime.datetime.now(UTC).replace(tzinfo=None)
    inv = MagicMock(spec=Invite)
    inv.code = code
    inv.status = status
    inv.expires_at = expires_at or (now + timedelta(days=7))
    inv.used_by_user_id = used_by_user_id
    inv.used_at = None
    inv.id = 1
    return inv


async def test_gate_invite_successful_activation(
    mock_bot: AsyncMock,
    mock_state: MagicMock,
):
    """Успешная активация: ACTIVE invite, не истёк → user.passed_gate=True, reason=INVITE_CODE_ENTRY."""
    user = _make_user(id=1, telegram_id=2001, passed_gate=False)
    invite = _make_invite(code="XY99-ZZ00", status=InviteStatus.ACTIVE)

    session = AsyncMock()
    session.execute = AsyncMock()
    session.commit = AsyncMock()
    session.add = MagicMock()

    call_count = [0]

    async def execute_side_effect(stmt):
        call_count[0] += 1
        res = MagicMock(spec=Result)
        if call_count[0] == 1:
            res.scalar_one_or_none.return_value = user
        elif call_count[0] == 2:
            res.scalar_one_or_none.return_value = invite
        elif call_count[0] == 3:
            res.rowcount = 1
        elif call_count[0] == 4:
            res.rowcount = 1
            user.passed_gate = True
            user.passed_gate_reason = PassedGateReason.INVITE_CODE_ENTRY
            user.passed_gate_at = datetime.datetime.now(UTC).replace(tzinfo=None)
            user.wb_user_cabinets = []
        else:
            res.scalar_one_or_none.return_value = None
        return res

    session.execute.side_effect = execute_side_effect

    @asynccontextmanager
    async def session_cm(read_only: bool = False):
        yield session

    message = MagicMock()
    message.chat.id = 2001
    message.from_user = MagicMock(id=2001)
    message.text = "  xy99-zz00  "

    with patch(
        "app.client_bot.user_interface.handlers.gate._sm",
        session_cm,
    ):
        await gate_invite_process_code(message, mock_bot, mock_state)

    assert user.passed_gate is True
    assert user.passed_gate_reason == PassedGateReason.INVITE_CODE_ENTRY
    mock_state.clear.assert_awaited_once()


async def test_gate_invite_wrong_code_user_stays_blocked(
    mock_bot: AsyncMock,
    mock_state: MagicMock,
):
    """Неверный код → user.passed_gate остаётся false и пользователю заново показывается invite-screen."""
    user = _make_user(telegram_id=2002, passed_gate=False)
    session = AsyncMock()
    session.execute = AsyncMock()
    session.commit = AsyncMock()

    call_count = [0]

    async def execute_side_effect(stmt):
        call_count[0] += 1
        res = MagicMock(spec=Result)
        if call_count[0] == 1:
            res.scalar_one_or_none.return_value = user
        else:
            res.scalar_one_or_none.return_value = None
        return res

    session.execute.side_effect = execute_side_effect

    @asynccontextmanager
    async def session_cm(read_only: bool = False):
        yield session

    message = MagicMock()
    message.chat.id = 2002
    message.from_user = MagicMock(id=2002)
    message.text = "NONEXISTENT"

    with patch(
        "app.client_bot.user_interface.handlers.gate._sm",
        session_cm,
    ):
        await gate_invite_process_code(message, mock_bot, mock_state)

    assert user.passed_gate is False
    assert mock_bot.send_message.await_count == 2

    first_call = mock_bot.send_message.await_args_list[0]
    first_text = first_call.kwargs.get(
        "text", first_call.args[1] if len(first_call.args) > 1 else ""
    )
    assert "Неверный" in first_text

    second_call = mock_bot.send_message.await_args_list[1]
    second_text = second_call.kwargs.get(
        "text", second_call.args[1] if len(second_call.args) > 1 else ""
    )
    assert "Ввести инвайт" in second_text
    assert "инвайт-код" in second_text


async def test_gate_invite_expired_becomes_expired_user_stays_blocked(
    mock_bot: AsyncMock,
    mock_state: MagicMock,
):
    """Invite ACTIVE, но expires_at в прошлом → invite становится EXPIRED, user.passed_gate false."""
    user = _make_user(telegram_id=2003, passed_gate=False)
    past = datetime.datetime.now(UTC).replace(tzinfo=None) - timedelta(days=1)
    invite = _make_invite(code="EXPIRED1", status=InviteStatus.ACTIVE, expires_at=past)

    session = AsyncMock()
    session.execute = AsyncMock()
    session.commit = AsyncMock()
    session.add = MagicMock()

    call_count = [0]

    async def execute_side_effect(stmt):
        call_count[0] += 1
        res = MagicMock(spec=Result)
        if call_count[0] == 1:
            res.scalar_one_or_none.return_value = user
        elif call_count[0] == 2:
            res.scalar_one_or_none.return_value = invite
        else:
            res.scalar_one_or_none.return_value = None
        return res

    session.execute.side_effect = execute_side_effect

    @asynccontextmanager
    async def session_cm(read_only: bool = False):
        yield session

    message = MagicMock()
    message.chat.id = 2003
    message.from_user = MagicMock(id=2003)
    message.text = "EXPIRED1"

    with patch(
        "app.client_bot.user_interface.handlers.gate._sm",
        session_cm,
    ):
        await gate_invite_process_code(message, mock_bot, mock_state)

    assert user.passed_gate is False
    assert invite.status == InviteStatus.EXPIRED
    session.add.assert_called()


async def test_gate_invite_already_used_does_not_open_access(
    mock_bot: AsyncMock,
    mock_state: MagicMock,
):
    """Invite уже USED → второй ввод не открывает доступ."""
    user = _make_user(telegram_id=2004, passed_gate=False)
    invite = _make_invite(
        code="USED01",
        status=InviteStatus.USED,
        used_by_user_id=9999,
    )

    session = AsyncMock()
    session.execute = AsyncMock()
    session.commit = AsyncMock()

    call_count = [0]

    async def execute_side_effect(stmt):
        call_count[0] += 1
        res = MagicMock(spec=Result)
        if call_count[0] == 1:
            res.scalar_one_or_none.return_value = user
        elif call_count[0] == 2:
            res.scalar_one_or_none.return_value = invite
        else:
            res.scalar_one_or_none.return_value = None
        return res

    session.execute.side_effect = execute_side_effect

    @asynccontextmanager
    async def session_cm(read_only: bool = False):
        yield session

    message = MagicMock()
    message.chat.id = 2004
    message.from_user = MagicMock(id=2004)
    message.text = "USED01"

    with patch(
        "app.client_bot.user_interface.handlers.gate._sm",
        session_cm,
    ):
        await gate_invite_process_code(message, mock_bot, mock_state)

    assert user.passed_gate is False
    mock_bot.send_message.assert_called()
    args, kwargs = mock_bot.send_message.call_args[0], mock_bot.send_message.call_args[1]
    text = kwargs.get("text", args[1] if len(args) > 1 else "")
    assert "использован" in text or "отозван" in text


async def test_gate_invite_non_start_command_keeps_state_and_prompts_code(
    mock_bot: AsyncMock,
    mock_state: MagicMock,
):
    """Команда /starting не должна обрабатываться как /start в invite-сценарии."""
    message = MagicMock()
    message.chat.id = 2005
    message.from_user = MagicMock(id=2005)
    message.text = "/starting"

    await gate_invite_process_code(message, mock_bot, mock_state)

    mock_state.clear.assert_not_awaited()
    mock_bot.send_message.assert_awaited_once()
    args, kwargs = mock_bot.send_message.call_args
    text = kwargs.get("text", args[1] if len(args) > 1 else "")
    assert "ожидается инвайт-код" in text


async def test_gate_invite_start_command_is_left_for_global_middleware(
    mock_bot: AsyncMock,
    mock_state: MagicMock,
):
    """`/start` не должен обрабатываться в gate-хендлере: это зона ReturnToStart."""
    message = MagicMock()
    message.chat.id = 2006
    message.from_user = MagicMock(id=2006)
    message.text = "/start"

    await gate_invite_process_code(message, mock_bot, mock_state)

    mock_state.clear.assert_not_awaited()
    mock_bot.send_message.assert_not_awaited()


async def test_gate_invite_start_command_case_insensitive_early_return(
    mock_bot: AsyncMock,
    mock_state: MagicMock,
) -> None:
    """`/Start` в FSM инвайта не должен уходить в ветку «ожидается инвайт-код»."""
    message = MagicMock()
    message.chat.id = 2007
    message.from_user = MagicMock(id=2007)
    message.text = "/Start"

    await gate_invite_process_code(message, mock_bot, mock_state)

    mock_state.clear.assert_not_awaited()
    mock_bot.send_message.assert_not_awaited()


@pytest.fixture
def mock_bot():
    bot = AsyncMock()
    bot.send_message = AsyncMock()
    return bot


@pytest.fixture
def mock_state():
    state = MagicMock()
    state.clear = AsyncMock()
    return state
