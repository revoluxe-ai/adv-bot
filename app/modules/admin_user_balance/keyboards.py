from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup

from app.modules.admin_user_balance.callbacks import AdminUserBalance


def get_user_balance_keyboard() -> InlineKeyboardMarkup:
    """
    Клавиатура после выбора пользователя: пополнить баланс, начислить бонусы, назад.
    """
    keyboard = [
        [
            InlineKeyboardButton(
                text="➕ Пополнить баланс",
                callback_data=AdminUserBalance(action="add_balance").pack(),
            ),
            InlineKeyboardButton(
                text="➕ Начислить бонусы",
                callback_data=AdminUserBalance(action="add_bonus").pack(),
            ),
        ],
        [
            InlineKeyboardButton(
                text="🔙 Назад",
                callback_data=AdminUserBalance(action="menu").pack(),
            )
        ],
        [
            InlineKeyboardButton(
                text="🔙 В главное меню админа",
                callback_data=AdminUserBalance(action="back").pack(),
            )
        ],
    ]
    return InlineKeyboardMarkup(inline_keyboard=keyboard)


def get_confirm_keyboard(operation: str) -> InlineKeyboardMarkup:
    """
    Клавиатура подтверждения операции (сумма и комментарий берутся из FSM).
    """
    keyboard = [
        [
            InlineKeyboardButton(
                text="✅ Подтвердить",
                callback_data=AdminUserBalance(
                    action="confirm", operation=operation
                ).pack(),
            ),
            InlineKeyboardButton(
                text="❌ Отмена",
                callback_data=AdminUserBalance(action="cancel").pack(),
            ),
        ]
    ]
    return InlineKeyboardMarkup(inline_keyboard=keyboard)


def get_back_to_admin_keyboard() -> InlineKeyboardMarkup:
    """Кнопка возврата в главное меню администратора (выход из сцены)."""
    keyboard = [
        [
            InlineKeyboardButton(
                text="🔙 В главное меню админа",
                callback_data=AdminUserBalance(action="back").pack(),
            )
        ]
    ]
    return InlineKeyboardMarkup(inline_keyboard=keyboard)
