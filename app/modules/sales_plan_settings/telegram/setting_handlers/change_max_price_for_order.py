from aiogram import Bot, F, Router
from aiogram.filters import StateFilter
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message
from sqlalchemy import select, update

from app.modules.common_slaves.wildberries.models import AdvSetting
from app.modules.sales_plan_settings.v3_raise_max_cpo import (
    format_v3_raise_max_auto_disable_message,
    resolve_flag_after_max_cpo_decrease,
)
from app.utils.db.session_maker import get_async_session_maker as sm

from .. import callbacks, main_message

router = Router()


@router.callback_query(
    callbacks.ChangePlanSetting.filter(F.target_point == "change-max-price-for-order")
)
async def change_max_for_sales_for_day_handler(
    callback: CallbackQuery,
    callback_data: callbacks.ChangePlanSetting,
    bot: Bot,
    state: FSMContext,
):
    adv_id = callback_data.adv_id
    await state.update_data(adv_id=adv_id)
    await state.set_state("waiting_for_new_max_price_for_order")
    message = callback.message
    assert message is not None
    await message.answer(
        "Введите новую максимальную себестоимость число с плавающей точкой  от 1):"
    )


@router.message(StateFilter("waiting_for_new_max_price_for_order"))
async def set_new_max_price_for_order(
    message: Message, state: FSMContext, bot: Bot
) -> None:
    text_message = (
        "Введите новую максимальную себестоимость число с плавающей точкой  от 1):"
    )
    text = message.text
    if text is None or not text.isdigit():
        await message.answer(text_message)
        return
    new_value = int(text)

    if new_value < 1:
        await message.answer(text_message)
        return
    data = await state.get_data()
    adv_id: int = data["adv_id"]

    async with sm() as session:
        stmt = select(AdvSetting).where(AdvSetting.adv_id == adv_id)
        result = await session.execute(stmt)
        adv = result.scalar_one()
        old_max = adv.max_price_for_order
        current_flag = bool(adv.substitute_fact_cpo_for_max)
        new_flag, side_effect = resolve_flag_after_max_cpo_decrease(
            old_max=old_max,
            new_max=new_value,
            current_flag=current_flag,
            adv_id=adv_id,
        )
        update_stmt = (
            update(AdvSetting)
            .where(AdvSetting.adv_id == adv_id)
            .values(
                {
                    AdvSetting.max_price_for_order: new_value,
                    AdvSetting.substitute_fact_cpo_for_max: new_flag,
                }
            )
        )
        await session.execute(update_stmt)
        await session.commit()

    assert message.from_user is not None
    chat_id = message.from_user.id
    if side_effect is not None:
        await bot.send_message(
            chat_id,
            format_v3_raise_max_auto_disable_message(side_effect),
        )
    await main_message.SalesPlanSettingsMenuMessage(bot, chat_id, adv_id, state)()
