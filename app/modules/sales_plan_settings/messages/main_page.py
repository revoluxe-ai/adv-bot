from aiogram import Router, Bot
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery
from . import messages
from . import callbacks

router = Router()


@router.callback_query(callbacks.SalesPlanSettingsMenu.filter())
async def plane_settings_menu_handler(
                            callback: CallbackQuery,
                            callback_data: callbacks.SalesPlanSettingsMenu,
                            bot: Bot,
                            state: FSMContext):

    await messages.SalesPlanSettingsMenu(
        bot,
        callback,
        callback_data,
        state,
    )()
    return

