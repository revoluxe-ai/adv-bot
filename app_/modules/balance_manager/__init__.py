"""
Модуль управления балансом пользователей

Этот модуль предоставляет интерфейс для работы с балансом и бонусами кабинетов WB:
- Пополнение баланса
- Списание средств
- Начисление и управление бонусами
- Отслеживание истории транзакций

Основные компоненты:
- balance_service: сервисы для работы с балансом
- exceptions: исключения модуля
"""

__all__ = ["get_cabinet_balance_and_bonuses", "add_balance_router"]


from .balance_service import (
    get_cabinet_balance as get_cabinet_balance_and_bonuses,
)  # Переименован для ясности
from .handlers import router as add_balance_router
