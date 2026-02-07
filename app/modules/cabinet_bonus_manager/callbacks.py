from aiogram.filters.callback_data import CallbackData


class AdminPanel(CallbackData, prefix="admin_panel"):
    """Callback для входа в панель администратора (показать выбор: кабинеты / пользователи)."""

    action: str  # "menu"


class AdminBonus(CallbackData, prefix="admin_bonus"):
    """Callback для кнопок управления бонусами"""

    action: str
    operation: str | None = None
    wb_cabinet_original_id: int | None = None
    amount: float | None = None
