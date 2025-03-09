from aiogram.filters.callback_data import CallbackData


class SalesPlanSettingsMenu(CallbackData, prefix="salesplansettingsmenu"):
    adv_id: int
