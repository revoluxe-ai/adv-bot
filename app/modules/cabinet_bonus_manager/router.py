"""
Обработчики команд администратора для управления бонусами кабинетов.
Файл является переходным для поддержки обратной совместимости со старым кодом.
Все обработчики теперь перенаправляются в isolated_router.py
"""
import logging
from aiogram import Router

# Экспортируем все компоненты из isolated_router.py для обратной совместимости
from app.modules.cabinet_bonus_manager.main_handler import (
    bonus_router
)

logger = logging.getLogger(__name__)
router = Router()

# Переопределяем маршрутизатор, включая в него изолированный маршрутизатор
router.include_router(bonus_router)

# ВАЖНО: Не добавляйте новые обработчики в этот файл!
# Все новые обработчики должны быть добавлены в isolated_router.py
