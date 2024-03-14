from aiogram import Router
from app.telegram_bot.middlewars import LastMessageMiddleWare
from app.telegram_bot import middlewars
from app.telegram_bot.user_interface.handlers import start
from app.telegram_bot.user_interface.handlers import adv_setting
from .user_interface.handlers import exceptions
from app.telegram_bot.user_interface.handlers import keyword_settings


global_router = Router()
# global_router.message.middleware(middlewars.HardErrorMiddleware())
# global_router.callback_query.middleware(middlewars.HardErrorMiddleware())
global_router.message.middleware(middlewars.ThrottlingMiddleware())
global_router.message.middleware(LastMessageMiddleWare())
global_router.callback_query.middleware(LastMessageMiddleWare())
global_router.include_routers(exceptions.user_router)
global_router.include_routers(exceptions.admin_router)
global_router.include_routers(start.router)
global_router.include_routers(adv_setting.router)
global_router.include_routers(keyword_settings.router)




