"""Canonical payload/hash tests для spec ``campaign-settings-history``."""

from __future__ import annotations

import datetime as dt
from enum import Enum, IntEnum
from typing import Any

import pytest

from app.modules.campaign_settings_contract import (
    REGISTERED_SOURCES,
    CampaignSettingsSources,
    CanonicalizationError,
    HistoryPolicy,
    build_canonical_settings_snapshot,
    canonical_state_hash,
)

pytestmark = pytest.mark.unit


class _Strategy(Enum):
    """Test enum для enum_value normalization spec campaign-settings-history."""

    MIN_CPO = "MIN_CPO"


class _KeywordMode(IntEnum):
    """Test enum для enum_name normalization spec campaign-settings-history."""

    OFF = 0
    MIN_CPA = 1


def _default_value(normalizer: str, allowed_values: tuple[str, ...]) -> Any:
    """Создать валидное fixture-value по declared normalizer.

    Helper нужен tests spec campaign-settings-history, чтобы fixture автоматически
    покрывал все history-included fields и ломался при новом normalizer contract.
    """
    if normalizer == "typed_scalar":
        return None
    if normalizer == "sorted_unique_int_list":
        return []
    if normalizer in {"sorted_unique_str_list", "sorted_unique_str_list_or_null"}:
        return []
    if normalizer == "canonical_json_or_null":
        return None
    if normalizer in {"enum_name", "enum_value", "literal_str"}:
        return allowed_values[0]
    if normalizer == "date_iso_or_null":
        return dt.date(2026, 10, 3)
    if normalizer == "timezone_name":
        return "Europe/Moscow"
    raise AssertionError(f"test fixture lacks normalizer {normalizer!r}")


def _source_row(source_name: str, **overrides: Any) -> dict[str, Any]:
    """Собрать complete history-input row из registry.

    Spec campaign-settings-history требует missing field fail-closed; helper
    гарантирует complete fixture и позволяет точечно менять meaningful values.
    """
    source = REGISTERED_SOURCES[source_name]
    row = {
        name: _default_value(policy.normalizer, policy.allowed_values)
        for name, policy in source.fields.items()
        if policy.history is not HistoryPolicy.EXCLUDED
    }
    row.update(overrides)
    return row


def _base_sources() -> CampaignSettingsSources:
    """Собрать representative full aggregate для canonical tests.

    Fixture покрывает все пять registered sources spec campaign-settings-history
    и содержит reordered/set-like данные для проверки deterministic semantics.
    """
    adv = _source_row(
        "AdvSetting",
        id=101,
        adv_id=7001,
        wb_cabinet_id=55,
        name="Campaign A",
        nmids=[30, 10, 30],
        type=8,
        _search_adv_id=8001,
        black_phrases=["beta", "alpha", "alpha"],
        relevant_phrases=["two", "one"],
        strategy=_Strategy.MIN_CPO,
        target_ctr_mode_strategy="forward",
        card_ab_hold_mode="off",
    )
    keywords = [
        _source_row(
            "KeywordSetting",
            text="beta",
            hard_status=2,
            strategy_mode=_KeywordMode.MIN_CPA,
            relevant=True,
            target_place=4,
        ),
        _source_row(
            "KeywordSetting",
            text="alpha",
            hard_status=1,
            strategy_mode=_KeywordMode.OFF,
            relevant=False,
            target_place=2,
        ),
    ]
    shelf = [
        _source_row(
            "AutoShelfBidControlSettings",
            nmid=30,
            max_bid_minor=60_000,
            currency="RUB",
            min_bid_distance_minor=100,
            target_test_impressions=500,
            target_test_observation_minutes=60,
            test_share=0.1,
            retest_interval_days=7,
        ),
        _source_row(
            "AutoShelfBidControlSettings",
            nmid=10,
            max_bid_minor=40_000,
            currency="RUB",
            min_bid_distance_minor=100,
            target_test_impressions=500,
            target_test_observation_minutes=60,
            test_share=0.1,
            retest_interval_days=7,
        ),
    ]
    schedule = _source_row(
        "AdvTimeSettings",
        schedule_enabled=True,
        date_enabled=True,
        date_start=dt.date(2026, 10, 1),
        date_end=dt.date(2026, 10, 31),
        timezone="Europe/Moscow",
    )
    week_masks = [
        _source_row("AdvTimeWeekMask", dow=5, hours_mask=255),
        _source_row("AdvTimeWeekMask", dow=1, hours_mask=15),
    ]
    return CampaignSettingsSources(
        adv_setting=adv,
        keyword_settings=keywords,
        auto_shelf_settings=shelf,
        adv_time_settings=schedule,
        adv_time_week_masks=week_masks,
    )


def test_canonical_payload_v1_contains_all_registered_sections() -> None:
    """Spec campaign-settings-history: проверить canonical aggregate shape v1.

    Тест нужен, чтобы history хранила один settings aggregate, а не очередной
    partial snapshot одной ORM table.
    """
    snapshot = build_canonical_settings_snapshot(_base_sources())

    assert snapshot.schema_version == 1
    assert snapshot.payload["schema_version"] == 1
    assert snapshot.payload["identity"]["adv_setting_id"] == 101
    assert snapshot.payload["identity"]["search_adv_id"] == 8001
    assert snapshot.payload["identity"]["nmids"] == [10, 30]
    assert [row["text"] for row in snapshot.payload["keywords"]] == ["alpha", "beta"]
    assert [row["nmid"] for row in snapshot.payload["auto_shelf_by_nmid"]] == [10, 30]
    assert [row["dow"] for row in snapshot.payload["schedule"]["week_mask"]] == [1, 5]
    assert len(snapshot.state_hash) == 64
    assert snapshot.payload_json.startswith("{")


def test_reordered_rows_and_set_semantic_lists_have_same_hash() -> None:
    """Spec campaign-settings-history: доказать deterministic state identity.

    Тест нужен против false history changes из-за SQL row order, list duplicates
    или dict insertion order при логически одинаковых настройках.
    """
    first = _base_sources()
    second = CampaignSettingsSources(
        adv_setting={
            **dict(first.adv_setting),
            "nmids": [10, 30],
            "black_phrases": ["alpha", "beta"],
            "relevant_phrases": ["one", "two", "one"],
        },
        keyword_settings=list(reversed(first.keyword_settings)),
        auto_shelf_settings=list(reversed(first.auto_shelf_settings)),
        adv_time_settings=dict(first.adv_time_settings or {}),
        adv_time_week_masks=list(reversed(first.adv_time_week_masks)),
    )

    a = build_canonical_settings_snapshot(first)
    b = build_canonical_settings_snapshot(second)

    assert a.payload_json == b.payload_json
    assert a.state_hash == b.state_hash


def test_excluded_wb_and_runtime_fields_do_not_change_state_hash() -> None:
    """Spec campaign-settings-history: отделить desired settings от WB/runtime.

    Тест нужен, чтобы active_status/last_update/physical CPM не создавали новые
    settings snapshots при неизменной пользовательской конфигурации.
    """
    first = _base_sources()
    adv_a = dict(first.adv_setting)
    adv_b = dict(first.adv_setting)
    adv_a.update({"active_status": "started", "last_update": dt.datetime(2026, 10, 3), "cpm": 100})
    adv_b.update({"active_status": "paused", "last_update": dt.datetime(2026, 10, 4), "cpm": 999})

    a = build_canonical_settings_snapshot(
        CampaignSettingsSources(
            adv_setting=adv_a,
            keyword_settings=first.keyword_settings,
            auto_shelf_settings=first.auto_shelf_settings,
            adv_time_settings=first.adv_time_settings,
            adv_time_week_masks=first.adv_time_week_masks,
        )
    )
    b = build_canonical_settings_snapshot(
        CampaignSettingsSources(
            adv_setting=adv_b,
            keyword_settings=first.keyword_settings,
            auto_shelf_settings=first.auto_shelf_settings,
            adv_time_settings=first.adv_time_settings,
            adv_time_week_masks=first.adv_time_week_masks,
        )
    )

    assert a.state_hash == b.state_hash


def test_unknown_enum_value_fails_closed() -> None:
    """Spec campaign-settings-history: unknown enum не становится valid history.

    Тест нужен для unsupported-state policy: новое значение strategy требует
    contract/schema review вместо silent serialization.
    """
    sources = _base_sources()
    adv = dict(sources.adv_setting)
    adv["strategy"] = "FUTURE_UNKNOWN_STRATEGY"

    with pytest.raises(CanonicalizationError, match="unsupported enum value"):
        build_canonical_settings_snapshot(
            CampaignSettingsSources(
                adv_setting=adv,
                keyword_settings=sources.keyword_settings,
                auto_shelf_settings=sources.auto_shelf_settings,
                adv_time_settings=sources.adv_time_settings,
                adv_time_week_masks=sources.adv_time_week_masks,
            )
        )


def test_invalid_list_item_type_fails_closed() -> None:
    """Spec campaign-settings-history: type drift в nmids не угадывается.

    Тест нужен, чтобы строковый "10" не превращался автоматически в integer и
    не маскировал broken source contract.
    """
    sources = _base_sources()
    adv = dict(sources.adv_setting)
    adv["nmids"] = [10, "30"]

    with pytest.raises(CanonicalizationError, match="expected int items"):
        build_canonical_settings_snapshot(
            CampaignSettingsSources(
                adv_setting=adv,
                keyword_settings=sources.keyword_settings,
                auto_shelf_settings=sources.auto_shelf_settings,
                adv_time_settings=sources.adv_time_settings,
                adv_time_week_masks=sources.adv_time_week_masks,
            )
        )


def test_duplicate_nested_identity_fails_closed() -> None:
    """Spec campaign-settings-history: duplicate keyword/nmid identity запрещена.

    Тест нужен, чтобы canonical hash не зависел от arbitrary ordering или
    last-write-wins при corrupted duplicate nested settings.
    """
    sources = _base_sources()
    duplicate = dict(sources.keyword_settings[0])
    duplicate["text"] = sources.keyword_settings[1]["text"]

    with pytest.raises(CanonicalizationError, match="duplicate canonical text"):
        build_canonical_settings_snapshot(
            CampaignSettingsSources(
                adv_setting=sources.adv_setting,
                keyword_settings=[*sources.keyword_settings, duplicate],
                auto_shelf_settings=sources.auto_shelf_settings,
                adv_time_settings=sources.adv_time_settings,
                adv_time_week_masks=sources.adv_time_week_masks,
            )
        )


def test_schema_version_is_part_of_hash_and_unknown_version_refuses() -> None:
    """Spec campaign-settings-history: version bump является semantic boundary.

    Тест нужен, чтобы одинаковые fields под другой schema_version не имели тот же
    state identity, а unsupported reader не притворялся совместимым.
    """
    snapshot = build_canonical_settings_snapshot(_base_sources())
    payload_v2 = dict(snapshot.payload)
    payload_v2["schema_version"] = 2

    assert canonical_state_hash(payload_v2) != snapshot.state_hash
    with pytest.raises(CanonicalizationError, match="unsupported schema_version=2"):
        build_canonical_settings_snapshot(_base_sources(), schema_version=2)


def test_missing_history_field_fails_closed() -> None:
    """Spec campaign-settings-history: partial source row нельзя хэшировать.

    Тест нужен, чтобы collector failure/missing column не создавал misleading
    snapshot с guessed defaults.
    """
    sources = _base_sources()
    adv = dict(sources.adv_setting)
    del adv["bot_active"]

    with pytest.raises(CanonicalizationError, match="missing canonical fields"):
        build_canonical_settings_snapshot(
            CampaignSettingsSources(
                adv_setting=adv,
                keyword_settings=sources.keyword_settings,
                auto_shelf_settings=sources.auto_shelf_settings,
                adv_time_settings=sources.adv_time_settings,
                adv_time_week_masks=sources.adv_time_week_masks,
            )
        )
