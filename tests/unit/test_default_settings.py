import pytest

from app.client_bot.modules.default_settings import apply_defaults_to_adv_setting
from app.client_bot.modules.default_settings.default_models.common_default import CampaignDefaultsV1
from app.modules.common_slaves.wildberries.models.models import AdvSetting
from app.modules.common_slaves.wildberries.models.wb_cabinet import WBCabinet
from app.modules.common_slaves.wildberries.models.enums import OrdersSourceForAutoMode
from app.modules.common_slaves.wildberries.models.fact_methods_enum import FactMethods
from app.modules.common_slaves.wildberries.models.models import BidderCoroutineType, BidderMode


pytestmark = pytest.mark.unit


def test_apply_defaults_to_adv_setting():
    # Создаем объект AdvSetting с отличными от дефолтных значениями
    adv_setting = AdvSetting(
        bidder_active=False,
        bidder_for_auto=True,
        bidder_mode=BidderMode.BY_POSITIONS,
        bot_active=False,
        bidder_coroutine_type=BidderCoroutineType.OLD_UPDATE_CPM_BIDDER,
        orders_source_for_auto_mode=OrdersSourceForAutoMode.ADV_SUM,
        sales_predict_method=FactMethods.DIRECT_SALES,
        auto_update_white_list=False,
        auto_update_target_place=False,
        target_ctr_mode=True,
        new_auto_min_ctr_mode=True,
        reset_place=True,
        max_place=None
    )
    wb_cabinet = WBCabinet(id=1, default_max_cpm=5000) # Mock WBCabinet
    adv_setting.wb_cabinet = wb_cabinet

    defaults_v1 = CampaignDefaultsV1()

    # Применяем дефолты
    apply_defaults_to_adv_setting(adv_setting, wb_cabinet)

    # Проверяем, что значения обновились на дефолтные
    assert adv_setting.bidder_active == defaults_v1.bidder_active
    assert adv_setting.bidder_for_auto == defaults_v1.bidder_for_auto
    assert adv_setting.bidder_mode == defaults_v1.bidder_mode
    # bot_active не входит в CampaignDefaultsV1 — apply_defaults не трогает его
    assert adv_setting.bot_active is False
    assert adv_setting.bidder_coroutine_type == defaults_v1.bidder_coroutine_type
    assert adv_setting.orders_source_for_auto_mode == defaults_v1.orders_source_for_auto_mode
    assert adv_setting.sales_predict_method == defaults_v1.sales_predict_method
    assert adv_setting.auto_update_white_list == defaults_v1.auto_update_white_list
    assert adv_setting.auto_update_target_place == defaults_v1.auto_update_target_place
    assert (
        adv_setting.auto_budget_watchdog_enabled
        == defaults_v1.auto_budget_watchdog_enabled
    )
    assert adv_setting.use_common_budget == defaults_v1.use_common_budget
    assert adv_setting.target_ctr_mode == defaults_v1.target_ctr_mode
    assert adv_setting.new_auto_min_ctr_mode == defaults_v1.new_auto_min_ctr_mode
    assert adv_setting.reset_place == defaults_v1.reset_place
    assert adv_setting.max_cpm == wb_cabinet.default_max_cpm # Check max_cpm update

    # Проверяем логику max_place (если был None, стал 1)
    assert adv_setting.max_place == 1

def test_apply_defaults_to_adv_setting_keeps_max_place():
    # Проверяем, что существующий max_place не меняется
    adv_setting = AdvSetting(max_place=10)
    wb_cabinet = WBCabinet(id=1, default_max_cpm=5000) # Mock WBCabinet
    adv_setting.wb_cabinet = wb_cabinet
    apply_defaults_to_adv_setting(adv_setting, wb_cabinet)
    assert adv_setting.max_place == 10
