from aiogram.filters.callback_data import CallbackData


class ChangeHideZeroViewsStatus(CallbackData, prefix="change_hide_zero_views"):
    adv_id: int
    wb_user_cabinet_original_id: int
    new_status: bool
