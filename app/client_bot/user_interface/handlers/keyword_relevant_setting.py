from aiogram import Bot, Router
from aiogram.types import CallbackQuery
from sqlalchemy import update

from app.modules.common_slaves.wildberries.models import KeywordSetting
from app.modules.shop_runner.service_manager.old_modules.setting_auto_updater.modules.white_list_updater.auto_white_list_updater.telegram.callbacks import (
    RelevantKeywordStatusSetting,
)
from app.utils.db.session_maker import get_async_session_maker as sm

router = Router()


@router.callback_query(RelevantKeywordStatusSetting.filter())
async def relevant_keyword_status_setting(
    callback_query: CallbackQuery, callback_data: RelevantKeywordStatusSetting, bot: Bot
):
    keyword_setting_original_id = callback_data.keyword_setting_original_id
    new_relevant_status = callback_data.new_relevant_status

    async with sm() as session:
        stmt = (
            update(KeywordSetting)
            .where(KeywordSetting.id == keyword_setting_original_id)
            .values({"relevant": new_relevant_status})
        )
        await session.execute(stmt)
        await session.commit()

    chat_id = callback_query.message.chat.id

    new_text_status_str: str = (
        "Ключ добавлен в релевантные фразы"
        if new_relevant_status
        else "Ключ убрал из релевантных фраз"
    )

    await bot.send_message(chat_id, new_text_status_str)
