"""Unit tests for common campaign defaults compatibility helpers."""

import pytest

from app.client_bot.modules.default_settings import (
    apply_common_defaults_settings_for_adv,
    apply_defaults_to_adv_setting,
)
from app.client_bot.modules.default_settings.default_models.common_default import (
    CampaignDefaultsV1,
)
from app.modules.common_slaves.wildberries.models.enums import OrdersSourceForAutoMode
from app.modules.common_slaves.wildberries.models.fact_methods_enum import FactMethods
from app.modules.common_slaves.wildberries.models.models import (
    AdvSetting,
    BidderCoroutineType,
    BidderMode,
)
from app.modules.common_slaves.wildberries.models.wb_cabinet import WBCabinet
from tests.factories import WBCabinetFactory, AdvSettingFactory

pytestmark = pytest.mark.unit


def test_apply_common_campaign_defaults() -> None:
    wb_cabinet = WBCabinetFactory.build(id=1,
                                        default_max_cpm=5000)
    adv_setting = AdvSettingFactory.build(
        bidder_active=False,
        bidder_mode=BidderMode.BY_AUTO_MAX_CPM,
        bidder_coroutine_type=BidderCoroutineType.OLD_UPDATE_CPM_BIDDER,
        orders_source_for_auto_mode=OrdersSourceForAutoMode.ADV_SUM,
        sales_predict_method=FactMethods.DIRECT_SALES,
        auto_update_minus_phrases=True,
        auto_budget_watchdog_enabled=False,
        use_common_budget=False,
        target_ctr_mode=True,
        new_auto_min_ctr_mode=True,
        reset_place=False,
        max_place=None,
        max_cpm=None,
        automatic_version=99,
        auto_update_white_list=True,
        auto_update_target_place=True,
        bidder_for_auto=True,
    )

    defaults_v1 = CampaignDefaultsV1()

    apply_common_defaults_settings_for_adv(adv_setting, wb_cabinet)

    assert adv_setting.bidder_active is False
    assert adv_setting.bidder_mode == defaults_v1.bidder_mode
    assert adv_setting.bidder_coroutine_type == defaults_v1.bidder_coroutine_type
    assert (
        adv_setting.orders_source_for_auto_mode
        == defaults_v1.orders_source_for_auto_mode
    )
    assert adv_setting.sales_predict_method == defaults_v1.sales_predict_method
    assert (
        adv_setting.auto_budget_watchdog_enabled
        == defaults_v1.auto_budget_watchdog_enabled
    )
    assert adv_setting.use_common_budget == defaults_v1.use_common_budget
    assert adv_setting.target_ctr_mode == defaults_v1.target_ctr_mode
    assert adv_setting.new_auto_min_ctr_mode == defaults_v1.new_auto_min_ctr_mode
    assert adv_setting.reset_place == defaults_v1.reset_place
    assert adv_setting.max_place == 1
    assert adv_setting.max_cpm == 5000




def test_apply_common_campaign_defaults_keeps_existing_manual_values() -> None:
    wb_cabinet = WBCabinetFactory.build(id=1,
                                        default_max_cpm=5000)
    adv_setting = AdvSettingFactory.build(max_place=10, max_cpm=777)

    apply_common_defaults_settings_for_adv(adv_setting, wb_cabinet)

    assert adv_setting.max_place == 10
    assert adv_setting.max_cpm == 777


def test_apply_defaults_to_adv_setting_is_backward_compatible_alias() -> None:
    adv_setting = AdvSettingFactory.build(max_place=None, max_cpm=None)
    wb_cabinet = WBCabinetFactory.build(id=1, default_max_cpm=5000)

    apply_defaults_to_adv_setting(adv_setting, wb_cabinet)

    assert adv_setting.max_place == 1
    assert adv_setting.max_cpm == 5000


def test_campaign_defaults_v1_disables_bidder_for_auto_for_safe_start() -> None:
    defaults_v1 = CampaignDefaultsV1()

    assert defaults_v1.bidder_for_auto is False
    assert defaults_v1.auto_update_minus_phrases is False


def test_apply_common_campaign_defaults_does_not_change_mode_specific_fields() -> None:
    wb_cabinet = WBCabinetFactory.build(id=1, default_max_cpm=5000)
    adv_setting = AdvSettingFactory.build(
        bidder_active=True,
        automatic_version=99,
        auto_update_white_list=True,
        auto_update_target_place=True,
        bidder_for_auto=True,
    )

    apply_common_defaults_settings_for_adv(adv_setting, wb_cabinet)

    assert adv_setting.bidder_active is True
    assert adv_setting.automatic_version == 99
    assert adv_setting.auto_update_white_list is True
    assert adv_setting.auto_update_target_place is True
    assert adv_setting.bidder_for_auto is True
    assert adv_setting.auto_update_minus_phrases is True
