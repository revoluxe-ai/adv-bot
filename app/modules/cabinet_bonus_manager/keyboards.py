from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.utils.keyboard import InlineKeyboardBuilder

def get_bonus_admin_keyboard() -> InlineKeyboardMarkup:
    """
    Создает клавиатуру с кнопками для управления бонусами
    """
    keyboard = InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text="➕ Добавить бонусы", callback_data="bonus_add"),
                InlineKeyboardButton(text="➖ Снять бонусы", callback_data="bonus_subtract")
            ],
            [
                InlineKeyboardButton(text="🔄 Обнулить бонусы", callback_data="bonus_reset"),
                InlineKeyboardButton(text="👁 Проверить бонусы", callback_data="bonus_check")
            ],
            [
                InlineKeyboardButton(text="🔙 Назад", callback_data="bonus_back")
            ]
        ]
    )
    return keyboard

def get_shop_bonus_keyboard(shop_id: str) -> InlineKeyboardMarkup:
    """
    Создает клавиатуру с кнопками для управления бонусами конкретного магазина
    
    Args:
        shop_id: Идентификатор магазина
        
    Returns:
        InlineKeyboardMarkup: Клавиатура для управления бонусами магазина
    """
    builder = InlineKeyboardBuilder()
    
    # Кнопки операций с бонусами
    builder.row(
        InlineKeyboardButton(text="➕ Пополнить бонусы", callback_data=f"shop_bonus_add_{shop_id}"),
        InlineKeyboardButton(text="➖ Списать бонусы", callback_data=f"shop_bonus_subtract_{shop_id}")
    )
    
    builder.row(
        InlineKeyboardButton(text="🔄 Обнулить бонусы", callback_data=f"shop_bonus_reset_{shop_id}")
    )
    
    # Кнопка возврата в меню
    builder.row(
        InlineKeyboardButton(text="🔙 Назад к меню", callback_data="bonus_menu")
    )
    
    return builder.as_markup()

def get_confirm_keyboard(operation: str = None, shop_id: str = None, amount: float = None) -> InlineKeyboardMarkup:
    """
    Создает клавиатуру с кнопками подтверждения/отмены операции
    
    Args:
        operation: Тип операции ('add', 'subtract', 'reset'), если None, то используются просто confirm/cancel
        shop_id: Идентификатор магазина
        amount: Сумма операции (только для add/subtract)
        
    Returns:
        InlineKeyboardMarkup: Клавиатура с кнопками подтверждения и отмены
    """
    builder = InlineKeyboardBuilder()
    
    # Формируем данные для callback
    if operation and shop_id:
        callback_data = f"bonus_confirm_{operation}_{shop_id}"
        if amount is not None:
            callback_data += f"_{amount}"
    else:
        # Простое подтверждение/отмена для сцены
        callback_data = "confirm_ok"
        
    # Добавляем кнопки подтверждения и отмены
    builder.row(
        InlineKeyboardButton(text="✅ Подтвердить", callback_data=callback_data if operation else "confirm_ok"),
        InlineKeyboardButton(text="❌ Отменить", callback_data="confirm_cancel")
    )
    
    # Добавляем кнопку возврата назад, если это сложная операция
    if operation and shop_id:
        builder.row(
            InlineKeyboardButton(text="🔙 Назад", callback_data="back_to_shop_bonus")
        )
    
    return builder.as_markup()

def get_back_to_menu_keyboard() -> InlineKeyboardMarkup:
    """
    Создает клавиатуру с кнопкой возврата в меню бонусов
    
    Returns:
        InlineKeyboardMarkup: Клавиатура с кнопкой возврата в меню
    """
    builder = InlineKeyboardBuilder()
    
    # Добавляем кнопку возврата в меню
    builder.row(
        InlineKeyboardButton(text="🔙 Вернуться в меню", callback_data="bonus_menu")
    )
    
    return builder.as_markup() 