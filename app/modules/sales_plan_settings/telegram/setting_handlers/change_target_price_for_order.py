from aiogram import Bot, F, Router
from aiogram.filters import StateFilter
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message
from sqlalchemy import update

from app.modules.common_slaves.wildberries.models import AdvSetting
from app.utils.db.session_maker import get_async_session_maker as sm

from .. import callbacks, main_callback, main_message

router = Router()


@router.callback_query(callbacks.ChangePlanSetting.filter(F.target_point == 'change-target-price-for-order'))
async def change_plan_for_sales_for_day_handler(
                            callback: CallbackQuery,
                            callback_data: main_callback.SalesPlanSettingsMenu,
                            bot: Bot,
                            state: FSMContext):
    adv_id = callback_data.adv_id
    await state.update_data(adv_id=adv_id)
    await state.set_state('waiting_for_new_target_price_for_order')
    message = callback.message
    await message.answer('Введите новую целевую себестоимость число с плавающей точкой  от 1):')


@router.message(StateFilter('waiting_for_new_target_price_for_order'))
async def set_new_target_price_for_order(message: Message,
                                           state: FSMContext,
                                           bot: Bot):
    text = message.text
    message_text = 'Введите новую целевую себестоимость число с плавающей точкой  от 1):'
    if not text.isdigit():
        await message.answer(message_text)
        return
    new_value = int(text)

    if new_value < 1:
        await message.answer(message_text)
        return
    data = await state.get_data()
    adv_id: int = data['adv_id']

    stmt = update(AdvSetting)\
    .filter(AdvSetting.adv_id == adv_id)\
    .values({
        AdvSetting.target_price_for_order: new_value
    })
    async with sm() as session:
        await session.execute(stmt)
        await session.commit()

    chat_id = message.from_user.id
    await main_message.SalesPlanSettingsMenuMessage(
        bot,
        chat_id,
        adv_id,
        state
    )()





