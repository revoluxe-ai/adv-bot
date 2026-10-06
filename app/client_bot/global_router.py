from aiogram import Router
from aiogram.fsm.scene import SceneRegistry

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
from .middlewars.channel_subscription import ChannelSubscriptionMiddleware
from .middlewars.gate import GateMiddleware
from .middlewars.phone_required import PhoneRequiredMiddleware
from .middlewars.return_to_start_from_state import ReturnToStart
from app.modules.wb_sky_mcp.bot_handlers import router as mcp_oauth_router
from .user_interface.handlers import gate, phone_collection, request_presentation, start

global_router = Router()

# Pre-answer: ImmediateCallbackAnswerUpdateMiddleware на Dispatcher (dispatcher_factory).

# Aiogram wraps with reversed(list): last registered runs first (outermost).
# Desired runtime: Gate → Channel → Phone → handler.
# Invite deferred: Gate no-ops when settings.invite_gate is False (default).
_ = global_router.message.middleware(ReturnToStart())
_ = global_router.message.middleware(PhoneRequiredMiddleware())
_ = global_router.message.middleware(ChannelSubscriptionMiddleware())
_ = global_router.message.middleware(GateMiddleware())
_ = global_router.callback_query.middleware(PhoneRequiredMiddleware())
_ = global_router.callback_query.middleware(ChannelSubscriptionMiddleware())
_ = global_router.callback_query.middleware(GateMiddleware())
# Один SceneRegistry на роутер: обе сцены должны быть в одном реестре,
# иначе при двух вызовах SceneRegistry(router) второй перезаписывает первый.
scene_registry = SceneRegistry(global_router)
scene_registry.add(BonusScene)
scene_registry.add(UserBalanceScene)

# gate.router first — gate:* callbacks when invite_gate re-enabled (dormant on rollout)
_ = global_router.include_router(mcp_oauth_router)
_ = global_router.include_router(gate.router)
_ = global_router.include_router(phone_collection.router)
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
