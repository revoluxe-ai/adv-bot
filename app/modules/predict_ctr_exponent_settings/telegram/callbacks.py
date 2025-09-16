from aiogram.filters.callback_data import CallbackData


class ChangeExponentSettinginAdvSettingCallback(
    CallbackData, prefix="change_exponent_setting"
):
    adv_id: int
