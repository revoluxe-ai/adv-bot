from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup

from app.modules.cabinet_bonus_manager.callbacks import AdminBonus


def get_shop_bonus_keyboard(wb_cabinet_original_id: int) -> InlineKeyboardMarkup:
    """
    Создает клавиатуру для управления бонусами кабинета

    Args:
        wb_cabinet_original_id: ID кабинета

    Returns:
        InlineKeyboardMarkup: Клавиатура с кнопками управления бонусами
    """
    keyboard = [
        [
            InlineKeyboardButton(
                text="➕ Добавить",
                callback_data=AdminBonus(action="add", wb_cabinet_original_id=wb_cabinet_original_id).pack(),
            ),
            InlineKeyboardButton(
                text="➖ Снять",
                callback_data=AdminBonus(action="subtract", wb_cabinet_original_id=wb_cabinet_original_id).pack(),
            ),
        ],
        [
            InlineKeyboardButton(
                text="🔄 Обнулить",
                callback_data=AdminBonus(action="reset", wb_cabinet_original_id=wb_cabinet_original_id).pack(),
            )
        ],
        [InlineKeyboardButton(text="🔙 Назад", callback_data=AdminBonus(action="menu").pack())],
    ]
    return InlineKeyboardMarkup(inline_keyboard=keyboard)


def get_confirm_keyboard(
    wb_cabinet_original_id: int, operation: str, amount: float | None = None
) -> InlineKeyboardMarkup:
    """
    Создает клавиатуру для подтверждения операции с бонусами

    Args:
        wb_cabinet_original_id: ID кабинета
        operation: Тип операции (add/subtract/reset)
        amount: Сумма операции (не используется для reset)

    Returns:
        InlineKeyboardMarkup: Клавиатура с кнопками подтверждения
    """
    keyboard = [
        [
            InlineKeyboardButton(
                text="✅ Подтвердить",
                callback_data=AdminBonus(
                    action="confirm",
                    wb_cabinet_original_id=wb_cabinet_original_id,
                    amount=amount,
                    operation=operation,
                ).pack(),
            ),
            InlineKeyboardButton(text="❌ Отмена", callback_data=AdminBonus(action="cancel").pack()),
        ]
    ]
    return InlineKeyboardMarkup(inline_keyboard=keyboard)


def get_back_to_menu_keyboard() -> InlineKeyboardMarkup:
    """
    Создает клавиатуру с кнопкой возврата в меню

    Returns:
        InlineKeyboardMarkup: Клавиатура с кнопкой возврата
    """
    keyboard = [
        [
            InlineKeyboardButton(
                text="🔙 Вернуться в меню",
                callback_data=AdminBonus(action="menu").pack(),
            )
        ]
    ]
    return InlineKeyboardMarkup(inline_keyboard=keyboard)
