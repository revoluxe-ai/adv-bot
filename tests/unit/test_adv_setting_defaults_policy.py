"""Declarative field-policy tests for ``AdvSetting`` defaults and mode overlays."""

from __future__ import annotations

from enum import Enum

import pytest
from sqlalchemy.sql.sqltypes import Enum as SAEnum

from app.client_bot.modules.default_settings.adv_setting_policy import (
    AdvSettingDefaultsPolicy,
    CommonCampaignDefaultsPolicy,
    FREE_SAFE_WHITE_LIST_MODES,
    FieldPolicy,
    FreeModeDefaultsPolicy,
    PaidModeDefaultsPolicy,
    apply_common_defaults_settings_for_adv,
    apply_free_mode_transition,
    apply_free_defaults_settings_for_adv,
    apply_new_campaign_free_defaults,
    apply_paid_auto_management_transition,
    apply_paid_defaults_settings_for_adv,
)
from app.modules.common_slaves.wildberries.models.models import (
    AdvSetting,
    BidderCoroutineType,
)
from app.modules.common_slaves.wildberries.models.wb_cabinet import WBCabinet
from app.modules.common_slaves.wildberries.models.white_list_mode import WhiteListMode
from tests.factories import AdvSettingFactory, WBCabinetFactory

COMMON_EXPECTED_FIELDS = {
    "bidder_mode",
    "bidder_coroutine_type",
    "orders_source_for_auto_mode",
    "sales_predict_method",
    "auto_budget_watchdog_enabled",
    "use_common_budget",
    "target_ctr_mode",
    "new_auto_min_ctr_mode",
    "reset_place",
    "max_place",
    "max_cpm",
}

MODE_SPECIFIC_EXPECTED_FIELDS = {
    "bidder_active",
    "automatic_version",
    "white_list_mode",
    "auto_update_white_list",
    "auto_update_target_place",
    "bidder_for_auto",
    "auto_update_minus_phrases",
}

TRANSITION_CONTROL_FIELDS = {"bot_active"}

FREE_START_EXPECTED_FIELDS = COMMON_EXPECTED_FIELDS | MODE_SPECIFIC_EXPECTED_FIELDS
PAID_START_EXPECTED_FIELDS = COMMON_EXPECTED_FIELDS | MODE_SPECIFIC_EXPECTED_FIELDS

POLICIES = (
    CommonCampaignDefaultsPolicy,
    FreeModeDefaultsPolicy,
    PaidModeDefaultsPolicy,
)

pytestmark = pytest.mark.unit


@pytest.fixture
def adv_setting() -> AdvSetting:
    return AdvSettingFactory.build(max_place=None, max_cpm=None, white_list_mode=None)


@pytest.fixture
def wb_cabinet() -> WBCabinet:
    return WBCabinetFactory.build(id=1, default_max_cpm=300)


def test_field_policy_apply_sets_value_when_predicate_matches(
    adv_setting: AdvSetting,
    wb_cabinet: WBCabinet,
) -> None:
    adv_setting.bidder_active = True
    policy = FieldPolicy(
        field=AdvSetting.bidder_active,
        apply_if=lambda adv, cabinet: True,
        value=lambda adv, cabinet: False,
        reason="test",
    )

    policy.apply(adv_setting, wb_cabinet)

    assert adv_setting.bidder_active is False


def test_field_policy_apply_keeps_value_when_predicate_does_not_match(
    adv_setting: AdvSetting,
    wb_cabinet: WBCabinet,
) -> None:
    adv_setting.max_place = 9
    policy = FieldPolicy(
        field=AdvSetting.max_place,
        apply_if=lambda adv, cabinet: False,
        value=lambda adv, cabinet: 1,
        reason="test",
    )

    policy.apply(adv_setting, wb_cabinet)

    assert adv_setting.max_place == 9


@pytest.mark.parametrize("policy", POLICIES)
def test_policy_rules_are_valid(policy: type[AdvSettingDefaultsPolicy]) -> None:
    policy.validate_rules()


def test_common_defaults_do_not_overlap_with_mode_overlays() -> None:
    common = CommonCampaignDefaultsPolicy.field_names()
    free = FreeModeDefaultsPolicy.field_names()
    paid = PaidModeDefaultsPolicy.field_names()

    assert common.isdisjoint(free)
    assert common.isdisjoint(paid)


def test_free_and_paid_overlays_cover_same_mode_specific_fields() -> None:
    assert FreeModeDefaultsPolicy.field_names() == PaidModeDefaultsPolicy.field_names()


def test_policy_field_sets_match_expected_contract() -> None:
    common_fields = CommonCampaignDefaultsPolicy.field_names()
    free_fields = FreeModeDefaultsPolicy.field_names()
    paid_fields = PaidModeDefaultsPolicy.field_names()

    assert common_fields == COMMON_EXPECTED_FIELDS
    assert free_fields == MODE_SPECIFIC_EXPECTED_FIELDS
    assert paid_fields == MODE_SPECIFIC_EXPECTED_FIELDS
    assert "bot_active" not in common_fields
    assert "bot_active" not in free_fields
    assert "bot_active" not in paid_fields
    assert common_fields | free_fields == FREE_START_EXPECTED_FIELDS
    assert common_fields | paid_fields == PAID_START_EXPECTED_FIELDS


def test_transition_control_fields_are_not_part_of_policy_field_sets() -> None:
    covered = set().union(*(policy.field_names() for policy in POLICIES))

    assert covered.isdisjoint(TRANSITION_CONTROL_FIELDS)


def test_common_defaults_do_not_override_existing_manual_values(
    adv_setting: AdvSetting,
    wb_cabinet: WBCabinet,
) -> None:
    adv_setting.max_cpm = 777
    adv_setting.max_place = 9

    apply_common_defaults_settings_for_adv(adv_setting, wb_cabinet)

    assert adv_setting.max_cpm == 777
    assert adv_setting.max_place == 9


def test_common_defaults_fill_empty_manual_values(
    adv_setting: AdvSetting,
    wb_cabinet: WBCabinet,
) -> None:
    adv_setting.max_cpm = None
    adv_setting.max_place = None

    apply_common_defaults_settings_for_adv(adv_setting, wb_cabinet)

    assert adv_setting.max_cpm == wb_cabinet.default_max_cpm
    assert adv_setting.max_place == 1


def test_free_white_list_mode_value_keeps_above_min_rating(
    adv_setting: AdvSetting,
    wb_cabinet: WBCabinet,
) -> None:
    adv_setting.white_list_mode = WhiteListMode.ABOVE_MIN_RATING

    value = FreeModeDefaultsPolicy.rules[2].value(adv_setting, wb_cabinet)

    assert value == WhiteListMode.ABOVE_MIN_RATING


def test_free_white_list_mode_value_keeps_active_only_white_list(
    adv_setting: AdvSetting,
    wb_cabinet: WBCabinet,
) -> None:
    adv_setting.white_list_mode = WhiteListMode.ACTIVE_ONLY_WHITE_LIST

    value = FreeModeDefaultsPolicy.rules[2].value(adv_setting, wb_cabinet)

    assert value == WhiteListMode.ACTIVE_ONLY_WHITE_LIST


@pytest.mark.parametrize(
    "mode",
    [
        WhiteListMode.REPLACE_ON_TRIM,
        WhiteListMode.TAIL_TRIMMING,
        None,
    ],
)
def test_free_white_list_mode_value_resets_paid_or_unknown_mode_to_safe_free_default(
    adv_setting: AdvSetting,
    wb_cabinet: WBCabinet,
    mode: WhiteListMode | None,
) -> None:
    adv_setting.white_list_mode = mode

    value = FreeModeDefaultsPolicy.rules[2].value(adv_setting, wb_cabinet)

    assert value == WhiteListMode.ABOVE_MIN_RATING


def test_free_safe_white_list_modes_constant_matches_contract() -> None:
    assert FREE_SAFE_WHITE_LIST_MODES == {
        WhiteListMode.ABOVE_MIN_RATING,
        WhiteListMode.ACTIVE_ONLY_WHITE_LIST,
    }


def test_new_campaign_free_defaults_apply_common_then_free(
    adv_setting: AdvSetting,
    wb_cabinet: WBCabinet,
) -> None:
    apply_new_campaign_free_defaults(adv_setting, wb_cabinet)

    assert adv_setting.bidder_active is False
    assert adv_setting.max_cpm == wb_cabinet.default_max_cpm
    assert adv_setting.bot_active is False
    assert adv_setting.automatic_version == 2
    assert adv_setting.white_list_mode == WhiteListMode.ABOVE_MIN_RATING
    assert adv_setting.auto_update_white_list is False
    assert adv_setting.auto_update_target_place is False
    assert adv_setting.bidder_for_auto is False
    assert adv_setting.auto_update_minus_phrases is False


def test_common_plus_paid_defaults_apply_current_paid_start_behavior(
    adv_setting: AdvSetting,
    wb_cabinet: WBCabinet,
) -> None:
    apply_common_defaults_settings_for_adv(adv_setting, wb_cabinet)
    apply_paid_auto_management_transition(adv_setting, wb_cabinet)

    assert adv_setting.bidder_active is True
    assert adv_setting.bot_active is True
    assert adv_setting.automatic_version == 3
    assert adv_setting.bidder_coroutine_type == BidderCoroutineType.UPDATE_CLUSTER_BIDS
    assert adv_setting.white_list_mode == WhiteListMode.REPLACE_ON_TRIM
    assert adv_setting.auto_update_white_list is False
    assert adv_setting.auto_update_target_place is True
    assert adv_setting.bidder_for_auto is False
    assert adv_setting.auto_update_minus_phrases is True


def test_free_overlay_sets_only_free_mode_fields(
    adv_setting: AdvSetting,
    wb_cabinet: WBCabinet,
) -> None:
    adv_setting.bidder_active = True
    adv_setting.max_cpm = 777
    adv_setting.auto_update_minus_phrases = True

    apply_free_mode_transition(adv_setting, wb_cabinet)

    assert adv_setting.bot_active is False
    assert adv_setting.automatic_version == 2
    assert adv_setting.white_list_mode == WhiteListMode.ABOVE_MIN_RATING
    assert adv_setting.auto_update_white_list is False
    assert adv_setting.auto_update_target_place is False
    assert adv_setting.bidder_for_auto is False

    assert adv_setting.bidder_active is False
    assert adv_setting.max_cpm == 777
    assert adv_setting.auto_update_minus_phrases is False


def test_transition_wrappers_keep_backward_compatible_behavior(
    adv_setting: AdvSetting,
    wb_cabinet: WBCabinet,
) -> None:
    apply_paid_defaults_settings_for_adv(adv_setting, wb_cabinet)
    assert adv_setting.bot_active is True
    assert adv_setting.bidder_active is True

    apply_free_defaults_settings_for_adv(adv_setting, wb_cabinet)
    assert adv_setting.bot_active is False
    assert adv_setting.bidder_active is False


def _expected_python_type(rule: FieldPolicy) -> type[object] | tuple[type[object], ...]:
    column = rule.field.property.columns[0]
    column_type = column.type

    enum_class = getattr(column_type, "enum_class", None)
    if enum_class is not None:
        return enum_class

    if isinstance(column_type, SAEnum):
        enum_args = tuple(
            arg for arg in getattr(column_type, "enums", ()) if isinstance(arg, str)
        )
        if enum_args:
            return str
        raise AssertionError(
            f"Cannot infer enum python type for {rule.field_name}: {column_type!r}"
        )

    try:
        python_type = column_type.python_type
    except NotImplementedError as exc:
        raise AssertionError(
            f"Cannot infer python_type for {rule.field_name}: {column_type!r}"
        ) from exc

    if python_type is bool:
        return bool
    if python_type is int:
        return int
    if python_type is float:
        return (int, float)
    if python_type is str:
        return str
    if isinstance(python_type, type) and issubclass(python_type, Enum):
        return python_type
    return python_type


def test_policy_values_match_adv_setting_column_types() -> None:
    adv_setting = AdvSettingFactory.build(
        max_place=None,
        max_cpm=None,
        white_list_mode=None,
    )
    wb_cabinet = WBCabinetFactory.build(default_max_cpm=5000)

    for policy_cls in POLICIES:
        for rule in policy_cls.rules:
            value = rule.value(adv_setting, wb_cabinet)
            column = rule.field.property.columns[0]

            if value is None:
                assert column.nullable, rule.field_name
                continue

            expected_type = _expected_python_type(rule)
            assert isinstance(value, expected_type), (
                rule.field_name,
                value,
                type(value),
                expected_type,
            )
