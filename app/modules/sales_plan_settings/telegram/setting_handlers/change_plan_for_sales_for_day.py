from aiogram import Bot, F, Router
from aiogram.filters import StateFilter
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message
from sqlalchemy import update

from app.modules.common_slaves.wildberries.models import AdvSetting
from app.utils.db.session_maker import get_async_session_maker as sm

from .. import callbacks, main_callback, main_message

router = Router()


@router.callback_query(callbacks.ChangePlanSetting.filter(F.target_point == "change-plan-for-sales-for-day"))
async def change_plan_for_sales_for_day_handler(
    callback: CallbackQuery,
    callback_data: main_callback.SalesPlanSettingsMenu,
    bot: Bot,
    state: FSMContext,
) -> None:
    adv_id = callback_data.adv_id
    await state.update_data(adv_id=adv_id)
    await state.set_state("waiting_for_new_plan_for_sales_for_day")
    if callback.message and isinstance(callback.message, Message):
        await callback.message.answer("Введите новый план по продажам в день (целое число от 1):")
    return


@router.message(StateFilter("waiting_for_new_plan_for_sales_for_day"))
async def set_new_exponent_for_predict_ctr(message: Message, state: FSMContext, bot: Bot) -> None:
    text = message.text
    if text is None or not text.isdigit():
        await message.answer("Введите новый план по продажам в день (целое число от 1):")
        return
    new_value = int(text)

    if new_value < 1:
        await message.answer("Введите новый план по продажам в день (целое число от 1):")
        return
    data = await state.get_data()
    adv_id: int = data["adv_id"]

    stmt = update(AdvSetting).filter(AdvSetting.adv_id == adv_id).values({AdvSetting.plan_for_sales_for_day: new_value})
    async with sm() as session:
        await session.execute(stmt)
        await session.commit()

    if message.from_user:
        chat_id = message.from_user.id
        await main_message.SalesPlanSettingsMenuMessage(bot, chat_id, adv_id, state)()
    return
