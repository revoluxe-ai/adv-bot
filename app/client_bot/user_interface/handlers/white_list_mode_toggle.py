from aiogram import Bot, Router
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery
from sqlalchemy import select, update

from app.modules.common_slaves.wildberries.models import AdvSetting
from app.modules.common_slaves.wildberries.models.white_list_mode import WhiteListMode
from app.modules.white_list_mode_settings.telegram.main_callback import WhiteListModeToggle
from app.modules.white_list_mode_settings.telegram.main_message import WhiteListModeMenuMessage
from app.utils.db.session_maker import get_async_session_maker as sm

router = Router()


@router.callback_query(WhiteListModeToggle.filter())
async def toggle_white_list_mode(
    callback_query: CallbackQuery,
    callback_data: WhiteListModeToggle,
    bot: Bot,
    state: FSMContext,
) -> None:
    new_mode = WhiteListMode[callback_data.new_mode]
    adv_setting_original_id = callback_data.adv_setting_original_id
    async with sm() as session:
        stmt_update = (
            update(AdvSetting)
            .where(AdvSetting.id == adv_setting_original_id)
            .values({"white_list_mode": new_mode})
        )
        await session.execute(stmt_update)
        await session.commit()

        stmt_select = select(AdvSetting).where(AdvSetting.id == adv_setting_original_id)
        result = await session.execute(stmt_select)
        adv_setting = result.scalar_one()

    assert callback_query.message
    chat_id = callback_query.message.chat.id

    await bot.send_message(
        chat_id,
        f"Выбран режим {new_mode.name.replace('_', ' ').title()}.",
    )

    await WhiteListModeMenuMessage(bot, chat_id, adv_setting.adv_id)()
