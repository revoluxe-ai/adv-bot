"""
Обработчики команд администратора для управления бонусами кабинетов.
Файл является переходным для поддержки обратной совместимости со старым кодом.
Все обработчики перенаправляются в isolated_router.py
"""
import logging
from aiogram import Router
from app.modules.cabinet_bonus_manager.isolated_router import bonus_router

logger = logging.getLogger(__name__)
router = Router()

# Переопределяем маршрутизатор, включая в него изолированный маршрутизатор
# Это обеспечивает поддержку старых импортов в других частях приложения
router.include_router(bonus_router)

# ВАЖНО: Не добавляйте новые обработчики в этот файл!
# Все новые обработчики должны быть добавлены в isolated_router.py 