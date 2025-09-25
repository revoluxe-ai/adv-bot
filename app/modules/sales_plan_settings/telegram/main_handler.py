from aiogram import Bot, Router
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery

from . import main_callback, main_message

router = Router()


@router.callback_query(main_callback.SalesPlanSettingsMenu.filter())
async def plane_settings_menu_handler(
    callback: CallbackQuery,
    callback_data: main_callback.SalesPlanSettingsMenu,
    bot: Bot,
    state: FSMContext,
) -> None:
    chat_id = callback.from_user.id
    adv_id = callback_data.adv_id
    await main_message.SalesPlanSettingsMenuMessage(bot, chat_id, adv_id, state)()
    return
