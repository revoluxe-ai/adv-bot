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


class BonusStateManager:
    """
    Класс для управления состояниями модуля бонусов.
    Предоставляет изолированное хранение данных в рамках FSMContext,
    используя специальный префикс для ключей данных.
    """
    KEY_PREFIX = "bonus_manager_"

    def __init__(self, state_context: FSMContext):
        self.state_context = state_context

    async def set_state(self, state: Optional[State]) -> None:
        """Устанавливает состояние FSM"""
        await self.state_context.set_state(state)

    async def clear_state(self) -> None:
        """Очищает состояние FSM и все данные модуля"""
        # Получаем текущие данные
        data = await self.state_context.get_data()
        
        # Удаляем только данные с нашим префиксом
        keys_to_remove = [key for key in data.keys() if key.startswith(self.KEY_PREFIX)]
        for key in keys_to_remove:
            await self.state_context.update_data({key: None})
        
        # Очищаем состояние
        await self.state_context.set_state(None)

    async def update_data(self, data: Dict[str, Any]) -> None:
        """
        Обновляет данные состояния с использованием префикса
        
        Args:
            data: Словарь с данными для сохранения
        """
        prefixed_data = {f"{self.KEY_PREFIX}{key}": value for key, value in data.items()}
        await self.state_context.update_data(prefixed_data)

    async def get_data(self) -> Dict[str, Any]:
        """
        Получает данные состояния, относящиеся к модулю бонусов
        
        Returns:
            Dict[str, Any]: Словарь с данными модуля (без префикса в ключах)
        """
        all_data = await self.state_context.get_data()
        
        # Фильтруем только данные с нашим префиксом и убираем префикс из ключей
        result = {}
        prefix_len = len(self.KEY_PREFIX)
        
        for key, value in all_data.items():
            if key.startswith(self.KEY_PREFIX):
                clean_key = key[prefix_len:]
                result[clean_key] = value
                
        return result

    async def get_value(self, key: str, default: Any = None) -> Any:
        """
        Получает конкретное значение по ключу
        
        Args:
            key: Ключ для получения данных (без префикса)
            default: Значение по умолчанию, если ключ не найден
            
        Returns:
            Any: Значение данных или default, если ключ не найден
        """
        data = await self.get_data()
        return data.get(key, default)

    @staticmethod
    def create(state_context: FSMContext) -> 'BonusStateManager':
        """
        Фабричный метод для создания экземпляра менеджера состояний
        
        Args:
            state_context: Контекст состояния FSM
            
        Returns:
            BonusStateManager: Экземпляр менеджера состояний
        """
        return BonusStateManager(state_context) 