"""
Менеджер состояний для модуля управления бонусами кабинетов.
Обеспечивает изоляцию состояний этого модуля от остальных частей приложения.
"""
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.context import FSMContext
from typing import Dict, Any, Optional, Union
import logging

logger = logging.getLogger(__name__)

class BonusManagerStateGroup(StatesGroup):
    """Группа состояний для модуля управления бонусами"""
    waiting_for_shop_id = State()  # Ожидание ввода shop_id
    waiting_for_amount = State()   # Ожидание ввода суммы
    waiting_for_description = State()  # Ожидание ввода описания операции
    waiting_for_confirm = State()  # Ожидание подтверждения операции

