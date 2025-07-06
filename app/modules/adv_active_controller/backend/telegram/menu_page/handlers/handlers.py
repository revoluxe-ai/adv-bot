from aiogram import Router as _Router, Bot
from aiogram.types import CallbackQuery as _CallbackQuery

from app.modules.adv_active_controller.backend.telegram.menu_page import (
    message as _message,
)
from app.modules.adv_active_controller.backend.telegram.menu_page import utils as _utils
from app.modules.adv_active_controller.backend.telegram.menu_page.callbacks import (
    AdvActiveController as _AdvActiveController,
)
from app.modules.common_slaves.wildberries.models import AdvSetting as _AdvSetting

router = _Router()


@router.callback_query(_AdvActiveController.filter())
async def adv_active_controller_menu_page_handler(
    callback_query: _CallbackQuery, callback_data: _AdvActiveController, bot: Bot
) -> None:
    """
    Обработчик для меню страницы контроля активности объявлений
    """

    adv_setting_original_id = callback_data.adv_setting_original_id

    adv: _AdvSetting = await _utils.get_adv_setting(adv_setting_original_id)
    assert callback_query.message
    chat_id = callback_query.message.chat.id
    await _message.AdvActiveControllerMenu(adv, bot, chat_id)()
