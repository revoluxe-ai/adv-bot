from aiogram.filters.callback_data import CallbackData

from app.modules.common_slaves.wildberries.models.white_list_mode import WhiteListMode


class WhiteListModeMenu(CallbackData, prefix="white_list_mode_menu"):
    adv_id: int


class WhiteListModeToggle(CallbackData, prefix="white_list_mode_toggle"):
    new_mode: str
    adv_setting_original_id: int
