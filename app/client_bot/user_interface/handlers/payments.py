import json
from datetime import timedelta

from aiogram import Router
import aiogram
from aiogram import types
from aiogram.types import LabeledPrice, Message
from sqlalchemy import select
from app.admin_bot.sender import sender_manager
from app.client_bot.user_interface.views import callbacks, messages
import asyncio

from app.modules.common_slaves.wildberries.models import WBCabinet
from app.payments.db.models import Payment
from settings.settings_master import settings
from app.utils.suffixes import get_day_suffix
from app.utils.db.models import User
from app.utils.db.session_maker import get_async_session_maker
from python_modules import path_setting_funcs

TEST_SUBSCRIBE_COST = 99

sm = get_async_session_maker()

router = Router()


@router.callback_query(callbacks.OrderSubscribe.filter())
async def order_subscribe(callback: types.CallbackQuery, callback_data: callbacks.OrderSubscribe, bot: aiogram.Bot):
    await callback.answer()
    user_telegram_id = callback.message.chat.id
    path_setting = path_setting_funcs.get_setting_path()
    provider_token = path_setting_funcs.get_document_by_key_name(path_setting, 'yookassa_token',)
    days = callback_data.period_days
    total_price = TEST_SUBSCRIBE_COST if settings.test_mode else callback_data.price
    prices = [LabeledPrice(label=f'Подписка на бота', amount=total_price * 100, )]
    wb_cabinet_original_id = callback_data.wb_cabinet_original_id
    payload = json.dumps(
        {
            'period': days,
            'wb_cabinet_original_id': wb_cabinet_original_id,
        }
    )

    await bot.send_invoice(
        user_telegram_id,
        title='Подписка на бота',
        description=(
            f"Счет на продление тарифа: \n"
            f"Продление подписки на 1 магазин сроком на {get_day_suffix(days)}"
            f" за {total_price} рублей. \n"
            f"После оплаты услуга считается оказанной, возврат средств не производится. "
        ),
        payload=payload,
        provider_token=provider_token,
        currency='RUB',
        prices=prices,
    )


@router.pre_checkout_query()
async def pre_checkout_query_handler(pre_checkout_query: types.PreCheckoutQuery, bot: aiogram.Bot):
    await bot.answer_pre_checkout_query(pre_checkout_query.id, ok=True)


@router.message(aiogram.F.successful_payment)
async def successful_payment_handler(message: types.Message, bot: aiogram.Bot):
    successful_payment = message.successful_payment
    payload = json.loads(successful_payment.invoice_payload)
    cost = successful_payment.total_amount / 100
    period = payload['period']
    wb_cabinet_original_id = payload['wb_cabinet_original_id']

    async with sm() as session:
        stmt = select(User).where(User.user_telegram_id == message.chat.id)
        result = await session.execute(stmt)
        user = result.scalars().first()

    message_for_admin = (
        f'Заказ от {user.username}({message.chat.id}), успешно оплачен на {cost} RUB\n'
        f'Тариф продлен на {get_day_suffix(period)}\n'
    )

    await sender_manager.send_message_to_admin(message_for_admin)

    async with sm() as session:
        stmt = select(WBCabinet).where(WBCabinet.id == wb_cabinet_original_id)
        result = await session.execute(stmt)

        wb_cabinet: WBCabinet = result.scalars().first()
        wb_cabinet.demo = False
        wb_cabinet.expiration_time += timedelta(days=period)

        payment = Payment()
        payment.user = user
        payment.amount = cost
        payment.target = f'wb_cabinet_id:{wb_cabinet_original_id}:period:{period}'

        await session.commit()

    await messages.OrderSubscribe(bot, message.chat.id)()
