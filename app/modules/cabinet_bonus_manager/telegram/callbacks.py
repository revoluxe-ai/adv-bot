from typing import Optional
from aiogram.filters.callback_data import CallbackData


class BonusCallback(CallbackData, prefix="bonus_isolated"):
    """Класс для обработки колбеков в изолированном модуле бонусов"""
    action: str
    shop_id: Optional[str] = None
    amount: Optional[float] = None
    operation: Optional[str] = None 