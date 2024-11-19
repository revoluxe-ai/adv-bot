import asyncio
import json
from datetime import timedelta
import datetime
import aiogram
from aiogram import Router, types
from aiogram.filters import StateFilter
from aiogram.fsm.context import FSMContext
from aiogram.types import LabeledPrice
from sqlalchemy import select, and_, func
import logging
from app.admin_bot.sender import sender_manager
from app.client_bot.const import EMAIL_FOR_PAYMENT_RECEIPT
from app.client_bot.user_interface import states
from app.client_bot.user_interface.handlers import start
from app.client_bot.user_interface.views import callbacks, messages
from app.modules.common_slaves.wildberries.models import WBCabinet, WBUserCabinet
from app.payments.db.models import Payment
from app.utils.db.models import User
from app.utils.db.session_maker import get_async_session_maker
from app.utils.suffixes import get_day_suffix
from python_modules import path_setting_funcs
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
    await callback.answer()
    wb_cabinet_original_id = callback_data.wb_cabinet_original_id
    await state.update_data(wb_cabinet_original_id_for_add_balance=wb_cabinet_original_id)
    await state.set_state(states.AddBalance.awaiting_amount)
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
    await messages.WaitingForAmount(bot, callback.message.chat.id, master_sum)()

@router.message(StateFilter(states.AddBalance.awaiting_amount))
async def waiting_for_amount(message: types.Message, state: FSMContext, bot: aiogram.Bot):
    text = message.text
    if '/start' in text:
        await start.start_registration(message, bot, state)
        return
    amount = message.text
    if not amount.isdigit():
        await message.answer("Введите сумму (число) от 10 000 рублей")
        return
    amount = int(amount)
    if amount < 10000:
        await message.answer("Введите сумму (число) от 10000")
        return
    state_data = await state.get_data()
    wb_cabinet_original_id = state_data['wb_cabinet_original_id_for_add_balance']

    payload = json.dumps(
        {
            'wb_cabinet_original_id': wb_cabinet_original_id,
        }
    )

    path_setting = path_setting_funcs.get_setting_path()
    provider_token = path_setting_funcs.get_document_by_key_name(path_setting, 'yookassa_token')

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
    prices = [LabeledPrice(label=f'Пополнение баланса', amount=amount * 100)]
    await bot.send_invoice(
        user_telegram_id,
        title='Подписка на бота',
        description=(
            f"Пополнение баланса магазина \n"
            f" на {amount} рублей. \n"
            f"После оплаты услуга считается оказанной, возврат средств не производится. \n\n"
            f"В случае проблем с оплатой свяжитесь с администратором бота @skyline360_1"
        ),
        provider_data=provider_data,
        payload=payload,
        provider_token=provider_token,
        currency='RUB',
        prices=prices,
    )
    await state.set_state(None)


@router.pre_checkout_query()
async def pre_checkout_query_handler(pre_checkout_query: types.PreCheckoutQuery, bot: aiogram.Bot):
    await bot.answer_pre_checkout_query(pre_checkout_query.id, ok=True)


@router.message(aiogram.F.successful_payment)
async def successful_payment_handler(message: types.Message, state: FSMContext, bot: aiogram.Bot):
    successful_payment = message.successful_payment
    cost = successful_payment.total_amount / 100

    """
Прайс:
- Работа одной кампании, подключенной к боту: 35 р/сутки
- Парсинг активных ключей для одной кампании (включается отдельной кнопой): 15 р/сутки
- Автоуправление ставкой: 25 р./сутки

        
🔥 Внимание! Только до {date_to}(завтра):

💰 Бонус 100 % от суммы пополнения!

🚀 При пополнении счета свыше мастер-суммы: бонус 300 % от суммы пополнения!

👍 Это делает его не только лучшим, но и самым выгодным решением для автоматизации рекламы на WB!

💼 Мастер-сумма (бонус 300%): {self.master_sum} рублей.

📩 Подробности у администратора бота: @skyline360_1 \n

Укажите сумму пополнения (не менее 100 рублей):"""

    # state_data = await state.get_data()
    # try:
    #     master_sum = state_data['master_sum']
    # except:
    #     async with sm() as session:
    #         time_from = '2024-07-22 00:00:00'
    #         time_from_datetime = datetime.datetime.strptime(time_from, '%Y-%m-%d %H:%M:%S')
    #         stmt = select(func.max(Payment.amount)) \
    #             .where(Payment.timestamp > time_from_datetime)
    #         result = await session.execute(stmt)
    #         max_amount = result.scalar()
    #         if not max_amount:
    #             max_amount = 50
    #         master_sum = max_amount * 2
    # if cost >= master_sum:
    #     bonus = cost
    # else:
    #     bonus = round(cost*0.3, 2)

    state_data = await state.get_data()
    wb_cabinet_original_id = state_data['wb_cabinet_original_id_for_add_balance']
    bonus = 0
    async with sm() as session:
        async with session.begin():
            stmt = select(User).where(User.user_telegram_id == message.chat.id)
            user = await session.execute(stmt)
            user = user.scalars().first()
            wb_cabinet = await session.execute(select(WBCabinet)\
                                               .filter(WBCabinet.id == wb_cabinet_original_id))
            wb_cabinet = wb_cabinet.scalars().first()
            if wb_cabinet.balance is None:
                wb_cabinet.balance = 0
            if wb_cabinet.bonus is None:
                wb_cabinet.bonus = 0
            wb_cabinet.balance += cost
            wb_cabinet.bonus += bonus
            payment = Payment(
                user=user,
                amount=cost,
                target='balance',
            )
            session.add(payment)
            await session.commit()
    await messages.BalanceUpdated(bot, message.chat.id, cost, bonus)()
    async with sm() as session:
        stmt = select(WBUserCabinet.id)\
        .join(WBUserCabinet.wb_cabinet)\
        .where(WBCabinet.id == wb_cabinet_original_id)
        wb_user_cabinet_id = await session.execute(stmt)
        wb_user_cabinet_id = wb_user_cabinet_id.scalars().first()
    logger.debug(f'wb_user_cabinet_id: {wb_user_cabinet_id}')
    await asyncio.sleep(1)
    await messages.ShopMenu(bot, message.chat.id, state, wb_user_cabinet_id)()