from aiogram import Router
from . import middlewars
from .user_interface.handlers import start
from .user_interface.handlers import adv_setting
from .user_interface.handlers import exceptions
from .user_interface.handlers import keyword_settings
from python_modules import path_setting_funcs



global_router = Router()
global_router.message.middleware(middlewars.ThrottlingMiddleware())

setting_path = path_setting_funcs.get_setting_path()
try:
    admin_bot_api = path_setting_funcs.get_document_by_key_name(setting_path,
                    'admin_telegram_bot_api')
    global_router.include_routers(exceptions.user_router)
    global_router.include_routers(exceptions.admin_router)
except:
    pass

global_router.include_routers(start.router)
global_router.include_routers(adv_setting.router)
global_router.include_routers(keyword_settings.router)




