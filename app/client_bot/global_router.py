from aiogram import Router
from aiogram.fsm.scene import SceneRegistry
from aiogram.utils import callback_answer

from ..modules.admin_user_balance.scene import (
    UserBalanceScene,
    register_user_balance_scene,
)
from ..modules.balance_manager import add_balance_router
from ..modules.cabinet_bonus_manager.bonus_scene import (
    BonusScene,
    register_bonus_scene,
)
from .common_routers import common_router
from .middlewars.gate import GateMiddleware
from .user_interface.handlers import gate, request_presentation, start

global_router = Router()
_ = global_router.message.middleware(GateMiddleware())
_ = global_router.callback_query.middleware(GateMiddleware())
_ = global_router.callback_query.middleware(
    callback_answer.CallbackAnswerMiddleware(pre=True, text="Запрос в обработке"),
)

# Один SceneRegistry на роутер: обе сцены должны быть в одном реестре,
# иначе при двух вызовах SceneRegistry(router) второй перезаписывает первый.
scene_registry = SceneRegistry(global_router)
scene_registry.add(BonusScene)
scene_registry.add(UserBalanceScene)

# ВАЖНО: порядок подключения роутеров критически важен
# gate_router первым — обрабатывает callback'и gate:* для пользователей без passed_gate
_ = global_router.include_router(gate.router)
_ = global_router.include_router(request_presentation.router)
# Затем start.router (команда /start и callback Start)
_ = global_router.include_router(start.router)
# global_router.include_router(bonus_router)
register_bonus_scene(global_router, scene_registry=scene_registry)
register_user_balance_scene(global_router, scene_registry=scene_registry)

# Затем регистрируем глобальные обработчики, особенно важный /start

# Затем регистрируем остальные роутеры
global_router.include_routers(common_router)
global_router.include_routers(add_balance_router)
# global_router.message.middleware(middlewars.ThrottlingMiddleware())
# global_router.callback_query.middleware(middlewars.ThrottlingMiddleware())
