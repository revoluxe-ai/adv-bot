from aiogram.filters.callback_data import CallbackData


class AutoUpdateWhiteListSetting(CallbackData, prefix="auto_update_white_list_setting"):
    new_status: bool
    adv_setting_original_id: int


class RelevantKeywordStatusSetting(CallbackData, prefix="relevant_keyword_status_setting"):
    new_relevant_status: bool
    keyword_setting_original_id: int
