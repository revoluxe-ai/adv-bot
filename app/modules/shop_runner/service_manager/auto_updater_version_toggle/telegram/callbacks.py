from aiogram.filters.callback_data import CallbackData


class AutoUpdaterVersionToggle(CallbackData, prefix="auto_updater_version_toggle_handler"):
    new_version: int
    adv_setting_original_id: int

