from aiogram.filters.callback_data import CallbackData





class ChangePlanSetting(CallbackData, prefix="change-plan-setting"):
    adv_id: int
    target_point: str