from aiogram import Bot, Router
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery

from app.modules.white_list_mode_settings.telegram.main_callback import WhiteListModeMenu
from app.modules.white_list_mode_settings.telegram.main_message import WhiteListModeMenuMessage

router = Router()


@router.callback_query(WhiteListModeMenu.filter())
async def white_list_mode_menu_handler(
    callback: CallbackQuery,
    callback_data: WhiteListModeMenu,
    bot: Bot,
    state: FSMContext,
) -> None:
    chat_id = callback.from_user.id
    adv_id = callback_data.adv_id
    await WhiteListModeMenuMessage(bot, chat_id, adv_id, state)()
