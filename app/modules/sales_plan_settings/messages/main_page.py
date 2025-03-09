from aiogram import Router, Bot
from aiogram.filters import StateFilter
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message
from sqlalchemy import select

from app.client_bot import utils
from app.client_bot.user_interface.handlers.start import start_registration
from . import messages
from app.utils.db.session_maker import get_async_session_maker as sm

from . import callbacks
from ...common_slaves.wildberries.models import AdvSetting
from ...wb_adv_updater import data_manager

router = Router()


@router.callback_query(callbacks.SalesPlanSettingsMenu.filter())
async def plane_settings_menu_handler(
                            callback: CallbackQuery,
                            callback_data: callbacks.SalesPlanSettingsMenu,
                            bot: Bot,
                            state: FSMContext):

    adv_id = callback_data.adv_id
    await state.update_data(adv_id=adv_id)

    await messages.SalesPlanSettingsMenu(
        bot,
        chat_id,
        keywords,
        adv_setting,
        wb_user_cabinet_original_id,
        adv_choice_last_page,
        main_photos[0],
        page=1,
    )(state)
    return

