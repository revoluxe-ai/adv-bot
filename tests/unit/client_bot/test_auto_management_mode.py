"""Compatibility-level tests for FREE/PAID campaign mode helpers."""

import pytest

from app.client_bot.user_interface.services.auto_management_mode import (
    apply_free_mode_transition,
    apply_free_defaults_settings_for_adv,
    apply_new_campaign_free_defaults,
    apply_paid_auto_management_transition,
    apply_paid_defaults_settings_for_adv,
)
from app.modules.common_slaves.wildberries.models.models import AdvSetting
from app.modules.common_slaves.wildberries.models.models import BidderCoroutineType
from app.modules.common_slaves.wildberries.models.wb_cabinet import WBCabinet
from app.modules.common_slaves.wildberries.models.white_list_mode import WhiteListMode

pytestmark = pytest.mark.unit


@pytest.fixture
def wb_cabinet() -> WBCabinet:
    return WBCabinet(id=1, default_max_cpm=5000)


def test_apply_paid_auto_management_mode_sets_only_paid_mode_fields(
    wb_cabinet: WBCabinet,
) -> None:
    adv_setting = AdvSetting(
        bot_active=False,
        automatic_version=2,
        white_list_mode=WhiteListMode.ABOVE_MIN_RATING,
        auto_update_white_list=True,
        auto_update_target_place=True,
        bidder_for_auto=True,
        bidder_active=False,
        max_place=5,
        max_cpm=2200,
        auto_update_minus_phrases=True,
    )

    apply_paid_auto_management_transition(adv_setting, wb_cabinet)

    assert adv_setting.bot_active is True
    assert adv_setting.automatic_version == 3
    assert adv_setting.white_list_mode == WhiteListMode.REPLACE_ON_TRIM
    assert adv_setting.auto_update_white_list is False
    assert adv_setting.auto_update_target_place is True
    assert adv_setting.bidder_for_auto is False
    assert adv_setting.bidder_active is True
    assert adv_setting.max_place == 5
    assert adv_setting.max_cpm == 2200
    assert adv_setting.auto_update_minus_phrases is True


def test_paid_auto_management_transition_keeps_current_bidder_path(
    wb_cabinet: WBCabinet,
) -> None:
    adv_setting = AdvSetting(
        bot_active=False,
        bidder_active=False,
        bidder_for_auto=True,
        automatic_version=2,
        bidder_coroutine_type=BidderCoroutineType.UPDATE_CLUSTER_BIDS,
    )

    apply_paid_auto_management_transition(adv_setting, wb_cabinet)

    assert adv_setting.bot_active is True
    assert adv_setting.bidder_active is True
    assert adv_setting.automatic_version == 3
    assert adv_setting.bidder_coroutine_type == BidderCoroutineType.UPDATE_CLUSTER_BIDS
    assert adv_setting.bidder_for_auto is False


def test_apply_free_auto_management_mode_sets_only_free_mode_fields(
    wb_cabinet: WBCabinet,
) -> None:
    adv_setting = AdvSetting(
        bot_active=True,
        automatic_version=3,
        white_list_mode=WhiteListMode.REPLACE_ON_TRIM,
        auto_update_white_list=True,
        auto_update_target_place=True,
        bidder_for_auto=True,
        bidder_active=True,
        max_place=11,
        max_cpm=3300,
        auto_update_minus_phrases=True,
    )

    apply_free_mode_transition(adv_setting, wb_cabinet)

    assert adv_setting.bot_active is False
    assert adv_setting.automatic_version == 2
    assert adv_setting.white_list_mode == WhiteListMode.ABOVE_MIN_RATING
    assert adv_setting.auto_update_white_list is False
    assert adv_setting.auto_update_target_place is False
    assert adv_setting.bidder_for_auto is False
    assert adv_setting.bidder_active is False
    assert adv_setting.max_place == 11
    assert adv_setting.max_cpm == 3300
    assert adv_setting.auto_update_minus_phrases is True


def test_free_transition_does_not_use_bot_active_as_bidder_path_selector(
    wb_cabinet: WBCabinet,
) -> None:
    adv_setting = AdvSetting(
        bot_active=False,
        bidder_active=True,
        bidder_for_auto=True,
        automatic_version=3,
        bidder_coroutine_type=BidderCoroutineType.UPDATE_CLUSTER_BIDS,
    )

    apply_free_mode_transition(adv_setting, wb_cabinet)

    assert adv_setting.bot_active is False
    assert adv_setting.bidder_active is False
    assert adv_setting.automatic_version == 2
    assert adv_setting.bidder_coroutine_type == BidderCoroutineType.UPDATE_CLUSTER_BIDS
    assert adv_setting.bidder_for_auto is False


def test_apply_new_campaign_free_defaults_apply_common_then_free(
    wb_cabinet: WBCabinet,
) -> None:
    adv_setting = AdvSetting(
        bot_active=True,
        automatic_version=3,
        white_list_mode=WhiteListMode.REPLACE_ON_TRIM,
        auto_update_white_list=True,
        auto_update_target_place=True,
        bidder_for_auto=True,
        bidder_active=False,
        max_place=None,
        max_cpm=None,
        auto_update_minus_phrases=True,
    )

    apply_new_campaign_free_defaults(adv_setting, wb_cabinet)

    assert adv_setting.bidder_active is False
    assert adv_setting.max_place == 1
    assert adv_setting.max_cpm == 5000
    assert adv_setting.auto_update_minus_phrases is False
    assert adv_setting.bot_active is False
    assert adv_setting.automatic_version == 2
    assert adv_setting.white_list_mode == WhiteListMode.ABOVE_MIN_RATING
    assert adv_setting.auto_update_white_list is False
    assert adv_setting.auto_update_target_place is False
    assert adv_setting.bidder_for_auto is False


def test_apply_new_campaign_free_defaults_keeps_existing_manual_limits(
    wb_cabinet: WBCabinet,
) -> None:
    adv_setting = AdvSetting(max_place=9, max_cpm=777)

    apply_new_campaign_free_defaults(adv_setting, wb_cabinet)

    assert adv_setting.max_place == 9
    assert adv_setting.max_cpm == 777


def test_apply_free_auto_management_mode_keeps_active_only_white_list_choice(
    wb_cabinet: WBCabinet,
) -> None:
    adv_setting = AdvSetting(
        white_list_mode=WhiteListMode.ACTIVE_ONLY_WHITE_LIST,
        automatic_version=3,
        bot_active=True,
    )

    apply_free_mode_transition(adv_setting, wb_cabinet)

    assert adv_setting.bot_active is False
    assert adv_setting.automatic_version == 2
    assert adv_setting.white_list_mode == WhiteListMode.ACTIVE_ONLY_WHITE_LIST


def test_apply_free_auto_management_mode_resets_paid_white_list_mode_to_safe_free_default(
    wb_cabinet: WBCabinet,
) -> None:
    adv_setting = AdvSetting(
        white_list_mode=WhiteListMode.REPLACE_ON_TRIM,
        automatic_version=3,
        bot_active=True,
    )

    apply_free_mode_transition(adv_setting, wb_cabinet)

    assert adv_setting.white_list_mode == WhiteListMode.ABOVE_MIN_RATING


def test_apply_paid_auto_management_transition_sets_bot_active_true(
    wb_cabinet: WBCabinet,
) -> None:
    adv_setting = AdvSetting(bot_active=False, bidder_active=False)

    apply_paid_auto_management_transition(adv_setting, wb_cabinet)

    assert adv_setting.bot_active is True
    assert adv_setting.bidder_active is True
    assert adv_setting.auto_update_target_place is True
    assert adv_setting.auto_update_white_list is False


def test_apply_free_mode_transition_sets_bot_active_false(
    wb_cabinet: WBCabinet,
) -> None:
    adv_setting = AdvSetting(
        bot_active=True,
        bidder_active=True,
        auto_update_target_place=True,
        auto_update_white_list=True,
    )

    apply_free_mode_transition(adv_setting, wb_cabinet)

    assert adv_setting.bot_active is False
    assert adv_setting.bidder_active is False
    assert adv_setting.auto_update_target_place is False
    assert adv_setting.auto_update_white_list is False


def test_backward_compatible_transition_wrappers_call_same_behavior(
    wb_cabinet: WBCabinet,
) -> None:
    adv_setting = AdvSetting(bot_active=False, bidder_active=False)

    apply_paid_defaults_settings_for_adv(adv_setting, wb_cabinet)
    assert adv_setting.bot_active is True
    assert adv_setting.bidder_active is True

    apply_free_defaults_settings_for_adv(adv_setting, wb_cabinet)
    assert adv_setting.bot_active is False
    assert adv_setting.bidder_active is False
