from aiogram import Bot, Router
from aiogram.types import CallbackQuery
from sqlalchemy import select, update

from app.client_bot.user_interface.services.total_spend_snapshot import (
    load_total_spend_snapshot,
)
from app.client_bot.user_interface.views import keyboards
from app.client_bot.user_interface.views.callbacks import CommonBudgetModeToggle
from app.client_bot.user_interface.views import messages
from app.modules.common_slaves.wildberries.models import AdvSetting
from app.utils.db.session_maker import get_async_session_maker as sm

router = Router()


@router.callback_query(CommonBudgetModeToggle.filter())
async def toggle_common_budget_mode(
    callback_query: CallbackQuery,
    callback_data: CommonBudgetModeToggle,
    bot: Bot,
) -> None:
    new_status = callback_data.new_status
    adv_setting_id = callback_data.adv_setting_original_id

    async with sm(read_only=False) as session:
        if new_status:
            result = await session.execute(
                select(AdvSetting).where(AdvSetting.id == adv_setting_id)
            )
            adv_setting = result.scalar_one_or_none()
            if adv_setting is not None and (adv_setting.common_budget_daily_limit is None or
                    adv_setting.common_budget_daily_limit == 0):
                common_limit = (adv_setting.auto_budget_daily_limit or 0) + (
                    adv_setting.search_auto_budget_daily_limit or 0
                )
                stmt = (
                    update(AdvSetting)
                    .where(AdvSetting.id == adv_setting_id)
                    .values({
                        "use_common_budget": new_status,
                        "common_budget_daily_limit": common_limit,
                    })
                )
            else:
                stmt = (
                    update(AdvSetting)
                    .where(AdvSetting.id == adv_setting_id)
                    .values({"use_common_budget": new_status})
                )
        else:
            result = await session.execute(
                select(AdvSetting).where(AdvSetting.id == adv_setting_id)
            )
            adv_setting = result.scalar_one_or_none()
            values: dict[str, bool | int] = {"use_common_budget": new_status}
            if adv_setting is not None:
                common = adv_setting.common_budget_daily_limit or 0
                auto = getattr(adv_setting, "auto_budget_daily_limit", 0)
                search = getattr(adv_setting, "search_auto_budget_daily_limit", 0)
                if auto == 0 and search == 0:
                    values["auto_budget_daily_limit"] = common // 2
                    values["search_auto_budget_daily_limit"] = common - (common // 2)
                elif auto == 0:
                    values["auto_budget_daily_limit"] = max(0, common - (search or 0))
                elif search == 0:
                    values["search_auto_budget_daily_limit"] = max(0, common - (auto or 0))
            stmt = (
                update(AdvSetting)
                .where(AdvSetting.id == adv_setting_id)
                .values(values)
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
