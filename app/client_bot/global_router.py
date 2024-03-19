from aiogram import Router
from . import middlewars
from .user_interface.handlers import start
from .user_interface.handlers import adv_setting
from .user_interface.handlers import exceptions
from .user_interface.handlers import keyword_settings


global_router = Router()
global_router.message.middleware(middlewars.ThrottlingMiddleware())
global_router.include_routers(exceptions.user_router)
global_router.include_routers(exceptions.admin_router)
global_router.include_routers(start.router)
global_router.include_routers(adv_setting.router)
global_router.include_routers(keyword_settings.router)




