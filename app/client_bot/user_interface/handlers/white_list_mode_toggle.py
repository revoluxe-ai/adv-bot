from aiogram import Bot, Router
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery
from sqlalchemy import select, update

from app.client_bot.ui_access import UiAccessMode
from app.modules.common_slaves.wildberries.models import AdvSetting
from app.modules.common_slaves.wildberries.models.white_list_mode import WhiteListMode
from app.modules.white_list_mode_settings.telegram.main_callback import WhiteListModeToggle
from app.modules.white_list_mode_settings.telegram.keyboards import FREE_WHITE_LIST_MODES
from app.modules.white_list_mode_settings.telegram.main_message import (
    WhiteListModeMenuMessage,
)
from app.utils.db.session_maker import get_async_session_maker as sm

router = Router()


def _resolve_white_list_mode_ui_access(adv_setting: AdvSetting) -> UiAccessMode:
    """Resolve a simple deterministic FREE/PAID fallback for white-list mode UI."""
    return UiAccessMode.PAID if adv_setting.bot_active else UiAccessMode.FREE


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
        stmt_select = select(AdvSetting).where(AdvSetting.id == adv_setting_original_id)
        result = await session.execute(stmt_select)
        adv_setting = result.scalar_one()
        ui_access = _resolve_white_list_mode_ui_access(adv_setting)
        if ui_access == UiAccessMode.FREE and new_mode not in FREE_WHITE_LIST_MODES:
            assert callback_query.message
            chat_id = callback_query.message.chat.id
            await bot.send_message(
                chat_id,
                "Этот режим белого списка доступен только в платном автоуправлении.",
            )
            await WhiteListModeMenuMessage(
                bot,
                chat_id,
                adv_setting.adv_id,
                ui_access=ui_access,
            )()
            return

        # TODO(strategy-transition): Вынести переключение стратегий в общий хелпер!
        stmt_update = (
            update(AdvSetting)
            .where(AdvSetting.id == adv_setting_original_id)
            .values({"white_list_mode": new_mode})
        )
        await session.execute(stmt_update)
        await session.commit()

        result = await session.execute(stmt_select)
        adv_setting = result.scalar_one()

    assert callback_query.message
    chat_id = callback_query.message.chat.id

    await bot.send_message(
        chat_id,
        f"Выбран режим {new_mode.name.replace('_', ' ').title()}.",
    )

    await WhiteListModeMenuMessage(bot, chat_id, adv_setting.adv_id, ui_access=ui_access)()
