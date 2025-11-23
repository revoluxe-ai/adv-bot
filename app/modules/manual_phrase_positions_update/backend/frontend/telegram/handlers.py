from aiogram import Bot, Router
from aiogram.types import CallbackQuery

from app.modules.common_slaves.wildberries.models import AdvSetting
from app.utils.db.session_maker import get_async_session_maker as sm

from .buttons import UpdatePositionsForActivePhrase

router = Router()


@router.callback_query(UpdatePositionsForActivePhrase.filter())
async def update_positions_for_active_phrase(
    callback_query: CallbackQuery,
    callback_data: UpdatePositionsForActivePhrase,
    bot: Bot,
) -> None:
    adv_setting_original_id = callback_data.adv_setting_original_id

    assert callback_query.message
    chat_id = callback_query.message.chat.id

    async with sm() as session:
        adv_setting: AdvSetting = await session.get(AdvSetting, adv_setting_original_id)

    assert adv_setting


    await bot.send_message(
        chat_id,
        (
           "Данная функция больше не поддерживается со стороны Wildberries"
        ),
    )
    return None

