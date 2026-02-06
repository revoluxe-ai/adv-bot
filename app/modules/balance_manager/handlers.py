import asyncio
import datetime
from datetime import UTC, date
import json
import logging
from uuid import uuid4

# pyright: reportUnusedCallResult=false
import aiogram
from aiogram import F, Router, types
from aiogram.filters import StateFilter
from aiogram.fsm.context import FSMContext
from aiogram.types import LabeledPrice
from sqlalchemy import func, select
from sqlalchemy.orm import joinedload

from app.client_bot import const
from app.client_bot.const import (
    EMAIL_FOR_PAYMENT_RECEIPT,
    GATE_ENTRY_AMOUNT,
    OFFERTA_URL,
)
from app.client_bot.user_interface import states
from app.client_bot.user_interface.handlers.shop_choice_message import ShopChoice
from app.client_bot.user_interface.views import callbacks
from app.modules.balance_manager.balance_service import (
    get_cabinet_balance,
    process_payment_with_bonus,
    transfer_user_balance_to_cabinet,
)
from app.modules.balance_manager.exceptions import InsufficientBalanceError
from app.modules.balance_manager.user_balance_service import (
    get_user_balance,
    process_user_payment_with_bonus,
)
from app.modules.common_slaves.wildberries.models import WBUserCabinet
from app.modules.shop_menu.message import ShopMenu
from app.payments.db.models import Payment
from app.settings import settings
from app.utils.db.models import User
from app.utils.db.passed_gate_reason import PassedGateReason
from app.utils.db.session_maker import get_async_session_maker
from . import messages
from ..billing.event_manager.event_manager import BillingEventManager
from ..common_slaves.wildberries.models.wb_cabinet import WBCabinet

logger = logging.getLogger(__name__)

TEST_SUBSCRIBE_COST = 99

sm = get_async_session_maker

router = Router()
BALANCE_TOPUP_CORRELATION_KEY = "balance_topup_correlation_id"
LOST_CONTEXT_MESSAGE = (
    "Потерян контекст оплаты. Нажмите на /start, зайдите в магазин и выполните оплату снова. Извините за неудобства!"
)

async def _get_balance_event_context(
    state: FSMContext,
) -> tuple[str | None, int | None]:
    data = await state.get_data()
    return (
        data.get(BALANCE_TOPUP_CORRELATION_KEY),
        data.get("wb_cabinet_original_id_for_add_balance"),
    )


async def _handle_lost_context(
    bot: aiogram.Bot,
    chat_id: int,
    billing_event_manager: BillingEventManager,
    where: str,
    notify_user: bool = True,
) -> None:
    await billing_event_manager.emit_add_balance_context_lost(
        user_telegram_id=chat_id,
        reason=where,
    )
    if notify_user:
        await bot.send_message(chat_id, LOST_CONTEXT_MESSAGE)



@router.callback_query(callbacks.AddBalance.filter())
async def add_balance(
    callback: types.CallbackQuery,
    bot: aiogram.Bot,
    callback_data: callbacks.AddBalance,
    state: FSMContext,
    billing_event_manager: BillingEventManager,
) -> None:
    wb_cabinet_original_id = callback_data.wb_cabinet_original_id
    correlation_id = str(uuid4())
    await state.update_data(
        wb_cabinet_original_id_for_add_balance=wb_cabinet_original_id,
        balance_topup_correlation_id=correlation_id,
    )

    assert callback.message is not None
    chat_id = callback.message.chat.id
    await billing_event_manager.emit_add_balance_click(
        user_telegram_id=chat_id,
        wb_cabinet_id=wb_cabinet_original_id,
        correlation_id=correlation_id,
    )

    keyboard = types.InlineKeyboardMarkup(
        inline_keyboard=[
            [
                types.InlineKeyboardButton(
                    text="Подтвердить✅",
                    callback_data=callbacks.ConfirmAddBalance(
                        wb_cabinet_original_id=wb_cabinet_original_id
                    ).pack(),
                )
            ]
        ]
    )
    assert callback.message is not None
    chat_id = callback.message.chat.id

    text = (
        "Оплачивая сервис вы соглашаетесь с  [публичной офертой]"
        f"({OFFERTA_URL})"
        " и [пользовательским соглашением]"
        "(https://docs.google.com/document/d/1fyxx_X25WSZ7cridzbCTFTBXqzqltpla1ew4XOAPo7g/edit?usp=sharing)"
    )

    await bot.send_message(
        chat_id, text, reply_markup=keyboard, parse_mode="MarkdownV2"
    )
    await billing_event_manager.emit_offerta_shown(
        user_telegram_id=chat_id,
        wb_cabinet_id=wb_cabinet_original_id,
        correlation_id=correlation_id,
    )

    return


@router.callback_query(callbacks.UserBalanceMenu.filter())
async def show_user_balance_menu(
    callback: types.CallbackQuery,
    bot: aiogram.Bot,
) -> None:
    """Экран «Мой баланс»: баланс, бонусы и кнопка пополнения."""
    assert callback.message is not None
    chat_id = callback.message.chat.id
    try:
        balance, bonus = await get_user_balance(chat_id)
    except Exception:
        balance, bonus = 0.0, 0.0
    total = balance + bonus
    text = (
        f"💰 <b>Личный баланс</b>: {balance:.0f} руб.\n"
        f"🎁 <b>Бонусы</b>: {bonus:.0f} руб.\n"
        f"📊 <b>Итого</b>: {total:.0f} руб.\n\n"
        "Пополнить личный баланс можно кнопкой ниже."
    )
    keyboard = types.InlineKeyboardMarkup(
        inline_keyboard=[
            [
                types.InlineKeyboardButton(
                    text="Пополнить баланс",
                    callback_data=callbacks.AddUserBalance().pack(),
                )
            ],
            [
                types.InlineKeyboardButton(
                    text="В главное меню",
                    callback_data=callbacks.Start().pack(),
                )
            ],
        ]
    )
    await bot.send_message(
        chat_id,
        text,
        reply_markup=keyboard,
        parse_mode="HTML",
    )


@router.callback_query(callbacks.AddUserBalance.filter())
async def add_user_balance_callback(
    callback: types.CallbackQuery,
    bot: aiogram.Bot,
    state: FSMContext,
    billing_event_manager: BillingEventManager,
) -> None:
    """Пополнение личного баланса пользователя: оферта и подтверждение."""
    correlation_id = str(uuid4())
    await state.update_data(
        balance_topup_correlation_id=correlation_id,
        balance_topup_target="user",
    )
    assert callback.message is not None
    chat_id = callback.message.chat.id
    await billing_event_manager.emit_add_balance_click(
        user_telegram_id=chat_id,
        wb_cabinet_id=None,
        correlation_id=correlation_id,
    )
    keyboard = types.InlineKeyboardMarkup(
        inline_keyboard=[
            [
                types.InlineKeyboardButton(
                    text="Подтвердить✅",
                    callback_data=callbacks.ConfirmAddUserBalance().pack(),
                )
            ]
        ]
    )
    text = (
        "Пополнение личного баланса. Оплачивая сервис вы соглашаетесь с "
        f'<a href="{OFFERTA_URL}">'
        "публичной офертой</a> и "
        '<a href="https://docs.google.com/document/d/1fyxx_X25WSZ7cridzbCTFTBXqzqltpla1ew4XOAPo7g/edit?usp=sharing">'
        "пользовательским соглашением</a>"
    )
    await bot.send_message(
        chat_id, text, reply_markup=keyboard, parse_mode=aiogram.enums.ParseMode.HTML
    )
    await billing_event_manager.emit_offerta_shown(
        user_telegram_id=chat_id,
        wb_cabinet_id=None,
        correlation_id=correlation_id,
    )


@router.callback_query(callbacks.ConfirmAddUserBalance.filter())
async def confirm_add_user_balance(
    callback: types.CallbackQuery,
    state: FSMContext,
    bot: aiogram.Bot,
    billing_event_manager: BillingEventManager,
) -> None:
    """Подтверждение пополнения личного баланса: переход к вводу суммы."""
    if callback.message is None:
        return
    chat_id = callback.message.chat.id
    data = await state.get_data()
    correlation_id = data.get(BALANCE_TOPUP_CORRELATION_KEY) or str(uuid4())
    await state.update_data(balance_topup_correlation_id=correlation_id)
    await billing_event_manager.emit_offerta_confirm_click(
        user_telegram_id=chat_id,
        wb_cabinet_id=None,
        correlation_id=correlation_id,
    )
    await state.set_state(states.AddUserBalance.awaiting_amount)
    try:
        user_balance, user_bonus = await get_user_balance(chat_id)
    except Exception:
        user_balance, user_bonus = 0.0, 0.0
    time_from = "2024-07-01 00:00:00"
    time_from_datetime = datetime.datetime.strptime(time_from, "%Y-%m-%d %H:%M:%S")
    async with sm() as session:
        stmt = select(func.max(Payment.amount)).where(
            Payment.timestamp > time_from_datetime
        )
        result_max_amount = await session.execute(stmt)
        max_amount = result_max_amount.scalar()
    master_sum = (max_amount or 50) * 2
    await messages.WaitingForAmount(
        bot,
        chat_id,
        float(master_sum),
        current_balance=user_balance,
        current_bonus=user_bonus,
    )()
    await billing_event_manager.emit_amount_prompt_shown(
        user_telegram_id=chat_id,
        wb_cabinet_id=None,
        correlation_id=correlation_id,
    )


@router.message(StateFilter(states.AddUserBalance.awaiting_amount), F.text)
async def waiting_for_user_amount(
    message: types.Message,
    state: FSMContext,
    bot: aiogram.Bot,
    billing_event_manager: BillingEventManager,
) -> None:
    """Ввод суммы пополнения личного баланса и отправка invoice с target=user."""
    assert message.text is not None
    amount_str = message.text.strip()
    min_sum = const.min_sum
    user_telegram_id = message.chat.id
    data = await state.get_data()
    correlation_id = data.get(BALANCE_TOPUP_CORRELATION_KEY) or str(uuid4())

    if not amount_str.isdigit():
        await billing_event_manager.emit_amount_input(
            user_telegram_id=user_telegram_id,
            wb_cabinet_id=None,
            amount_text=amount_str,
            is_valid=False,
            parsed_amount=None,
            correlation_id=correlation_id,
        )
        await message.answer(f"Введите сумму (число) от {min_sum} рублей")
        return

    amount_int = int(amount_str)
    if amount_int < const.MIN_SUM:
        await billing_event_manager.emit_amount_input(
            user_telegram_id=user_telegram_id,
            wb_cabinet_id=None,
            amount_text=amount_str,
            is_valid=False,
            parsed_amount=float(amount_int),
            correlation_id=correlation_id,
        )
        await message.answer(f"Введите сумму (число) от {min_sum}")
        return

    await billing_event_manager.emit_amount_input(
        user_telegram_id=user_telegram_id,
        wb_cabinet_id=None,
        amount_text=amount_str,
        is_valid=True,
        parsed_amount=float(amount_int),
        correlation_id=correlation_id,
    )

    payload = json.dumps({"target": "user"})
    provider_token = settings.YOOKASSA_TOKEN
    provider_data = json.dumps(
        {
            "receipt": {
                "items": [
                    {
                        "description": "Пополнение личного баланса",
                        "quantity": "1",
                        "amount": {"value": amount_int, "currency": "RUB"},
                        "vat_code": 1,
                    }
                ],
                "email": EMAIL_FOR_PAYMENT_RECEIPT,
            }
        }
    )
    sum_kopecks = amount_int * 100
    prices = [
        LabeledPrice(label="Пополнение личного баланса", amount=sum_kopecks)
    ]
    await bot.send_invoice(
        user_telegram_id,
        title="Пополнение личного баланса",
        description=f"Пополнение личного баланса на {amount_int} руб.",
        provider_data=provider_data,
        payload=payload,
        provider_token=provider_token,
        currency="RUB",
        prices=prices,
    )
    await billing_event_manager.emit_invoice_sent(
        user_telegram_id=user_telegram_id,
        wb_cabinet_id=None,
        amount=float(amount_int),
        currency="RUB",
        payload={"invoice_payload": payload},
        correlation_id=correlation_id,
    )
    await state.set_state()


@router.callback_query(callbacks.ConfirmAddBalance.filter())
async def confirm_add_balance(
    callback: types.CallbackQuery,
    callback_data: callbacks.ConfirmAddBalance,
    state: FSMContext,
    bot: aiogram.Bot,
    billing_event_manager: BillingEventManager,
) -> None:
    if callback.message is None:
        return
    chat_id = callback.message.chat.id
    correlation_id, _ = await _get_balance_event_context(state)
    if correlation_id is None:
        await _handle_lost_context(
            bot,
            chat_id,
            billing_event_manager,
            where="confirm_add_balance",
            notify_user=False,
        )
        correlation_id = str(uuid4())
        await state.update_data(
            balance_topup_correlation_id=correlation_id,
            wb_cabinet_original_id_for_add_balance=callback_data.wb_cabinet_original_id,
        )
    assert callback.message is not None

    await billing_event_manager.emit_offerta_confirm_click(
        user_telegram_id=chat_id,
        wb_cabinet_id=callback_data.wb_cabinet_original_id,
        correlation_id=correlation_id,
    )
    wb_cabinet_original_id: int = callback_data.wb_cabinet_original_id
    await state.set_state(states.AddBalance.awaiting_payment_method)
    keyboard = types.InlineKeyboardMarkup(
        inline_keyboard=[
            [
                types.InlineKeyboardButton(
                    text="Платежная система Yookassa",
                    callback_data=callbacks.AddBalanceByCard(
                        wb_cabinet_original_id=wb_cabinet_original_id
                    ).pack(),
                )
            ],
            [
                types.InlineKeyboardButton(
                    text="С личного баланса",
                    callback_data=callbacks.AddBalanceFromUserBalance(
                        wb_cabinet_original_id=wb_cabinet_original_id
                    ).pack(),
                )
            ],
        ]
    )
    await bot.send_message(
        chat_id,
        "Как пополнить баланс кабинета?",
        reply_markup=keyboard,
    )


async def _send_waiting_for_amount_cabinet(
    bot: aiogram.Bot,
    chat_id: int,
    wb_cabinet_original_id: int,
    state: FSMContext,
    billing_event_manager: BillingEventManager,
) -> None:
    """Отправляет сообщение «Введите сумму» с балансом кабинета (для оплаты картой)."""
    result = await get_cabinet_balance(wb_cabinet_original_id)
    cabinet_balance: int | float = result[0]
    cabinet_bonus: int | float = result[1]
    time_from = "2024-07-01 00:00:00"
    time_from_datetime = datetime.datetime.strptime(time_from, "%Y-%m-%d %H:%M:%S")
    async with sm() as session:
        stmt = select(func.max(Payment.amount)).where(
            Payment.timestamp > time_from_datetime
        )
        result_max_amount = await session.execute(stmt)
        max_amount = result_max_amount.scalar()
        if not max_amount:
            max_amount = 50
        master_sum = max_amount * 2
    await state.update_data(master_sum=master_sum)
    correlation_id, _ = await _get_balance_event_context(state)
    await messages.WaitingForAmount(
        bot,
        chat_id,
        master_sum,
        current_balance=cabinet_balance,
        current_bonus=cabinet_bonus,
    )()
    if correlation_id:
        await billing_event_manager.emit_amount_prompt_shown(
            user_telegram_id=chat_id,
            wb_cabinet_id=wb_cabinet_original_id,
            correlation_id=correlation_id,
        )


@router.callback_query(callbacks.AddBalanceByCard.filter())
async def add_balance_by_card(
    callback: types.CallbackQuery,
    callback_data: callbacks.AddBalanceByCard,
    state: FSMContext,
    bot: aiogram.Bot,
    billing_event_manager: BillingEventManager,
) -> None:
    """Выбор «Оплатить картой»: переход к вводу суммы и инвойсу."""
    if callback.message is None:
        return
    chat_id = callback.message.chat.id
    wb_cabinet_original_id = callback_data.wb_cabinet_original_id
    await state.update_data(add_balance_source="card")
    await state.set_state(states.AddBalance.awaiting_amount)
    await _send_waiting_for_amount_cabinet(
        bot, chat_id, wb_cabinet_original_id, state, billing_event_manager
    )


@router.callback_query(callbacks.AddBalanceFromUserBalance.filter())
async def add_balance_from_user_balance(
    callback: types.CallbackQuery,
    callback_data: callbacks.AddBalanceFromUserBalance,
    state: FSMContext,
    bot: aiogram.Bot,
) -> None:
    """Выбор «С личного баланса»: переход к вводу суммы для перевода."""
    if callback.message is None:
        return
    chat_id = callback.message.chat.id
    wb_cabinet_original_id = callback_data.wb_cabinet_original_id
    await state.update_data(
        add_balance_source="user_balance",
        wb_cabinet_original_id_for_add_balance=wb_cabinet_original_id,
    )
    await state.set_state(states.AddBalance.awaiting_amount)
    try:
        user_balance, _ = await get_user_balance(chat_id)
        available = user_balance
    except Exception:
        available = 0.0
    text = (
        f"Введите сумму для перевода с личного баланса на кабинет.\n"
        f"Доступно (баланс): {available:.0f} руб."
    )
    await bot.send_message(chat_id, text)


@router.message(StateFilter(states.AddBalance.awaiting_amount), F.text)
async def waiting_for_amount(
    message: types.Message,
    state: FSMContext,
    bot: aiogram.Bot,
    billing_event_manager: BillingEventManager,
) -> None:
    assert message.text is not None
    amount: str = message.text
    min_sum = const.min_sum
    data = await state.get_data()
    add_balance_source = data.get("add_balance_source", "card")
    correlation_id, wb_cabinet_original_id = await _get_balance_event_context(state)
    user_telegram_id = message.chat.id
    if wb_cabinet_original_id is None:
        await _handle_lost_context(
            bot, user_telegram_id, billing_event_manager, where="waiting_for_amount"
        )
        await state.set_state()
        return

    if not amount.isdigit():
        if add_balance_source == "user_balance":
            await message.answer(f"Введите сумму (число) от {min_sum} рублей")
        else:
            await billing_event_manager.emit_amount_input(
                user_telegram_id=user_telegram_id,
                wb_cabinet_id=wb_cabinet_original_id,
                amount_text=amount,
                is_valid=False,
                parsed_amount=None,
                correlation_id=correlation_id,
            )
            await message.answer(f"Введите сумму (число) от {min_sum} рублей")
        return

    amount_int: int = int(amount)
    if amount_int < const.MIN_SUM:
        if add_balance_source == "user_balance":
            await message.answer(f"Введите сумму (число) от {min_sum}")
        else:
            await billing_event_manager.emit_amount_input(
                user_telegram_id=user_telegram_id,
                wb_cabinet_id=wb_cabinet_original_id,
                amount_text=amount,
                is_valid=False,
                parsed_amount=float(amount_int),
                correlation_id=correlation_id,
            )
            await message.answer(f"Введите сумму (число) от {min_sum}")
        return

    if add_balance_source == "user_balance":
        try:
            user_balance, user_bonus = await get_user_balance(user_telegram_id)
            available = user_balance + user_bonus
        except Exception:
            available = 0.0
        if amount_int > available:
            await message.answer("Недостаточно средств на личном балансе.")
            return
        try:
            await transfer_user_balance_to_cabinet(
                user_telegram_id=user_telegram_id,
                cabinet_id=wb_cabinet_original_id,
                amount=float(amount_int),
            )
        except InsufficientBalanceError:
            await message.answer("Недостаточно средств на личном балансе.")
            return
        await state.set_state()
        await messages.BalanceUpdated(bot, message.chat.id, float(amount_int), 0.0)()
        async with sm() as session:
            stmt = (
                select(WBUserCabinet.id)
                .join(WBUserCabinet.wb_cabinet)
                .where(WBCabinet.id == wb_cabinet_original_id)
            )
            wb_user_cabinet_id_result = await session.execute(stmt)
            wb_user_cabinet_id: int | None = (
                wb_user_cabinet_id_result.scalars().first()
            )
        if wb_user_cabinet_id is not None:
            await asyncio.sleep(1)
            await ShopMenu(bot, message.chat.id, state, wb_user_cabinet_id)()
        return

    await billing_event_manager.emit_amount_input(
        user_telegram_id=user_telegram_id,
        wb_cabinet_id=wb_cabinet_original_id,
        amount_text=amount,
        is_valid=True,
        parsed_amount=float(amount_int),
        correlation_id=correlation_id,
    )

    payload = json.dumps(
        {
            "wb_cabinet_original_id": wb_cabinet_original_id,
        }
    )

    provider_token = settings.YOOKASSA_TOKEN
    provider_data = json.dumps(
        {
            "receipt": {
                "items": [
                    {
                        "description": "Пополнение баланса",
                        "quantity": "1",
                        "amount": {"value": amount_int, "currency": "RUB"},
                        "vat_code": 1,
                    }
                ],
                "email": EMAIL_FOR_PAYMENT_RECEIPT,
            }
        }
    )

    sum_for_adding = int(amount) * 100
    prices = [LabeledPrice(label="Пополнение баланса", amount=str(sum_for_adding))] # pyright: ignore # noqa
    await bot.send_invoice(
        user_telegram_id,
        title="Подписка на бота",
        description=f"Пополнение баланса магазина \n на {amount} рублей. \n",
        provider_data=provider_data,
        payload=payload,
        provider_token=provider_token,
        currency="RUB",
        prices=prices,
    )
    await billing_event_manager.emit_invoice_sent(
        user_telegram_id=user_telegram_id,
        wb_cabinet_id=wb_cabinet_original_id,
        amount=float(amount_int),
        currency="RUB",
        payload={"invoice_payload": payload},
        correlation_id=correlation_id,
    )
    await state.set_state()


@router.pre_checkout_query()
async def pre_checkout_query_handler(
    pre_checkout_query: types.PreCheckoutQuery,
    bot: aiogram.Bot,
    state: FSMContext,
    billing_event_manager: BillingEventManager,
) -> None:
    correlation_id, wb_cabinet_original_id = await _get_balance_event_context(
        state
    )
    if correlation_id is None:
        await _handle_lost_context(
            bot,
            pre_checkout_query.from_user.id if pre_checkout_query.from_user else 0,
            billing_event_manager,
            where="pre_checkout_query",
            notify_user=False,
        )
        correlation_id = str(uuid4())
        await state.update_data(balance_topup_correlation_id=correlation_id)
    from_user_id = pre_checkout_query.from_user.id

    await bot.answer_pre_checkout_query(pre_checkout_query.id, ok=True)
    if wb_cabinet_original_id is not None:
        await billing_event_manager.emit_pre_checkout_ok(
            user_telegram_id=from_user_id,
            wb_cabinet_id=wb_cabinet_original_id,
            correlation_id=correlation_id,
        )


@router.message(aiogram.F.successful_payment)
async def successful_payment_handler(
    message: types.Message,
    state: FSMContext,
    bot: aiogram.Bot,
    billing_event_manager: BillingEventManager,
) -> None:
    successful_payment = message.successful_payment
    assert successful_payment is not None
    cost = successful_payment.total_amount / 100
    payload_str = getattr(successful_payment, "invoice_payload", None)
    parsed_payload: dict[str, object] = {}
    if payload_str:
        try:
            parsed_payload = json.loads(payload_str)
        except Exception:
            pass

    correlation_id, wb_cabinet_original_id = await _get_balance_event_context(state)
    if correlation_id is None:
        correlation_id = (
            getattr(successful_payment, "telegram_payment_charge_id", None)
            or str(uuid4())
        )
        await _handle_lost_context(
            bot,
            message.chat.id,
            billing_event_manager,
            where="successful_payment",
            notify_user=False,
        )

    # Ветка пополнения личного баланса пользователя
    if parsed_payload.get("target") == "user":
        async with sm() as session:
            stmt = (
                select(User)
                .where(User.user_telegram_id == message.chat.id)
                .options(joinedload(User.wb_user_cabinets))
            )
            result = await session.execute(stmt)
            user = result.unique().scalar_one_or_none()
        if not user:
            logger.error("Пользователь с telegram_id %s не найден", message.chat.id)
            await billing_event_manager.emit_error_event(
                where="successful_payment",
                error="user_not_found",
                user_telegram_id=message.chat.id,
                correlation_id=correlation_id,
            )
            await message.answer(
                "Произошла ошибка при обработке платежа. Обратитесь в поддержку."
            )
            return
        try:
                await billing_event_manager.emit_successful_payment_received(
                    user_id=user.id,
                    user_telegram_id=message.chat.id,
                    wb_cabinet_id=None,
                    amount=float(cost),
                    currency="RUB",
                    correlation_id=correlation_id,
                )
        except Exception as exc:  # pragma: no cover
            logger.exception(
                "Failed to emit successful_payment_received (user balance); continuing",
                exc_info=exc,
            )
        bonus_percent = 0.0
        if date.today() <= date(2025, 12, 31):
            bonus_percent = settings.BALANCE_TOPUP_BONUS_PERCENT
        try:
            (
                _,
                _,
                amount,
                bonus_amount,
            ) = await process_user_payment_with_bonus(
                user_telegram_id=message.chat.id,
                amount=float(cost),
                bonus_percent=bonus_percent,
                description="Пополнение личного баланса через Telegram",
            )
        except Exception as exc:
            logger.exception("process_user_payment_with_bonus failed", exc_info=exc)
            await message.answer(
                "Произошла ошибка при начислении. Обратитесь в поддержку."
            )
            return
        try:
                await billing_event_manager.emit_balance_topup_applied(
                    user_id=user.id,
                    user_telegram_id=message.chat.id,
                    wb_cabinet_id=None,
                    amount=amount,
                    bonus_amount=bonus_amount,
                    correlation_id=correlation_id,
                )
        except Exception as exc:  # pragma: no cover
            logger.exception(
                "Failed to emit balance_topup_applied (user); continuing",
                exc_info=exc,
            )
        if parsed_payload.get("gate_entry") is True and cost == float(GATE_ENTRY_AMOUNT):
            async with sm() as session:
                stmt = select(User).where(User.user_telegram_id == message.chat.id)
                result = await session.execute(stmt)
                gate_user = result.scalar_one_or_none()
                if gate_user is not None:
                    gate_user.passed_gate = True
                    gate_user.passed_gate_reason = PassedGateReason.BALANCE_TOP_UP
                    now_utc = datetime.datetime.now(UTC).replace(tzinfo=None)
                    gate_user.passed_gate_at = now_utc
                    session.add(gate_user)
                    await session.commit()
            await message.answer("Оплата получена. Доступ открыт.")
        await messages.BalanceUpdated(bot, message.chat.id, amount, bonus_amount)()
        await ShopChoice(bot, message.chat.id, user.wb_user_cabinets)()
        return

    # Ветка пополнения баланса кабинета
    if wb_cabinet_original_id is None and parsed_payload:
        cab_id_raw = parsed_payload.get("wb_cabinet_original_id")
        if isinstance(cab_id_raw, int | str):
            try:
                wb_cabinet_original_id = int(cab_id_raw)
            except (TypeError, ValueError):
                pass
    if wb_cabinet_original_id is None:
        await _handle_lost_context(
            bot,
            message.chat.id,
            billing_event_manager,
            where="successful_payment",
        )
        return

    async with sm() as session:
        stmt = select(User.id).where(User.user_telegram_id == message.chat.id)
        user_result = await session.execute(stmt)
        user_id = user_result.scalar_one_or_none()

        if not user_id:
            logger.error("Пользователь с telegram_id %s не найден", message.chat.id)
            await billing_event_manager.emit_error_event(
                where="successful_payment",
                error="user_not_found",
                user_telegram_id=message.chat.id,
                correlation_id=correlation_id,
            )
            await message.answer(
                "Произошла ошибка при обработке платежа. Обратитесь в поддержку."
            )
            return

    try:
        await billing_event_manager.emit_successful_payment_received(
            user_id=user_id,
            user_telegram_id=message.chat.id,
            wb_cabinet_id=wb_cabinet_original_id,
            amount=float(cost),
            currency="RUB",
            correlation_id=correlation_id,
        )
    except Exception as exc:  # pragma: no cover - logging/error handling path
        logger.exception(
            "Failed to emit successful_payment_received event; "
            "continuing with balance update",
            exc_info=exc,
        )

    bonus_percent = 0.0
    if date.today() <= date(2025, 12, 31):
        bonus_percent = settings.BALANCE_TOPUP_BONUS_PERCENT

    (
        _,
        _,
        amount,
        bonus_amount,
    ) = await process_payment_with_bonus(
        user_id=user_id,
        cabinet_id=wb_cabinet_original_id,
        amount=float(cost),
        bonus_percent=bonus_percent,
        description="Пополнение баланса через Telegram",
    )

    try:
        await billing_event_manager.emit_balance_topup_applied(
            user_id=user_id,
            user_telegram_id=message.chat.id,
            wb_cabinet_id=wb_cabinet_original_id,
            amount=amount,
            bonus_amount=bonus_amount,
            correlation_id=correlation_id,
        )
    except Exception as exc:  # pragma: no cover - logging/error handling path
        logger.exception(
            "Failed to emit balance_topup_applied event; continuing",
            exc_info=exc,
        )

    await messages.BalanceUpdated(bot, message.chat.id, amount, bonus_amount)()

    async with sm() as session:
        stmt = (
            select(WBUserCabinet.id)
            .join(WBUserCabinet.wb_cabinet)
            .where(WBCabinet.id == wb_cabinet_original_id)
        )
        wb_user_cabinet_id_result = await session.execute(stmt)
        wb_user_cabinet_id: int | None = wb_user_cabinet_id_result.scalars().first()
    if wb_user_cabinet_id is None:
        raise ValueError("Кабинет не найден")

    logger.debug("wb_user_cabinet_id: %s", wb_user_cabinet_id)
    await asyncio.sleep(1)
    await ShopMenu(bot, message.chat.id, state, wb_user_cabinet_id)()
