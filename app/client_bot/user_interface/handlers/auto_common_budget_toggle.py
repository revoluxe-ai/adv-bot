from aiogram import Bot, Router
from aiogram.types import CallbackQuery
from sqlalchemy import update

from app.client_bot.user_interface.services.total_spend_snapshot import (
    load_total_spend_snapshot,
)
from app.client_bot.user_interface.views import keyboards, callbacks, messages
from app.modules.common_slaves.wildberries.models import AdvSetting
from app.utils.db.session_maker import get_async_session_maker as sm

router = Router()


@router.callback_query(callbacks.AutoCommonBudgetToggle.filter())
async def toggle_auto_common_budget(
    callback_query: CallbackQuery,
    callback_data: callbacks.AutoCommonBudgetToggle,
    bot: Bot,
) -> None:
    new_status = callback_data.new_status
    adv_setting_id = callback_data.adv_setting_original_id

    async with sm(read_only=False) as session:
        stmt = (
            update(AdvSetting)
            .where(AdvSetting.id == adv_setting_id)
            .values({"auto_common_budget": new_status})
        )
        await session.execute(stmt)
        await session.commit()

    async with sm() as session:
        adv_setting = await session.get(AdvSetting, adv_setting_id)
    if adv_setting is None:
        return

    assert callback_query.message
    msg = callback_query.message
    chat_id = msg.chat.id
    message_id = msg.message_id

    total_spend = await load_total_spend_snapshot(adv_setting)
    menu = messages.CampaignActivityMenu(
        bot, chat_id, adv_setting, total_spend=total_spend
    )
    text = menu.text
    keyboard = keyboards.get_campaign_activity_menu_keyboard(adv_setting)
    await bot.edit_message_text(
        chat_id=chat_id,
        message_id=message_id,
        text=text,
        reply_markup=keyboard,
    )
