from aiogram import Bot, Router
from aiogram.filters import StateFilter
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message
from sqlalchemy import select

from app.client_bot import utils
from app.client_bot.user_interface.handlers.start_registration_func import (
    start_registration,
)
from app.client_bot.user_interface.views import messages
from app.utils.db.session_maker import get_async_session_maker as sm

from ...common_slaves.wildberries.models import AdvSetting
from ...wb_adv_updater import data_manager
from .callbacks import ChangeExponentSettinginAdvSettingCallback

router = Router()


@router.callback_query(ChangeExponentSettinginAdvSettingCallback.filter())
async def change_exponent_setting(
    callback: CallbackQuery,
    callback_data: ChangeExponentSettinginAdvSettingCallback,
    state: FSMContext,
):
    adv_id = callback_data.adv_id
    wb_user_cabinet_original_id = callback_data.wb_user_cabinet_original_id
    await state.update_data(adv_id=adv_id,
                            last_wb_user_cabinet_original_id=wb_user_cabinet_original_id)
    await state.set_state("waiting_for_new_exponent")
    message = callback.message
    await message.answer("Введите новое значение для экспоненты прогнозируемого CTR:")


@router.message(StateFilter("waiting_for_new_exponent"))
async def set_new_exponent_for_predict_ctr(
    message: Message, state: FSMContext, bot: Bot
):
    data = await state.get_data()
    adv_id: int = data["adv_id"]
    text = message.text
    if text == "/start":
        await state.set_state(None)
        await start_registration(message, bot, state)
        return
    # Заменяем запятую на точку, если есть
    text = text.replace(",", ".")
    if not text.replace(".", "", 1).isdigit() or text.count(".") > 1:
        await message.answer(
            "Введите число в правильном формате (например, 1.23 или 1,23)"
        )
        return
    exponent_predict_ctr = float(text)
    async with sm(read_only=False) as session:
        query = select(AdvSetting).filter(AdvSetting.adv_id == adv_id)
        result = await session.execute(query)
        adv_setting: AdvSetting = result.scalar_one()
        adv_setting.exponent_predict_ctr = exponent_predict_ctr
        await session.commit()
    await message.answer(
        f"Экспонента прогнозируемого CTR изменена на {exponent_predict_ctr}"
    )
    await state.set_state(None)

    keywords = await utils.get_keywords_for_keyboard(adv_setting)
    await state.update_data(adv_choice_last_page=1)
    state_data = await state.get_data()
    wb_user_cabinet_original_id = state_data.get("last_wb_user_cabinet_original_id")
    nmids = adv_setting.nmids
    chat_id = message.from_user.id
    adv_choice_last_page = 1
    try:
        main_photos = await data_manager.get_main_photos(nmids[:1])
    except:
        await messages.NoMainPhotos(bot, chat_id)(adv_setting)
        return

    await messages.AdvKeywordsSetting(
        bot,
        chat_id,
        keywords,
        adv_setting,
        wb_user_cabinet_original_id,
        adv_choice_last_page,
        main_photos[0],
        page=1,
    )(state)
    return
