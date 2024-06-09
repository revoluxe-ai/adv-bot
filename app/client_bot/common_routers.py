from aiogram import Router

from python_modules import path_setting_funcs

from .middlewars.check_rights import check_subscribe_on_shop
from .user_interface.handlers import adv_setting, exceptions, keyword_settings, setting_min_ctr

common_router = Router()

setting_path = path_setting_funcs.get_setting_path()

admin_bot_api = path_setting_funcs.get_document_by_key_name(setting_path, 'admin_telegram_bot_api')
common_router.include_routers(exceptions.user_router)
common_router.include_routers(exceptions.admin_router)
common_router.include_routers(adv_setting.router)
common_router.include_routers(keyword_settings.router)
common_router.include_routers(setting_min_ctr.router)

common_router.callback_query.middleware(check_subscribe_on_shop.CheckSubscribeOnShop())
