"""Excel projection parity для campaign settings contract.

Spec: campaign-settings-history.
Доказывает, что human-facing Excel использует canonical registry membership,
а synthetic diagnostics не становятся настройками.
"""

from __future__ import annotations

import pytest

from app.client_bot.user_interface.services.adv_excel_roundtrip.schema import (
    EDITABLE_ADV_SETTING_COLUMNS,
    EDITABLE_SHELF_BID_CONTROL_COLUMNS,
    EXCEL_TEMPLATE_VERSION,
    ordered_edit_fields,
)
from app.client_bot.user_interface.services.cpm_target_place_workbook import (
    _HEADERS as TARGET_PLACE_HEADERS,
)
from app.modules.campaign_settings_contract import (
    REGISTERED_SOURCES,
    excel_alias,
    excel_editable_fields,
    ordered_shelf_editable_aliases,
)

pytestmark = pytest.mark.unit


def test_main_excel_edit_membership_is_registry_derived_and_v8_compatible() -> None:
    """Spec campaign-settings-history: v8 AdvSetting EDIT membership равен registry."""
    assert EXCEL_TEMPLATE_VERSION == 8
    assert EDITABLE_ADV_SETTING_COLUMNS == excel_editable_fields("AdvSetting")
    assert ordered_edit_fields()[: len(EDITABLE_ADV_SETTING_COLUMNS)] == sorted(
        EDITABLE_ADV_SETTING_COLUMNS
    )


def test_shelf_excel_alias_membership_and_order_match_registry() -> None:
    """Spec campaign-settings-history: shelf aliases идут из registry без второго whitelist."""
    assert EDITABLE_SHELF_BID_CONTROL_COLUMNS == ordered_shelf_editable_aliases()
    assert EDITABLE_SHELF_BID_CONTROL_COLUMNS == (
        "auto_shelf_max_bid_rub",
        "auto_shelf_test_share",
        "auto_shelf_target_test_impressions",
        "auto_shelf_target_test_observation_minutes",
        "auto_shelf_min_bid_distance_rub",
    )


def test_keyword_target_place_workbook_headers_are_registry_backed() -> None:
    """Spec campaign-settings-history: keyword workbook сохраняет текущий header contract."""
    assert TARGET_PLACE_HEADERS == [
        excel_alias("KeywordSetting", "id"),
        excel_alias("KeywordSetting", "text"),
        excel_alias("KeywordSetting", "target_place"),
        "target_place",
    ]
    assert TARGET_PLACE_HEADERS == [
        "keyword_id",
        "keyword",
        "current_target_place",
        "target_place",
    ]
    assert "target_place" in excel_editable_fields("KeywordSetting")


def test_excel_synthetic_diagnostics_are_not_canonical_settings_fields() -> None:
    """Spec campaign-settings-history: plan/fact/spend/export diagnostics не входят в settings."""
    synthetic = {
        "excel_template_version",
        "snapshot_at",
        "offer_id",
        "export_issue",
        "fact_orders_per_day",
        "fact_cost_per_order",
        "plan_orders_per_day",
        "plan_target_cost",
        "plan_max_cost",
        "orders_dev_pct",
        "cost_dev_pct",
        "deviation_score",
        "total_spend_auto",
        "total_spend_search",
        "total_spend_common",
    }
    all_source_fields = {
        field_name
        for source in REGISTERED_SOURCES.values()
        for field_name in source.fields
    }

    assert synthetic.isdisjoint(all_source_fields)
