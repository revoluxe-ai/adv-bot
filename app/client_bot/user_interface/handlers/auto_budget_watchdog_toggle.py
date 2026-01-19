from aiogram import Bot, Router
from aiogram.types import CallbackQuery
from sqlalchemy import update

from app.client_bot.user_interface.views.callbacks import AutoBudgetWatchdogToggle
from app.modules.common_slaves.wildberries.models import AdvSetting
from app.utils.db.session_maker import get_async_session_maker as sm

router = Router()


@router.callback_query(AutoBudgetWatchdogToggle.filter())
async def toggle_auto_budget_watchdog(
    callback_query: CallbackQuery,
    callback_data: AutoBudgetWatchdogToggle,
    bot: Bot,
) -> None:
    new_status = callback_data.new_status
    adv_setting_id = callback_data.adv_setting_original_id

    async with sm() as session:
        stmt = (
            update(AdvSetting)
            .where(AdvSetting.id == adv_setting_id)
            .values({"auto_budget_watchdog_enabled": new_status})
        )
        await session.execute(stmt)
        await session.commit()

    assert callback_query.message
    chat_id = callback_query.message.chat.id

    status_text = (
        "Контроль запуска кампаний и пополнения бюджета включен"
        if new_status
        else "Контроль запуска кампаний и пополнения бюджета отключен"
    )
    await bot.send_message(chat_id, status_text)
