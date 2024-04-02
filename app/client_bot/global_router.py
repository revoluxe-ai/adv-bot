from aiogram import Router
from . import middlewars
from .user_interface.handlers import start
from .user_interface.handlers import adv_setting
from .user_interface.handlers import exceptions
from .user_interface.handlers import keyword_settings
from python_modules import path_setting_funcs
from . import echo_handler
from .common_routers import common_router


global_router = Router()
global_router.include_routers(common_router)
global_router.include_routers(start.router)
global_router.message.middleware(middlewars.ThrottlingMiddleware())
global_router.callback_query.middleware(middlewars.ThrottlingMiddleware())







