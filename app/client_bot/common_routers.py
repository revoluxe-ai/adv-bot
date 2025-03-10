from aiogram import Router
from app.modules.shop_runner.auction_boost_mode_settings import AuctionBoostModeSettingsRouter
from app.modules.predict_ctr_exponent_settings import ChangeExponentSettinginAdvSettingRouter
from app.modules.bidder_step_setting.telegram_handler import router as bidder_step_setting_router
from app.modules.adv_creator.telegram.handlers.main_handler import router as adv_creator_router
from python_modules import path_setting_funcs
from .middlewars.return_to_start_from_state import ReturnToStart
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
                                      shop_settings,
                                       reset_place_setting

)
from app.modules.wb_adv_updater.modules.bidder import tg_router as bidder_router
from app.modules.white_list_updater import router as white_list_updater_router
from ..settings import settings
from app.modules.user_message_sender import middleware_for_adding_task
from app.modules.sales_plan_settings  import SalesPlanSettingsMenuRouter

common_router = Router()

setting_path = path_setting_funcs.get_setting_path()

# admin_bot_api = path_setting_funcs.get_document_by_key_name(setting_path, 'admin_telegram_bot_api')
common_router.include_routers(keywords_positions_history.handlers.router)
if not settings.test_mode:
    common_router.include_routers(exceptions.user_router)
    common_router.include_routers(exceptions.admin_router)

common_router.message.middleware.register(ReturnToStart())
common_router.include_routers(SalesPlanSettingsMenuRouter)
common_router.include_routers(AuctionBoostModeSettingsRouter)
common_router.include_routers(ChangeExponentSettinginAdvSettingRouter)
common_router.include_routers(bidder_step_setting_router)
common_router.include_routers(adv_creator_router)
common_router.include_routers(white_list_updater_router)
common_router.include_routers(reset_place_setting.router)
common_router.include_routers(bidder_router)
common_router.include_routers(change_cpm.router)
common_router.include_routers(favorite_advs_for_users.router)
common_router.include_routers(clusters.router)
common_router.include_routers(start.router)
common_router.include_routers(download_keywords.router)
common_router.include_routers(adv_setting.router)
# common_router.include_routers(adv_creator_router)
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
common_router.callback_query.middleware(middleware_for_adding_task.AddingMessageTaskMiddleWare())
common_router.message.middleware(middleware_for_adding_task.AddingMessageTaskMiddleWare())