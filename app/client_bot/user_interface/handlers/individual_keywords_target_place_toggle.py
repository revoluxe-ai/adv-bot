from aiogram import Bot, Router
from aiogram.types import CallbackQuery
from sqlalchemy import update

from app.client_bot.user_interface.views.callbacks import (
    IndividualKeywordsTargetPlaceToggle,
)
from app.modules.common_slaves.wildberries.models import AdvSetting
from app.utils.db.session_maker import get_async_session_maker as sm

router = Router()


@router.callback_query(IndividualKeywordsTargetPlaceToggle.filter())
async def toggle_individual_keywords_target_place(
    callback_query: CallbackQuery,
    callback_data: IndividualKeywordsTargetPlaceToggle,
    bot: Bot,
) -> None:
    new_status = callback_data.new_status
    adv_id = callback_data.adv_id

    async with sm() as session:
        stmt = (
            update(AdvSetting)
            .where(AdvSetting.adv_id == adv_id)
            .values({"individual_keywords_target_place_mode": new_status})
        )
        _ = await session.execute(stmt)
        await session.commit()

    assert callback_query.message
    chat_id = callback_query.message.chat.id

    status_text = (
        "Инд. места КЗ включены"
        if new_status
        else "Инд. места КЗ выключены"
    )
    _ = await bot.send_message(chat_id, status_text)
