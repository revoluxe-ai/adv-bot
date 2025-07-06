from aiogram.filters.callback_data import CallbackData


class AdvActiveController(CallbackData, predfix="AdvActiveController"):
    adv_setting_original_id: int


class NewAutoAdvStatus(CallbackData, prefix="NewAutoAdvStatus"):
    adv_setting_original_id: int
    target_adv: str  # 'auto' or 'auction'
    new_status: bool  # True for enable, False for disable
