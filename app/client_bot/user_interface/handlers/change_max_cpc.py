import aiogram
from aiogram import F, Router, types
from aiogram.filters import StateFilter
from aiogram.fsm.context import FSMContext
from sqlalchemy.future import select

from app.modules.common_slaves.wildberries.models import AdvSetting
from app.utils.db.session_maker import get_async_session_maker

from .. import states
from ..views import callbacks, messages

sm = get_async_session_maker

router = Router()


@router.callback_query(
    callbacks.ChangeMaxCPC.filter(F.action == "to_max_cpc_change_page")
)
async def to_page_for_cpc_setting(
    callback: types.CallbackQuery,
    callback_data: callbacks.ChoiceAdvPaginator,
    bot: aiogram.Bot,
    state: FSMContext,
):
    await state.set_state(states.ChangeMaxCPC.waiting_for_new_max_cpc)
    adv_original_id = callback_data.adv_original_id
    await messages.MaxCPCSetting(bot, callback.message.chat.id)(adv_original_id)


@router.message(StateFilter(states.ChangeMaxCPC.waiting_for_new_max_cpc))
async def set_max_cpc(message: types.Message, bot: aiogram.Bot, state: FSMContext):
    data = await state.get_data()
    text = message.text
    chat_id = message.chat.id

    def get_cpc_from_text(text):
        text = text.replace(",", ".")
        try:
            cpc_value = float(text.strip())
            return cpc_value
        except ValueError:
            return None

    cpc = get_cpc_from_text(text)
    if cpc:
        adv_original_id = data["last_adv_original_id"]
        async with sm(read_only=False) as session:
            adv = await session.execute(
                select(AdvSetting).where(AdvSetting.id == adv_original_id)
            )
            adv = adv.scalar()
            if cpc == 0:
                cpc = None
            adv.max_cpc = cpc
            await session.commit()
            await messages.MaxCPCSetting(bot, chat_id)(adv_original_id)
    else:
        await bot.send_message(chat_id, "Некорректное значение. Попробуйте еще раз")
    return


@router.callback_query(callbacks.ChangeMaxCPC.filter(F.action == "turn_off_max_cpc"))
async def turn_off_max_cpc(
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
        adv.max_cpc = None
        await session.commit()
        await messages.MaxCPCSetting(bot, callback.message.chat.id)(adv_original_id)
    return
