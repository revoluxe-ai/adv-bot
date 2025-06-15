import asyncio
import datetime
import json
import logging

import aiogram
from aiogram import Router, types
from aiogram.filters import StateFilter
from aiogram.fsm.context import FSMContext
from aiogram.types import LabeledPrice
from sqlalchemy import select, func

from app.client_bot import const
from app.client_bot.const import EMAIL_FOR_PAYMENT_RECEIPT
from app.client_bot.user_interface import states
from app.client_bot.user_interface.views import callbacks
from app.modules.balance_manager.balance_service import (
    get_cabinet_balance,
    process_payment_with_bonus,
)
from app.modules.common_slaves.wildberries.models import WBCabinet, WBUserCabinet
from app.modules.shop_menu.message import ShopMenu
from app.payments.db.models import Payment
from app.settings import settings
from app.utils.db.models import User
from app.utils.db.session_maker import get_async_session_maker
from . import messages

logger = logging.getLogger(__name__)

TEST_SUBSCRIBE_COST = 99

sm = get_async_session_maker

router = Router()


@router.callback_query(callbacks.AddBalance.filter())
async def add_balance(
    callback: types.CallbackQuery,
    bot: aiogram.Bot,
    callback_data: callbacks.AddBalance,
    state: FSMContext,
) -> None:
    wb_cabinet_original_id = callback_data.wb_cabinet_original_id
    await state.update_data(
        wb_cabinet_original_id_for_add_balance=wb_cabinet_original_id
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
        "(https://docs.google.com/document/d/12oK7Z9f8vrRik9_kjjtN1B3t4QFex6RxBCbyQwzBJ4o/)"
        " и [пользовательским соглашением]"
        "(https://docs.google.com/document/d/1fxmcwfZUwoHqDUQenHq31eHjcg641vef1ZYx3Mxqg40/)"
    )

    await bot.send_message(
        chat_id, text, reply_markup=keyboard, parse_mode="MarkdownV2"
    )

    return


@router.callback_query(callbacks.ConfirmAddBalance.filter())
async def confirm_add_balance(
    callback: types.CallbackQuery,
    callback_data: callbacks.ConfirmAddBalance,
    state: FSMContext,
    bot: aiogram.Bot,
) -> None:
    wb_cabinet_original_id: int = callback_data.wb_cabinet_original_id
    await state.set_state(states.AddBalance.awaiting_amount)
    result = await get_cabinet_balance(wb_cabinet_original_id)
    cabinet_balance: int | float = result[0]
    cabinet_bonus: int | float = result[1]
    # Пока оставляем расчет master_sum как был
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
    assert callback.message is not None
    # Передаем текущий баланс и бонусы в сообщение
    await messages.WaitingForAmount(
        bot,
        callback.message.chat.id,
        master_sum,
        current_balance=cabinet_balance,
        current_bonus=cabinet_bonus,
    )()


@router.message(StateFilter(states.AddBalance.awaiting_amount))
async def waiting_for_amount(
    message: types.Message, state: FSMContext, bot: aiogram.Bot
) -> None:
    assert message.text is not None
    amount: str = message.text
    min_sum = const.min_sum
    if not amount.isdigit():
        await message.answer(f"Введите сумму (число) от {min_sum} рублей")
        return
    amount_int: int = int(amount)
    if amount_int < const.MIN_SUM:
        await message.answer(f"Введите сумму (число) от {min_sum}")
        return
    state_data = await state.get_data()
    wb_cabinet_original_id = state_data["wb_cabinet_original_id_for_add_balance"]

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

    user_telegram_id = message.chat.id
    sum_for_adding = int(amount) * 100
    prices = [LabeledPrice(label=f"Пополнение баланса", amount=str(sum_for_adding))]
    await bot.send_invoice(
        user_telegram_id,
        title="Подписка на бота",
        description=f"Пополнение баланса магазина \n" f" на {amount} рублей. \n",
        provider_data=provider_data,
        payload=payload,
        provider_token=provider_token,
        currency="RUB",
        prices=prices,
    )
    await state.set_state()


@router.pre_checkout_query()
async def pre_checkout_query_handler(
    pre_checkout_query: types.PreCheckoutQuery, bot: aiogram.Bot
) -> None:
    await bot.answer_pre_checkout_query(pre_checkout_query.id, ok=True)


@router.message(aiogram.F.successful_payment)
async def successful_payment_handler(
    message: types.Message, state: FSMContext, bot: aiogram.Bot
) -> None:
    successful_payment = message.successful_payment
    assert successful_payment is not None
    cost = successful_payment.total_amount / 100
    state_data = await state.get_data()
    wb_cabinet_original_id = state_data["wb_cabinet_original_id_for_add_balance"]
    # Получаем ID пользователя из базы
    async with sm() as session:
        stmt = select(User.id).where(User.user_telegram_id == message.chat.id)
        user_result = await session.execute(stmt)
        user_id = user_result.scalar_one_or_none()

        if not user_id:
            logger.error(f"Пользователь с telegram_id {message.chat.id} не найден")
            await message.answer(
                "Произошла ошибка при обработке платежа. Обратитесь в поддержку."
            )
            return

    # Используем новый сервис для обработки платежа
    balance_payment, bonus_payment, amount, bonus_amount = (
        await process_payment_with_bonus(
            user_id=user_id,
            cabinet_id=wb_cabinet_original_id,
            amount=float(cost),
            bonus_percent=0,  # Пока без бонусов
            description=f"Пополнение баланса через Telegram",
        )
    )

    await messages.BalanceUpdated(bot, message.chat.id, amount, bonus_amount)()

    # Переходим к меню магазина
    async with sm() as session:
        stmt = (
            select(WBUserCabinet.id)
            .join(WBUserCabinet.wb_cabinet)
            .where(WBCabinet.id == wb_cabinet_original_id)
        )
        wb_user_cabinet_id_result = await session.execute(stmt)
        wb_user_cabinet_id = wb_user_cabinet_id_result.scalar_one()

    logger.debug(f"wb_user_cabinet_id: {wb_user_cabinet_id}")
    await asyncio.sleep(1)
    await ShopMenu(bot, message.chat.id, state, wb_user_cabinet_id)()
