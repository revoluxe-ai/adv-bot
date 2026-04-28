"""Проверка: editable поля Excel должны иметь UI-сценарий изменения."""

from __future__ import annotations

from pathlib import Path

import pytest

from app.client_bot.user_interface.services.adv_excel_roundtrip.schema import (
    EDITABLE_ADV_SETTING_COLUMNS,
)


UI_HANDLER_BY_FIELD: dict[str, str] = {
    "bot_active": "app/client_bot/user_interface/handlers/adv_setting.py",
    "max_cpm": "app/client_bot/user_interface/handlers/cpm_builder.py",
    "min_views_for_ml_predict": "app/client_bot/user_interface/handlers/min_views_for_ml_predict_ctr.py",
    "clusters_mode": "app/client_bot/user_interface/handlers/clusters.py",
    "target_ctr_mode": "app/client_bot/user_interface/handlers/strategy_setting.py",
    "hide_small_query_keywords": "app/client_bot/user_interface/handlers/keyword_settings.py",
    "bidder_coroutine_type": "app/client_bot/user_interface/handlers/bidder_coroutine_type_toggle/handlers.py",
    "target_ctr_mode_strategy": "app/client_bot/user_interface/handlers/strategy_setting.py",
    "reset_place": "app/client_bot/user_interface/handlers/reset_place_setting.py",
    "exponent_predict_ctr": "app/modules/predict_ctr_exponent_settings/telegram/handlers.py",
    "bidder_step": "app/modules/bidder_step_setting/telegram_handler.py",
    "plan_for_sales_for_day": "app/modules/sales_plan_settings/telegram/setting_handlers/change_plan_for_sales_for_day.py",
    "target_price_for_order": "app/modules/sales_plan_settings/telegram/setting_handlers/change_target_price_for_order.py",
    "max_price_for_order": "app/modules/sales_plan_settings/telegram/setting_handlers/change_max_price_for_order.py",
    "bidder_for_auto": "app/modules/bidder_auto_mode/handlers.py",
    "auto_update_white_list": "app/modules/shop_runner/service_manager/old_modules/setting_auto_updater/modules/white_list_updater/auto_white_list_updater/telegram/handlers.py",
    "auto_budget_watchdog_enabled": "app/client_bot/user_interface/handlers/auto_budget_watchdog_toggle.py",
    "auto_update_target_place": "app/modules/shop_runner/service_manager/old_modules/auto_updater_target_place/telegram/handlers.py",
    "auto_update_exponent": "app/client_bot/user_interface/handlers/auto_update_exponent_toggle.py",
    "rec_system_mode": "app/client_bot/user_interface/handlers/rec_system_mode_toggle.py",
    "hide_zero_views_keywords": "app/modules/hide_zero_views_toggle/telegram/handlers.py",
    "auto_budget_daily_limit": "app/client_bot/user_interface/handlers/campaign_activity.py",
    "search_auto_budget_daily_limit": "app/client_bot/user_interface/handlers/campaign_activity.py",
    "use_common_budget": "app/client_bot/user_interface/handlers/common_budget_mode_toggle.py",
    "common_budget_daily_limit": "app/client_bot/user_interface/handlers/campaign_activity.py",
    "auto_add_only_relevant_phrase": "app/client_bot/user_interface/handlers/auto_add_only_relevant_phrase_toggle.py",
    "orders_source_for_auto_mode": "app/client_bot/user_interface/handlers/orders_source_toggle.py",
    "predict_ctr_mode": "app/client_bot/user_interface/handlers/predict_ctr_mode_toggle.py",
    "sales_predict_method": "app/client_bot/user_interface/handlers/sales_predict_method_toggle.py",
    "automatic_version": "app/modules/shop_runner/service_manager/auto_updater_version_toggle/telegram/handlers.py",
    "white_list_mode": "app/client_bot/user_interface/handlers/white_list_mode_toggle.py",
    "individual_keywords_target_place_mode": "app/client_bot/user_interface/handlers/individual_keywords_target_place_toggle.py",
    "target_position_mode": "app/client_bot/user_interface/handlers/target_position_mode_toggle.py",
    "strategy": "app/client_bot/user_interface/handlers/strategy_setting.py",
    "auto_update_strategy": "app/client_bot/user_interface/handlers/strategy_setting.py",
    "updater_common_bid_in_search_adv_active_status": "app/client_bot/user_interface/handlers/common_bid_toggle.py",
    "use_incremental_stats": "app/client_bot/user_interface/handlers/incremental_stats_toggle.py",
    "max_place": "app/client_bot/user_interface/handlers/cpm_builder.py",
}


@pytest.mark.unit
def test_excel_editable_fields_match_ui_mapping() -> None:
    assert set(EDITABLE_ADV_SETTING_COLUMNS) == set(UI_HANDLER_BY_FIELD)


@pytest.mark.unit
def test_ui_mapping_files_exist() -> None:
    for path in UI_HANDLER_BY_FIELD.values():
        assert Path(path).exists(), f"UI handler not found: {path}"
