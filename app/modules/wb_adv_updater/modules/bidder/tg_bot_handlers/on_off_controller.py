import aiogram
from aiogram import F, Router, types
from aiogram.fsm.context import FSMContext
from sqlalchemy.future import select

from app.client_bot.user_interface import states
from app.client_bot.user_interface.views import callbacks
from app.modules.common_slaves.wildberries.models import AdvSetting
from app.utils.db.session_maker import get_async_session_maker

sm = get_async_session_maker

router = Router()


# функция включения биддера
@router.callback_query(callbacks.CPMSettingMenu.filter(F.action == "set_auto_cpm"))
async def get_min_position(
    callback: types.CallbackQuery,
    callback_data: callbacks.ChoiceAdvPaginator,
    bot: aiogram.Bot,
    state: FSMContext,
):
    adv_original_id = callback_data.adv_original_id
    await state.update_data(last_adv_original_id=adv_original_id)
    await state.set_state(states.CPMSetting.waiting_for_min_position)
    import app.client_bot.user_interface.views.messages as ui_messages

    await ui_messages.AutoCPMSettingGetMinPosition(bot, callback.message.chat.id)(
        adv_original_id
    )
    return


@router.callback_query(callbacks.CPMSettingMenu.filter(F.action == "off_auto_cpm"))
async def off_auto_cpm(
    callback: types.CallbackQuery,
    callback_data: callbacks.ChoiceAdvPaginator,
    bot: aiogram.Bot,
    state: FSMContext,
):
    adv_original_id = callback_data.adv_original_id
    async with sm(read_only=False) as session:
        adv = await session.execute(
            select(AdvSetting).where(AdvSetting.id == adv_original_id)
        )
        adv = adv.scalar()
        adv.bidder_active = False
        await session.commit()
        import app.client_bot.user_interface.views.messages as ui_messages

        await ui_messages.CPMSetting(bot, callback.message.chat.id)(adv_original_id)
    return
