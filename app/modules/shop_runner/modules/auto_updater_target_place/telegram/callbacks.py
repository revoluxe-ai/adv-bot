from aiogram.filters.callback_data import CallbackData


class AutoUpdateTargetPlaceSetting(
    CallbackData, prefix="auto_update_target_place_setting"
):
    new_status: bool
    adv_setting_original_id: int
