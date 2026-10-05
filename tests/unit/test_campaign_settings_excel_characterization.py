"""Characterization текущего Excel contract после registry wiring.

Spec: campaign-settings-history.
Фиксирует observable v8 membership/order, не требует ручных literal whitelist
в adapter code.
"""

from __future__ import annotations

import pytest

from app.client_bot.user_interface.services.adv_excel_roundtrip.schema import (
    EDITABLE_ADV_SETTING_COLUMNS,
    EDITABLE_SHELF_BID_CONTROL_COLUMNS,
    EXCEL_TEMPLATE_VERSION,
    READ_ONLY_ADV_COLUMNS,
)
from app.client_bot.user_interface.services.cpm_target_place_workbook import (
    _HEADERS as TARGET_PLACE_HEADERS,
)
from app.modules.campaign_settings_contract import (
    excel_editable_fields,
    excel_read_only_fields,
)

pytestmark = pytest.mark.unit


_EXPECTED_V8_ADV_EDITABLE = frozenset({
    "bot_active",
    "auto_shelf_bid_control_enabled",
    "max_cpm",
    "min_views_for_ml_predict",
    "clusters_mode",
    "target_ctr_mode",
    "hide_small_query_keywords",
    "bidder_coroutine_type",
    "target_ctr_mode_strategy",
    "reset_place",
    "exponent_predict_ctr",
    "bidder_step",
    "plan_for_sales_for_day",
    "target_price_for_order",
    "max_price_for_order",
    "bidder_for_auto",
    "auto_update_white_list",
    "auto_budget_watchdog_enabled",
    "auto_update_target_place",
    "auto_update_exponent",
    "rec_system_mode",
    "hide_zero_views_keywords",
    "auto_budget_daily_limit",
    "search_auto_budget_daily_limit",
    "use_common_budget",
    "common_budget_daily_limit",
    "auto_budget_total_limit",
    "search_auto_budget_total_limit",
    "common_budget_total_limit",
    "auto_common_budget",
    "auto_add_only_relevant_phrase",
    "orders_source_for_auto_mode",
    "predict_ctr_mode",
    "sales_predict_method",
    "aggressiveness",
    "keyword_calibration_max_step",
    "white_list_mode",
    "individual_keywords_target_place_mode",
    "target_position_mode",
    "strategy",
    "auto_update_strategy",
    "updater_common_bid_in_search_adv_active_status",
    "use_incremental_stats",
    "max_place",
    "substitute_fact_cpo_for_max",
    "raise_plan_on_promobonuses",
})


def test_excel_v8_editable_adv_fields_match_registry_and_legacy_behavior() -> None:
    """v8 AdvSetting EDIT membership remains exact while registry owns it."""
    assert EXCEL_TEMPLATE_VERSION == 8
    assert EDITABLE_ADV_SETTING_COLUMNS == _EXPECTED_V8_ADV_EDITABLE
    assert EDITABLE_ADV_SETTING_COLUMNS == excel_editable_fields("AdvSetting")


def test_excel_v8_shelf_edit_columns_keep_exact_order() -> None:
    """Human-facing shelf column order is unchanged."""
    assert EDITABLE_SHELF_BID_CONTROL_COLUMNS == (
        "auto_shelf_max_bid_rub",
        "auto_shelf_test_share",
        "auto_shelf_target_test_impressions",
        "auto_shelf_target_test_observation_minutes",
        "auto_shelf_min_bid_distance_rub",
    )


def test_keyword_target_place_workbook_headers_are_characterized() -> None:
    """Keyword target-place workbook retains its four current columns."""
    assert TARGET_PLACE_HEADERS == [
        "keyword_id",
        "keyword",
        "current_target_place",
        "target_place",
    ]


def test_adv_read_only_source_membership_is_registry_derived() -> None:
    """RO source-field membership has one authority instead of a second whitelist."""
    assert READ_ONLY_ADV_COLUMNS == excel_read_only_fields("AdvSetting")
    assert READ_ONLY_ADV_COLUMNS == frozenset(
        {"id", "adv_id", "_search_adv_id", "nmids"}
    )
