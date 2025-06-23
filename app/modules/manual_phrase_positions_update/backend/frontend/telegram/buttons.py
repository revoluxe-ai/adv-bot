from aiogram.filters.callback_data import CallbackData


class UpdatePositionsForActivePhrase(
    CallbackData, prefix="UpdatePositionsForActivePhrase"
):
    adv_setting_original_id: int
    wb_user_cabinet_original_id: int
    target: str
