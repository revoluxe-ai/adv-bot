"""Unit tests for admin panel partner statistics and reset handlers."""

from __future__ import annotations

from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager
from decimal import Decimal
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from aiogram.types import Chat, Message
from sqlalchemy.ext.asyncio import AsyncSession

from app.client_bot.user_interface.handlers.admin_panel import (
    _PartnerAdminListState,
    admin_reset_user_access_process,
    filter_partner_stats_list,
    process_partner_payout_amount,
    show_admin_panel,
    show_partner_detail,
    show_partner_stats_list,
    start_partner_payout,
)
from app.client_bot.user_interface.states import AdminPartnerList, AdminPartnerPayout
from app.client_bot.user_interface.views.callbacks import PartnerAdminAction
from app.modules.partner_program.partner_stats import PartnerAdminStatsRow, PartnerStats


def make_session_context(
    *, user: object | None
) -> tuple[AsyncMock, AsyncGenerator[AsyncSession, None]]:
    """Build an async session context manager that returns a predefined user."""
    session = AsyncMock(spec=AsyncSession)
    result_mock = MagicMock()
    result_mock.scalar_one_or_none.return_value = user
    session.execute.return_value = result_mock
    session.commit = AsyncMock()

    @asynccontextmanager
    async def session_cm(
        read_only: bool = False,
    ) -> AsyncGenerator[AsyncSession, None]:
        yield session

    return session, session_cm


def _partner_row() -> PartnerAdminStatsRow:
    """Build a sample partner admin stats row for list/detail assertions."""
    return PartnerAdminStatsRow(
        partner_user_id=7,
        user_telegram_id=123456789,
        username="partner_user",
        phone="+79990001122",
        invite_count=4,
        used_invite_count=3,
        invited_users_count=3,
        paid_users_count=2,
        clients_paid_sum=Decimal("200.00"),
        earned_amount=Decimal("30.00"),
        paid_out_amount=Decimal("10.00"),
        available_to_payout=Decimal("20.00"),
    )


def _partner_row_two() -> PartnerAdminStatsRow:
    return PartnerAdminStatsRow(
        partner_user_id=8,
        user_telegram_id=987654321,
        username="second_partner",
        phone="+79990002233",
        invite_count=2,
        used_invite_count=2,
        invited_users_count=5,
        paid_users_count=1,
        clients_paid_sum=Decimal("100.00"),
        earned_amount=Decimal("15.00"),
        paid_out_amount=Decimal("3.00"),
        available_to_payout=Decimal("12.00"),
    )


def _partner_stats() -> PartnerStats:
    """Build sample partner payout stats for payout-flow assertions."""
    return PartnerStats(
        partner_user_id=7,
        invite_count=4,
        used_invite_count=3,
        invited_users_count=3,
        paid_users_count=2,
        clients_paid_sum=Decimal("200.00"),
        earned_amount=Decimal("30.00"),
        paid_out_amount=Decimal("10.00"),
        available_to_payout=Decimal("20.00"),
    )


@pytest.mark.asyncio
async def test_show_admin_panel_contains_partner_and_reset_buttons() -> None:
    """Menu edit runs only when callback.message is a Message; keyboard has partner+reset."""
    callback = MagicMock()
    # bare MagicMock fails isinstance(..., Message); show_admin_panel then skips edit_text.
    callback.message = MagicMock(spec=Message)
    callback.message.edit_text = AsyncMock()
    state = MagicMock()
    state.clear = AsyncMock()

    await show_admin_panel(callback, state)

    state.clear.assert_awaited_once()
    callback.message.edit_text.assert_awaited_once()
    keyboard = callback.message.edit_text.await_args.kwargs["reply_markup"]
    texts = [button.text for row in keyboard.inline_keyboard for button in row]
    assert any("Статистика партнёров" in text for text in texts)
    assert any("Сбросить пользователя" in text for text in texts)


@pytest.mark.asyncio
async def test_show_partner_stats_list_renders_summary_and_partner_buttons() -> None:
    """Partner list handler renders summary text and detail buttons."""
    callback = MagicMock()
    callback.from_user = MagicMock(id=555)
    callback.message = MagicMock(spec=Message)
    callback.message.edit_text = AsyncMock()
    state = MagicMock()
    state.set_state = AsyncMock()

    with patch(
        "app.client_bot.user_interface.handlers.admin_panel.list_partner_stats",
        new=AsyncMock(return_value=[_partner_row(), _partner_row_two()]),
    ), patch(
        "app.client_bot.user_interface.handlers.admin_panel._load_partner_list_state",
        new=AsyncMock(return_value=_PartnerAdminListState()),
    ), patch(
        "app.client_bot.user_interface.handlers.admin_panel._save_partner_list_state",
        new=AsyncMock(),
    ):
        await show_partner_stats_list(callback, state)

    state.set_state.assert_awaited_once_with(AdminPartnerList.waiting_filter)
    callback.message.edit_text.assert_awaited_once()
    text = callback.message.edit_text.await_args.args[0]
    keyboard = callback.message.edit_text.await_args.kwargs["reply_markup"]
    assert "Статистика партнёров" in text
    assert "Всего партнёров: 2" in text
    assert "Всего приглашённых пользователей: 8" in text
    assert "Всего платных пользователей: 3" in text
    assert "Всего оплат приглашённых: 300₽" in text
    assert "Всего заработано партнёрами: 45₽" in text
    assert "Всего выплачено: 13₽" in text
    assert "Всего к выплате: 32₽" in text
    assert "@partner_user" not in text
    assert "+79990001122" not in text
    button_texts = [button.text for row in keyboard.inline_keyboard for button in row]
    assert any("@partner_user | ID 7" in text for text in button_texts)
    assert any("@second_partner | ID 8" in text for text in button_texts)
    assert "Сбросить фильтр" in button_texts


@pytest.mark.asyncio
async def test_filter_partner_stats_list_shows_not_found_message_and_controls() -> None:
    message = MagicMock(spec=Message)
    message.text = "404"
    message.from_user = MagicMock(id=555)
    message.answer = AsyncMock()
    state = MagicMock()

    with patch(
        "app.client_bot.user_interface.handlers.admin_panel.list_partner_stats",
        new=AsyncMock(return_value=[_partner_row()]),
    ), patch(
        "app.client_bot.user_interface.handlers.admin_panel._load_partner_list_state",
        new=AsyncMock(return_value=_PartnerAdminListState()),
    ), patch(
        "app.client_bot.user_interface.handlers.admin_panel._save_partner_list_state",
        new=AsyncMock(),
    ):
        await filter_partner_stats_list(message, state)

    message.answer.assert_awaited_once()
    text = message.answer.await_args.args[0]
    keyboard = message.answer.await_args.kwargs["reply_markup"]
    assert "Партнёры не найдены" in text
    button_texts = [button.text for row in keyboard.inline_keyboard for button in row]
    assert "Сбросить фильтр" in button_texts
    assert "Назад" in button_texts


@pytest.mark.asyncio
async def test_show_partner_detail_renders_detailed_partner_card() -> None:
    callback = MagicMock()
    callback.from_user = MagicMock(id=555)
    callback.message = MagicMock(spec=Message)
    callback.message.edit_text = AsyncMock()
    callback_data = PartnerAdminAction(action="detail", partner_user_id=7)

    with patch(
        "app.client_bot.user_interface.handlers.admin_panel._build_partner_detail_text",
        new=AsyncMock(
            return_value=(
                "Карточка партнёра\n\n"
                "username: partner_user\n"
                "User.id: 7\n"
                "telegram_id: 123456789\n"
                "phone: +79990001122\n\n"
                "invite_count: 4\n"
                "used_invite_count: 3\n"
                "invited_users_count: 3\n"
                "paid_users_count: 2\n\n"
                "clients_paid_sum: 200₽\n"
                "earned_amount: 30₽\n"
                "paid_out_amount: 10₽\n"
                "available_to_payout: 20₽"
            )
        ),
    ), patch(
        "app.client_bot.user_interface.handlers.admin_panel._load_partner_list_state",
        new=AsyncMock(return_value=_PartnerAdminListState()),
    ), patch(
        "app.client_bot.user_interface.handlers.admin_panel._save_partner_list_state",
        new=AsyncMock(),
    ):
        await show_partner_detail(callback, callback_data)

    callback.message.edit_text.assert_awaited_once()
    text = callback.message.edit_text.await_args.args[0]
    keyboard = callback.message.edit_text.await_args.kwargs["reply_markup"]
    assert "username: partner_user" in text
    assert "User.id: 7" in text
    assert "telegram_id: 123456789" in text
    assert "available_to_payout: 20₽" in text
    button_texts = [button.text for row in keyboard.inline_keyboard for button in row]
    assert "Сделать выплату" in button_texts
    assert "Назад к списку" in button_texts


@pytest.mark.asyncio
async def test_start_partner_payout_saves_partner_id_in_fsm() -> None:
    """Payout start stores partner id in FSM and asks for amount."""
    callback = MagicMock()
    callback.from_user = MagicMock(id=555)
    callback.message = MagicMock(spec=Message)
    callback.message.edit_text = AsyncMock()
    state = MagicMock()
    state.update_data = AsyncMock()
    state.set_state = AsyncMock()
    callback_data = PartnerAdminAction(action="payout", partner_user_id=7)

    with patch(
        "app.client_bot.user_interface.handlers.admin_panel.get_partner_stats",
        new=AsyncMock(return_value=_partner_stats()),
    ), patch(
        "app.client_bot.user_interface.handlers.admin_panel._load_partner_list_state",
        new=AsyncMock(return_value=_PartnerAdminListState()),
    ), patch(
        "app.client_bot.user_interface.handlers.admin_panel._save_partner_list_state",
        new=AsyncMock(),
    ):
        await start_partner_payout(callback, callback_data, state)

    state.update_data.assert_awaited_once_with(partner_user_id=7)
    state.set_state.assert_awaited_once_with(AdminPartnerPayout.waiting_amount)
    text = callback.message.edit_text.await_args.args[0]
    assert "Введите сумму выплаты для партнёра 7" in text
    assert "Доступно к выплате: 20₽" in text


@pytest.mark.asyncio
async def test_process_partner_payout_amount_creates_payout_and_shows_updated_stats() -> None:
    """Successful payout creates a record and shows the updated partner card."""
    message = MagicMock(spec=Message)
    message.text = "12.50"
    message.from_user = MagicMock(id=555)
    message.answer = AsyncMock()
    state = MagicMock()
    state.get_data = AsyncMock(return_value={"partner_user_id": 7})
    state.clear = AsyncMock()

    with patch(
        "app.client_bot.user_interface.handlers.admin_panel._get_admin_user_db_id",
        new=AsyncMock(return_value=99),
    ), patch(
        "app.client_bot.user_interface.handlers.admin_panel.create_partner_payout",
        new=AsyncMock(),
    ) as create_mock, patch(
        "app.client_bot.user_interface.handlers.admin_panel._build_partner_detail_text",
        new=AsyncMock(return_value="updated partner card"),
    ):
        await process_partner_payout_amount(message, state)

    create_mock.assert_awaited_once_with(
        partner_user_id=7,
        admin_user_id=99,
        amount="12.50",
    )
    state.clear.assert_awaited_once()
    message.answer.assert_awaited_once()
    assert message.answer.await_args.args[0] == "updated partner card"


@pytest.mark.asyncio
async def test_process_partner_payout_amount_shows_soft_validation_error() -> None:
    """ValueError from payout creation is shown without clearing FSM."""
    message = MagicMock(spec=Message)
    message.text = "50"
    message.from_user = MagicMock(id=555)
    message.answer = AsyncMock()
    state = MagicMock()
    state.get_data = AsyncMock(return_value={"partner_user_id": 7})
    state.clear = AsyncMock()

    with patch(
        "app.client_bot.user_interface.handlers.admin_panel._get_admin_user_db_id",
        new=AsyncMock(return_value=99),
    ), patch(
        "app.client_bot.user_interface.handlers.admin_panel.create_partner_payout",
        new=AsyncMock(side_effect=ValueError("amount exceeds available")),
    ):
        await process_partner_payout_amount(message, state)

    state.clear.assert_not_called()
    message.answer.assert_awaited_once()
    assert "amount exceeds available" in message.answer.await_args.args[0]


@pytest.mark.asyncio
async def test_admin_reset_user_access_process_resets_db_and_subscription_cache() -> None:
    """Reset clears gate/phone in PG, deletes subscription cache, and keeps partner menu."""
    user = MagicMock()
    user.id = 12
    user.username = "target_user"
    user.passed_gate = True
    user.phone = "+79990001122"
    session, session_cm = make_session_context(user=user)

    message = MagicMock(spec=Message)
    message.text = "123456789"
    message.chat = MagicMock(spec=Chat, id=500)
    message.answer = AsyncMock()
    state = MagicMock()
    state.clear = AsyncMock()
    redis_client = MagicMock()
    redis_client.delete = AsyncMock(return_value=1)

    with patch(
        "app.client_bot.user_interface.handlers.admin_panel._sm",
        session_cm,
    ), patch(
        "app.client_bot.user_interface.handlers.admin_panel.AppContainer"
    ) as app_container_cls:
        app_container_cls.return_value.redis_client_wrapper.return_value = redis_client
        await admin_reset_user_access_process(message, state)

    session.commit.assert_awaited_once()
    redis_client.delete.assert_awaited_once_with(
        "client_bot:support_channel_subscription:123456789"
    )
    state.clear.assert_awaited_once()
    message.answer.assert_awaited_once()
    answer_text = message.answer.await_args.args[0]
    assert "сброшен" in answer_text.lower()
    reply_markup = message.answer.await_args.kwargs["reply_markup"]
    texts = [button.text for row in reply_markup.inline_keyboard for button in row]
    assert any("Статистика партнёров" in text for text in texts)
    assert any("Сбросить пользователя" in text for text in texts)
