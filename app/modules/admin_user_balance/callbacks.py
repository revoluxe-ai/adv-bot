from aiogram.filters.callback_data import CallbackData


class AdminUserBalance(CallbackData, prefix="admin_user_balance"):
    """Callback для кнопок пополнения баланса пользователей администратором."""

    action: str  # menu | add_balance | add_bonus | confirm | cancel | back
    operation: str | None = None  # add_balance | add_bonus (for confirm)
