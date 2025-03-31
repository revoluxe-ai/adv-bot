import asyncio
import json
import datetime
import aiogram
from aiogram import Router, types
from aiogram.filters import StateFilter
from aiogram.fsm.context import FSMContext
from aiogram.types import LabeledPrice
from sqlalchemy import select, func
import logging
from app.client_bot import const
from app.client_bot.const import EMAIL_FOR_PAYMENT_RECEIPT
from app.client_bot.user_interface import states
from app.client_bot.user_interface.views import callbacks, messages
from app.modules.balance_manager.balance_service import get_cabinet_balance, process_payment_with_bonus
from app.modules.balance_manager.exceptions import CabinetNotFoundError, UserNotFoundError
from app.modules.common_slaves.wildberries.models import WBCabinet, WBUserCabinet
from app.modules.shop_menu.message import ShopMenu
from app.payments.db.models import Payment
from app.utils.db.models import User
from app.utils.db.session_maker import get_async_session_maker
from app.settings import settings


logger = logging.getLogger(__name__)

TEST_SUBSCRIBE_COST = 99

sm = get_async_session_maker

router = Router()


@router.callback_query(callbacks.AddBalance.filter())
async def add_balance(callback: types.CallbackQuery,
                      callback_data: callbacks.AddBalance,
                      state: FSMContext,
                      bot: aiogram.Bot):

    wb_cabinet_original_id = callback_data.wb_cabinet_original_id
    await state.update_data(wb_cabinet_original_id_for_add_balance=wb_cabinet_original_id)
    await state.set_state(states.AddBalance.awaiting_amount)
    cabinet_balance, cabinet_bonus = await get_cabinet_balance(wb_cabinet_original_id)

    # Пока оставляем расчет master_sum как был
    time_from = '2024-07-01 00:00:00'
    time_from_datetime = datetime.datetime.strptime(time_from, '%Y-%m-%d %H:%M:%S')
    async with sm() as session:
        stmt = select(func.max(Payment.amount)) \
            .where(Payment.timestamp > time_from_datetime)
        result = await session.execute(stmt)
        max_amount = result.scalar()
        if not max_amount:
            max_amount = 50
        master_sum = max_amount * 2

    await state.update_data(master_sum=master_sum)

    # Передаем текущий баланс и бонусы в сообщение
    await messages.WaitingForAmount(
        bot,
        callback.message.chat.id,
        master_sum,
        current_balance=cabinet_balance,
        current_bonus=cabinet_bonus
    )()


@router.message(StateFilter(states.AddBalance.awaiting_amount))
async def waiting_for_amount(message: types.Message, state: FSMContext, bot: aiogram.Bot):
    amount: str = message.text
    min_sum = const.min_sum
    if not amount.isdigit():
        await message.answer(f"Введите сумму (число) от {min_sum} рублей")
        return
    amount: int = int(amount)
    if amount < const.MIN_SUM:
        await message.answer(f"Введите сумму (число) от {min_sum}")
        return
    state_data = await state.get_data()
    wb_cabinet_original_id = state_data['wb_cabinet_original_id_for_add_balance']

    payload = json.dumps(
        {
            'wb_cabinet_original_id': wb_cabinet_original_id,
        }
    )

    provider_token = settings.YOOKASSA_TOKEN
    provider_data = json.dumps(
        {
            "receipt": {
                "items": [
                    {
                        "description": 'Пополнение баланса',
                        "quantity": "1",
                        "amount": {
                            "value": amount,
                            "currency": "RUB"
                        },
                        "vat_code": 1
                    }
                ],
                "email": EMAIL_FOR_PAYMENT_RECEIPT
            }
        }
    )

    user_telegram_id = message.chat.id
    sum_for_adding = amount * 100
    prices = [LabeledPrice(label=f'Пополнение баланса', amount=sum_for_adding)]
    await bot.send_invoice(
        user_telegram_id,
        title='Подписка на бота',
        description=(
            f"Пополнение баланса магазина \n"
            f" на {amount} рублей. \n"
        ),
        provider_data=provider_data,
        payload=payload,
        provider_token=provider_token,
        currency='RUB',
        prices=prices,
    )
    await state.set_state()


@router.pre_checkout_query()
async def pre_checkout_query_handler(pre_checkout_query: types.PreCheckoutQuery, bot: aiogram.Bot):
    await bot.answer_pre_checkout_query(pre_checkout_query.id, ok=True)


@router.message(aiogram.F.successful_payment)
async def successful_payment_handler(message: types.Message, state: FSMContext, bot: aiogram.Bot):
    successful_payment = message.successful_payment
    cost = successful_payment.total_amount / 100
    state_data = await state.get_data()
    wb_cabinet_original_id = state_data['wb_cabinet_original_id_for_add_balance']
    # Получаем ID пользователя из базы
    async with sm() as session:
        stmt = select(User.id).where(User.user_telegram_id == message.chat.id)
        user_result = await session.execute(stmt)
        user_id = user_result.scalar_one_or_none()

        if not user_id:
            logger.error(f"Пользователь с telegram_id {message.chat.id} не найден")
            await message.answer("Произошла ошибка при обработке платежа. Обратитесь в поддержку.")
            return

    # Используем новый сервис для обработки платежа
    balance_payment, bonus_payment, amount, bonus_amount = await process_payment_with_bonus(
        user_id=user_id,
        cabinet_id=wb_cabinet_original_id,
        amount=cost,
        bonus_percent=0,  # Пока без бонусов
        description=f"Пополнение баланса через Telegram"
    )

    await messages.BalanceUpdated(bot, message.chat.id, amount, bonus_amount)()

    # Переходим к меню магазина
    async with sm() as session:
        stmt = select(WBUserCabinet.id)\
                .join(WBUserCabinet.wb_cabinet)\
                .where(WBCabinet.id == wb_cabinet_original_id)
        wb_user_cabinet_id = await session.execute(stmt)
        wb_user_cabinet_id = wb_user_cabinet_id.scalars().first()

    logger.debug(f'wb_user_cabinet_id: {wb_user_cabinet_id}')
    await asyncio.sleep(1)
    await ShopMenu(bot, message.chat.id, state, wb_user_cabinet_id)()
