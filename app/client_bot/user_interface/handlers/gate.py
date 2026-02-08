"""Обработчики гейта: инвайт (ввод кода), входной платёж, оферта, восстановление доступа."""

import datetime
import json
from datetime import UTC

from aiogram import F, Bot, Router, types
from aiogram.filters import StateFilter
from aiogram.fsm.context import FSMContext
from aiogram.types import LabeledPrice
from sqlalchemy import select, update
from sqlalchemy.orm import joinedload

from app.client_bot.const import EMAIL_FOR_PAYMENT_RECEIPT, GATE_ENTRY_AMOUNT, OFFERTA_URL
from app.client_bot.user_interface.handlers.shop_choice_message import MainMenu
from app.client_bot.user_interface.states import GateInvite
from app.client_bot.user_interface.views.callbacks import Gate
from app.client_bot.user_interface.views.gate import get_gate_keyboard
from app.modules.common_slaves.wildberries.models import WBUserCabinet
from app.settings import settings
from app.utils.db.models import Invite, InviteStatus, User
from app.utils.db.passed_gate_reason import PassedGateReason
from app.utils.db.session_maker import get_async_session_maker

router = Router()
_sm = get_async_session_maker


def _normalize_invite_code(raw: str) -> str:
    """Trim, upper, keep dashes."""
    return raw.strip().upper()


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
    code = _normalize_invite_code(message.text)
    if not code:
        _ = await bot.send_message(
            message.chat.id,
            "Введите непустой инвайт-код.",
            reply_markup=get_gate_keyboard(),
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
            _ = await bot.send_message(
                chat_id,
                "Ошибка: пользователь не найден. Попробуйте /start.",
                reply_markup=get_gate_keyboard(),
            )
            return

        # Invite by code
        invite_stmt = select(Invite).where(Invite.code == code)
        invite_result = await session.execute(invite_stmt)
        invite = invite_result.scalar_one_or_none()

        if invite is None:
            _ = await bot.send_message(
                chat_id,
                "Неверный инвайт-код.",
                reply_markup=get_gate_keyboard(),
            )
            return

        if invite.status != InviteStatus.ACTIVE:
            _ = await bot.send_message(
                chat_id,
                "Этот инвайт уже использован или отозван.",
                reply_markup=get_gate_keyboard(),
            )
            return

        if invite.expires_at < now_utc:
            invite.status = InviteStatus.EXPIRED
            session.add(invite)
            await session.commit()
            _ = await bot.send_message(
                chat_id,
                "Срок действия инвайт-кода истёк.",
                reply_markup=get_gate_keyboard(),
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
            _ = await bot.send_message(
                chat_id,
                "Этот инвайт уже использован или истёк.",
                reply_markup=get_gate_keyboard(),
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
    # Показать старт-меню (выбор магазина)
    async with _sm() as session:
        stmt = (
            select(User)
            .options(
                joinedload(User.wb_user_cabinets).joinedload(WBUserCabinet.wb_cabinet)
            )
            .where(User.user_telegram_id == telegram_id)
        )
        res = await session.execute(stmt)
        user_with_cabinets: User | None = res.unique().scalar_one_or_none()
    cabinets = (
        list(user_with_cabinets.wb_user_cabinets)
        if user_with_cabinets is not None
        else []
    )
    await MainMenu(bot, chat_id)()


@router.callback_query(Gate.filter(F.action == "pay_entry_amount"))
async def gate_pay_entry_amount(callback: types.CallbackQuery, bot: Bot) -> None:
    """Отправка invoice на входной платёж (сумма GATE_ENTRY_AMOUNT)."""
    if callback.message is None:
        return
    user_telegram_id = callback.from_user.id
    payload = json.dumps({"target": "user", "gate_entry": True})
    provider_token = settings.YOOKASSA_TOKEN
    provider_data = json.dumps(
        {
            "receipt": {
                "items": [
                    {
                        "description": "Входной платёж",
                        "quantity": "1",
                        "amount": {"value": GATE_ENTRY_AMOUNT, "currency": "RUB"},
                        "vat_code": 1,
                    }
                ],
                "email": EMAIL_FOR_PAYMENT_RECEIPT,
            }
        }
    )
    sum_kopecks = GATE_ENTRY_AMOUNT * 100
    prices = [
        LabeledPrice(label=f"Входной платёж {GATE_ENTRY_AMOUNT} ₽", amount=sum_kopecks)
    ]
    _ = await bot.send_invoice(
        user_telegram_id,
        title=f"Входной платёж {GATE_ENTRY_AMOUNT} ₽",
        description=f"Входной платёж {GATE_ENTRY_AMOUNT} ₽ зачисляется на баланс пользователя.",
        provider_data=provider_data,
        payload=payload,
        provider_token=provider_token,
        currency="RUB",
        prices=prices,
    )



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