from aiogram.types import InlineKeyboardButton

from app.client_bot.user_interface.views.callbacks import ChangeRecSystemModeStatus
from app.modules.common_slaves.wildberries.models import AdvSetting, WBUserCabinet


def get(adv_setting:  AdvSetting, wb_user_cabinet: WBUserCabinet) -> InlineKeyboardButton:
    # Новая кнопка для режима раскрутки РС (полок)
    if adv_setting.rec_system_mode:
        rec_text = "Выключить режим раскрутки РС (полок)"
        rec_new_status = False
    else:
        rec_text = "Включить режим раскрутки РС (полок)"
        rec_new_status = True

    rec_callback = ChangeRecSystemModeStatus(
        adv_id=adv_setting.adv_id,
        wb_user_cabinet_original_id=wb_user_cabinet.id,
        new_status=rec_new_status,
    ).pack()
    rec_button = InlineKeyboardButton(text=rec_text, callback_data=rec_callback)
    return rec_button
