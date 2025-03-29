from aiogram import Router
from aiogram.utils import callback_answer

from . import middlewars
from .common_routers import common_router
from app.modules.cabinet_bonus_manager import register_bonus_scene, bonus_router
from .user_interface.handlers import payments, ref_program, start, add_balance

global_router = Router()
global_router.callback_query.middleware(callback_answer.CallbackAnswerMiddleware(pre=True, text='Запрос в обработке'))

# ВАЖНО: порядок подключения роутеров критически важен для правильной обработки команды /start
# Сначала регистрируем bonus_router и bonus_scene
# bonus_router содержит обработчик команды /start, который очищает состояния модуля
# Но не использует return, позволяя глобальному обработчику start.router выполниться
global_router.include_router(start.router)
global_router.include_router(bonus_router)
register_bonus_scene(global_router)

# Затем регистрируем глобальные обработчики, особенно важный /start

# Затем регистрируем остальные роутеры
global_router.include_routers(common_router)
global_router.include_routers(add_balance.router)
global_router.include_routers(ref_program.router)
# global_router.message.middleware(middlewars.ThrottlingMiddleware())
global_router.include_routers(payments.router)
# global_router.callback_query.middleware(middlewars.ThrottlingMiddleware())

