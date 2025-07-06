from aiogram.filters.callback_data import CallbackData


class ChangeAddingBalanceSum(CallbackData, prefix="ChangeAddingBalanceSum"):
    adv_setting_original_id: int
    """
    Callback data for changing the maximum balance adding sum per day.
    """
