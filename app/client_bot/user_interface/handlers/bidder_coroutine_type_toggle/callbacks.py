from aiogram.filters.callback_data import CallbackData

class BidderCoroutineTypeToggle(CallbackData, prefix="bidder_coroutine_type_toggle"):
    """Переключение типа корутины биддера."""

    new_type: str
    adv_setting_original_id: int









