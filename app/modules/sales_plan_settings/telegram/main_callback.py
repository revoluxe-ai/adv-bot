from aiogram.filters.callback_data import CallbackData


class SalesPlanSettingsMenu(CallbackData, prefix="sales-plan-settings-menu-callback"):
    adv_id: int
