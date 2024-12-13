from aiogram import Router

from python_modules import path_setting_funcs
from .user_interface.handlers import (adv_setting,
                                      exceptions,
                                      keyword_settings,
                                      setting_min_ctr,
                                      favorite_advs_for_users,
                                      change_max_cpc,
                                      min_views_for_ml_predict_ctr,
                                      keywords_positions_history,
                                      add_white_phrases,
                                      get_shop_for_admin,
                                      cpm_builder,
                                      add_black_phrases,
                                      download_keywords,
                                     clusters,
                                     update_adv,
                                     start,
                                     strategy_setting,
                                      change_cpm,
                                      shop_settings

)

from app.modules.wb_adv_updater.modules.bidder import tg_router as bidder_router
from app.modules.phone_getter import router as phone_getter_router

from ..settings import settings

common_router = Router()

setting_path = path_setting_funcs.get_setting_path()

admin_bot_api = path_setting_funcs.get_document_by_key_name(setting_path, 'admin_telegram_bot_api')
common_router.include_routers(keywords_positions_history.handlers.router)
if not settings.test_mode:
    common_router.include_routers(exceptions.user_router)
    common_router.include_routers(exceptions.admin_router)

common_router.include_routers(phone_getter_router)
common_router.include_routers(bidder_router)
common_router.include_routers(change_cpm.router)
common_router.include_routers(favorite_advs_for_users.router)
common_router.include_routers(clusters.router)
common_router.include_routers(start.router)
common_router.include_routers(download_keywords.router)
common_router.include_routers(adv_setting.router)
common_router.include_routers(add_black_phrases.router)
common_router.include_routers(cpm_builder.router)
common_router.include_routers(get_shop_for_admin.router)
common_router.include_routers(keyword_settings.router)
common_router.include_routers(add_white_phrases.router)
common_router.include_routers(setting_min_ctr.router)
common_router.include_routers(change_max_cpc.router)
common_router.include_routers(min_views_for_ml_predict_ctr.router)
common_router.include_routers(update_adv.router)
common_router.include_routers(strategy_setting.router)
common_router.include_routers(shop_settings.router)
# common_router.callback_query.middleware(check_subscribe_on_shop.CheckSubscribeOnShop())
