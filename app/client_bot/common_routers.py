from aiogram import Router

from app.modules.adv_creator.telegram.handlers.main_handler import (
    router as adv_creator_router,
)
from app.modules.bidder_auto_mode import router as BidderAutoModeRouter  # noqa
from app.modules.bidder_step_setting.telegram_handler import (
    router as bidder_step_setting_router,
)
from app.modules.manual_phrase_positions_update import (
    manual_update_phrase_position_router,
)
from app.modules.predict_ctr_exponent_settings import (
    ChangeExponentSettinginAdvSettingRouter,
)
from app.modules.hide_zero_views_toggle import HideZeroViewsToggleRouter
from app.modules.sales_plan_settings import SalesPlanSettingsMenuRouter
from app.modules.white_list_mode_settings import router as WhiteListModeSettingsRouter
from app.modules.shop_runner.auction_boost_mode_settings import (
    AuctionBoostModeSettingsRouter,
)
from app.modules.shop_runner.service_manager.old_modules.auto_updater_target_place.telegram import (
    auto_updater_target_place_setting_router,
)
from app.modules.shop_runner.service_manager.v3_rollout_aggressiveness_toggle import (
    v3_rollout_aggressiveness_toggle_router,
)
from app.modules.shop_runner.service_manager.services.auto_updater_v3.card_ab_hold.telegram import (
    card_ab_hold_confirm_router,
    card_ab_hold_router,
)
from app.modules.shop_runner.service_manager.v3_tick_report_ui import (
    v3_tick_report_ui_router,
)
from app.modules.shop_runner.service_manager.keyword_v3_decision_trace_ui import (
    keyword_v3_decision_trace_ui_router,
)
from app.modules.v3_calibration_step_setting import (
    v3_calibration_step_setting_router,
)
from app.modules.shop_runner.service_manager.old_modules.setting_auto_updater.modules.white_list_updater.auto_white_list_updater import (
    AutoWhiteListUpdaterRouter,
)
from app.modules.user_message_sender import middleware_for_adding_task
from app.modules.wb_adv_updater.modules.bidder import tg_router as bidder_router

from ..settings import settings

from .user_interface.handlers.keywords_positions_history import (
    KeywordsPositionsHistoryRouter,
)
from .user_interface.handlers.raise_card_analyze import (
    raise_card_analyze_router,
)
from .user_interface.handlers import (
    admin_panel,
    add_black_phrases,
    add_relevant_phrase_templates,
    invite_show,
    add_white_phrases,
    adv_setting,
    change_auto_bid,
    change_cpm,
    clusters,
    connect_existing_advs,
    cpm_builder,
    download_keywords,
    adv_excel_roundtrip,
    exceptions,
    favorite_advs_for_users,
    get_shop_for_admin,
    keyword_relevant_setting,
    keyword_settings,
    min_views_for_ml_predict_ctr,
    orders_source_toggle,
    predict_ctr_mode_toggle,
    target_position_mode_toggle,
    sales_predict_method_toggle,
    auto_update_exponent_toggle,
    auto_add_only_relevant_phrase_toggle,
    auto_budget_watchdog_toggle,
    common_bid_toggle,
    individual_keywords_target_place_toggle,
    reset_place_setting,
    set_common_bid_manual,
    rebind_adv_campaign_ids,
    shop_settings,
    strategy_setting,
    rec_system_mode_toggle,
    campaign_activity,
    auto_shelf_bid_control_menu,
    time_settings,
    white_list_mode_toggle,
)
from .user_interface.handlers.common_budget_mode_toggle import (
    router as common_budget_mode_toggle_router,
)
from .user_interface.handlers.auto_common_budget_toggle import (
    router as auto_common_budget_toggle_router,
)
from .user_interface.handlers.incremental_stats_toggle import (
    router as incremental_stats_toggle_router,
)
from .user_interface.handlers.bidder_coroutine_type_toggle import (
    router as bidder_coroutine_type_toggle_router,
)

common_router = Router()


# admin_bot_api = path_setting_funcs.get_document_by_key_name(setting_path, 'admin_telegram_bot_api')
common_router.include_routers(KeywordsPositionsHistoryRouter)
common_router.include_routers(raise_card_analyze_router)
common_router.include_routers(admin_panel.router)
if not settings.test_mode:
    common_router.include_routers(exceptions.user_router)
    common_router.include_routers(exceptions.admin_router)


# Router includes reorganized for new module
common_router.include_routers(manual_update_phrase_position_router)
common_router.include_routers(auto_updater_target_place_setting_router)
common_router.include_routers(v3_rollout_aggressiveness_toggle_router)
common_router.include_routers(card_ab_hold_router)
common_router.include_routers(card_ab_hold_confirm_router)
common_router.include_routers(v3_calibration_step_setting_router)
common_router.include_routers(v3_tick_report_ui_router)
common_router.include_routers(keyword_v3_decision_trace_ui_router)
common_router.include_routers(AutoWhiteListUpdaterRouter)
common_router.include_routers(keyword_relevant_setting.router)
common_router.include_routers(orders_source_toggle.router)
common_router.include_routers(predict_ctr_mode_toggle.router)
common_router.include_routers(target_position_mode_toggle.router)
common_router.include_routers(sales_predict_method_toggle.router)
common_router.include_routers(auto_update_exponent_toggle.router)
common_router.include_routers(auto_add_only_relevant_phrase_toggle.router)
common_router.include_routers(auto_budget_watchdog_toggle.router)
common_router.include_routers(common_budget_mode_toggle_router)
common_router.include_routers(auto_common_budget_toggle_router)
common_router.include_routers(common_bid_toggle.router)
common_router.include_routers(set_common_bid_manual.router)
common_router.include_routers(rebind_adv_campaign_ids.router)
common_router.include_routers(individual_keywords_target_place_toggle.router)
common_router.include_routers(incremental_stats_toggle_router)
common_router.include_routers(BidderAutoModeRouter)
common_router.include_routers(SalesPlanSettingsMenuRouter)
common_router.include_routers(AuctionBoostModeSettingsRouter)
common_router.include_routers(ChangeExponentSettinginAdvSettingRouter)
common_router.include_routers(HideZeroViewsToggleRouter)
common_router.include_routers(bidder_coroutine_type_toggle_router)
common_router.include_routers(bidder_step_setting_router)
common_router.include_routers(adv_creator_router)
common_router.include_routers(connect_existing_advs.router)
common_router.include_routers(rec_system_mode_toggle.router)
common_router.include_routers(white_list_mode_toggle.router)
common_router.include_routers(WhiteListModeSettingsRouter)
common_router.include_routers(reset_place_setting.router)
common_router.include_routers(bidder_router)
common_router.include_routers(change_cpm.router)
common_router.include_routers(favorite_advs_for_users.router)
common_router.include_routers(invite_show.router)
common_router.include_routers(clusters.router)
# common_router.include_routers(start.router)  # Уже подключен в global_router.py
common_router.include_routers(download_keywords.router)
common_router.include_routers(adv_excel_roundtrip.router)
common_router.include_routers(adv_setting.router)
common_router.include_routers(campaign_activity.router)
common_router.include_routers(auto_shelf_bid_control_menu.router)
common_router.include_routers(time_settings.router)
# common_router.include_routers(adv_creator_router)
common_router.include_routers(add_black_phrases.router)
common_router.include_routers(add_relevant_phrase_templates.router)
common_router.include_routers(cpm_builder.router)
common_router.include_routers(get_shop_for_admin.router)
common_router.include_routers(keyword_settings.router)  # type: ignore[attr-defined]
common_router.include_routers(add_white_phrases.router)
common_router.include_routers(change_auto_bid.router)
common_router.include_routers(min_views_for_ml_predict_ctr.router)
# TODO(legacy-remove): модуль содержит legacy callbacks.StrategySetting;
# удалить legacy-ветку после стабилизации нового экрана StrategyMenu.
common_router.include_routers(strategy_setting.router)  # type: ignore[attr-defined]
common_router.include_routers(shop_settings.router)
# Закомментировано, т.к. роутер уже подключен в global_router.py через register_bonus_scene
# common_router.include_routers(cabinet_bonus_manager_router)
_ = common_router.callback_query.middleware(
    middleware_for_adding_task.AddingMessageTaskMiddleWare()
)
_ = common_router.message.middleware(
    middleware_for_adding_task.AddingMessageTaskMiddleWare()
)
