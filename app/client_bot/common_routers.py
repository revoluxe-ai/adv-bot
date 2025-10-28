from aiogram import Router

from app.modules.adv_creator.telegram.handlers.main_handler import (
    router as adv_creator_router,
)
from app.modules.bidder_auto_mode import router as BidderAutoModeRouter
from app.modules.bidder_step_setting.telegram_handler import (
    router as bidder_step_setting_router,
)
from app.modules.manual_phrase_positions_update import (
    manual_update_phrase_position_router,
)
from app.modules.predict_ctr_exponent_settings import (
    ChangeExponentSettinginAdvSettingRouter,
)
from app.modules.sales_plan_settings import SalesPlanSettingsMenuRouter
from app.modules.shop_runner.auction_boost_mode_settings import (
    AuctionBoostModeSettingsRouter,
)
from app.modules.shop_runner.service_manager.old_modules.auto_updater_target_place import (
    auto_updater_target_place_setting_router,
)
from app.modules.shop_runner.service_manager.old_modules.setting_auto_updater.modules.white_list_updater.auto_white_list_updater import (
    AutoWhiteListUpdaterRouter,
)
from app.modules.user_message_sender import middleware_for_adding_task
from app.modules.wb_adv_updater.modules.bidder import tg_router as bidder_router
from app.modules.white_list_updater import router as white_list_updater_router

from ..settings import settings
from .middlewars.return_to_start_from_state import ReturnToStart

from .user_interface.handlers.keywords_positions_history import (
    KeywordsPositionsHistoryRouter,
)
from .user_interface.handlers import (
    add_black_phrases,
    add_white_phrases,
    adv_setting,
    change_cpm,
    auto_max_cpm_toggle,
    change_max_cpc,
    clusters,
    cpm_builder,
    download_keywords,
    exceptions,
    favorite_advs_for_users,
    get_shop_for_admin,
    keyword_relevant_setting,
    keyword_settings,
    min_views_for_ml_predict_ctr,
    orders_source_toggle,
    predict_ctr_mode_toggle,
    reset_place_setting,
    setting_min_ctr,
    shop_settings,
    strategy_setting,
    update_adv,
)

common_router = Router()


# admin_bot_api = path_setting_funcs.get_document_by_key_name(setting_path, 'admin_telegram_bot_api')
common_router.include_routers(KeywordsPositionsHistoryRouter)
if not settings.test_mode:
    common_router.include_routers(exceptions.user_router)
    common_router.include_routers(exceptions.admin_router)


common_router.message.middleware.register(ReturnToStart())

common_router.include_routers(manual_update_phrase_position_router)
common_router.include_router(auto_updater_target_place_setting_router)
common_router.include_routers(AutoWhiteListUpdaterRouter)
common_router.include_routers(keyword_relevant_setting.router)
common_router.include_routers(orders_source_toggle.router)
common_router.include_routers(predict_ctr_mode_toggle.router)
common_router.include_routers(auto_max_cpm_toggle.router)
common_router.include_routers(BidderAutoModeRouter)
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
# common_router.include_routers(start.router)  # Уже подключен в global_router.py
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
# Закомментировано, т.к. роутер уже подключен в global_router.py через register_bonus_scene
# common_router.include_routers(cabinet_bonus_manager_router)
common_router.callback_query.middleware(
    middleware_for_adding_task.AddingMessageTaskMiddleWare()
)
common_router.message.middleware(
    middleware_for_adding_task.AddingMessageTaskMiddleWare()
)
