from aiogram import Router
from . import middlewars
from .user_interface.handlers import start
from .user_interface.handlers import adv_setting
from .user_interface.handlers import exceptions
from .user_interface.handlers import keyword_settings
from python_modules import path_setting_funcs
from . import echo_handler
from .user_interface.handlers import user_subscribe_on_channel



common_router = Router()




setting_path = path_setting_funcs.get_setting_path()

admin_bot_api = path_setting_funcs.get_document_by_key_name(setting_path,
                'admin_telegram_bot_api')
common_router.include_routers(exceptions.user_router)
common_router.include_routers(exceptions.admin_router)

common_router.include_routers(user_subscribe_on_channel.router)
common_router.include_routers(adv_setting.router)
common_router.include_routers(keyword_settings.router)


common_router.callback_query.middleware(middlewars.CheckSubscribeOnChannel())


