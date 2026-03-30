"""Обработчики гейта: инвайт (ввод кода), оферта, восстановление доступа."""

import datetime
from datetime import UTC

from aiogram import F, Bot, Router, types
from aiogram.filters import StateFilter
from aiogram.fsm.context import FSMContext
from sqlalchemy import select, update

from app.client_bot.user_interface.handlers.presentation_invite import (
    normalize_invite_code,
)
from app.client_bot.user_interface.handlers.shop_choice_message import MainMenu
from app.client_bot.user_interface.states import GateInvite
from app.client_bot.user_interface.views.callbacks import Gate
from app.client_bot.const import OFFERTA_URL
from app.client_bot.user_interface.views.gate import get_gate_keyboard, get_gate_message_text
from app.utils.db.models import Invite, InviteStatus, User
from app.utils.db.passed_gate_reason import PassedGateReason
from app.utils.db.session_maker import get_async_session_maker

router = Router()
_sm = get_async_session_maker


async def _clear_invite_fsm_and_show_gate(
    bot: Bot,
    chat_id: int,
    state: FSMContext,
    error_line: str,
) -> None:
    """Сброс FSM и возврат к экрану гейта (текст + клавиатура) после ошибки ввода инвайта."""
    await state.clear()
    full_text = f"{error_line}\n\n{get_gate_message_text()}"
    _ = await bot.send_message(
        chat_id,
        full_text,
        reply_markup=get_gate_keyboard(),
    )


@router.callback_query(Gate.filter(F.action == "invite_enter"))
async def gate_invite_enter(
    callback: types.CallbackQuery, bot: Bot, state: FSMContext
) -> None:
    """Перевод в FSM ввода инвайт-кода и запрос кода."""
    if callback.message is None:
        return
    await state.set_state(GateInvite.waiting_code)
    _ = await bot.send_message(
        callback.message.chat.id,
        "Отправьте инвайт-код одним сообщением.",
    )


@router.message(StateFilter(GateInvite.waiting_code), F.text)
async def gate_invite_process_code(
    message: types.Message, bot: Bot, state: FSMContext
) -> None:
    """Приём инвайт-кода: атомарная активация или ошибка + gate."""
    if not message.text or not message.from_user:
        return
    code = normalize_invite_code(message.text)
    if not code:
        await _clear_invite_fsm_and_show_gate(
            bot,
            message.chat.id,
            state,
            "Введите непустой инвайт-код.",
        )
        return

    now_utc = datetime.datetime.now(UTC).replace(tzinfo=None)
    telegram_id = message.from_user.id
    chat_id = message.chat.id

    async with _sm(read_only=False) as session:
        # User by telegram_id
        user_stmt = select(User).where(User.user_telegram_id == telegram_id)
        user_result = await session.execute(user_stmt)
        user = user_result.scalar_one_or_none()
        if not user:
            await _clear_invite_fsm_and_show_gate(
                bot,
                chat_id,
                state,
                "Ошибка: пользователь не найден. Попробуйте /start.",
            )
            return

        # Invite by code
        invite_stmt = select(Invite).where(Invite.code == code)
        invite_result = await session.execute(invite_stmt)
        invite = invite_result.scalar_one_or_none()

        if invite is None:
            await _clear_invite_fsm_and_show_gate(
                bot,
                chat_id,
                state,
                "Неверный инвайт-код.",
            )
            return

        if invite.status != InviteStatus.ACTIVE:
            await _clear_invite_fsm_and_show_gate(
                bot,
                chat_id,
                state,
                "Этот инвайт уже использован или отозван.",
            )
            return

        if invite.expires_at < now_utc:
            invite.status = InviteStatus.EXPIRED
            session.add(invite)
            await session.commit()
            await _clear_invite_fsm_and_show_gate(
                bot,
                chat_id,
                state,
                "Срок действия инвайт-кода истёк.",
            )
            return

        # Атомарная активация: UPDATE invite только если ACTIVE и не истёк
        update_invite_stmt = (
            update(Invite)
            .where(
                Invite.code == code,
                Invite.status == InviteStatus.ACTIVE,
                Invite.expires_at >= now_utc,
            )
            .values(
                status=InviteStatus.USED,
                used_by_user_id=user.id,
                used_at=now_utc,
            )
        )
        result = await session.execute(update_invite_stmt)
        rowcount = getattr(result, "rowcount", 0)
        if rowcount != 1:
            await _clear_invite_fsm_and_show_gate(
                bot,
                chat_id,
                state,
                "Этот инвайт уже использован или истёк.",
            )
            return

        # В той же транзакции: открыть гейт пользователю
        _ = await session.execute(
            update(User)
            .where(User.id == user.id)
            .values(
                passed_gate=True,
                passed_gate_at=now_utc,
                passed_gate_reason=PassedGateReason.INVITE_CODE_ENTRY,
            )
        )
        await session.commit()

    await state.clear()
    await MainMenu(bot, chat_id, full_client_ui=True)()


@router.callback_query(Gate.filter(F.action == "offer_open"))
async def gate_offer_open(callback: types.CallbackQuery, bot: Bot) -> None:
    """Отправка ссылки на оферту."""
    if callback.message is None:
        return
    chat_id = callback.message.chat.id
    _ = await bot.send_message(
        chat_id,
        f"Оферта: {OFFERTA_URL}",
    )


@router.callback_query(Gate.filter(F.action == "restore_request"))
async def gate_restore_request(callback: types.CallbackQuery, bot: Bot) -> None:
    """Заглушка: запрос на восстановление доступа принят."""
    if callback.message is None:
        return
    chat_id = callback.message.chat.id
    _ = await bot.send_message(
        chat_id,
        "Запрос на восстановление доступа принят.",
        reply_markup=get_gate_keyboard(),
    )
