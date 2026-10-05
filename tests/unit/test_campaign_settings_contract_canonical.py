"""Canonical snapshot tests.

Spec: campaign-settings-history.
Доказывают deterministic normalization, schema-versioned hash и fail-closed
поведение для unsupported/ambiguous source state.
"""

from __future__ import annotations

from dataclasses import replace
from datetime import date
from enum import Enum

import pytest

import app.modules.campaign_settings_contract.canonical as canonical_module
from app.modules.campaign_settings_contract import (
    REGISTERED_SOURCES,
    ContractValidationError,
    HistoryPolicy,
    NormalizationPolicy,
    build_canonical_snapshot,
    normalize_value,
)

pytestmark = pytest.mark.unit


class _DemoEnum(Enum):
    FOO = 1


def _sample_value(field_policy) -> object:
    """Spec campaign-settings-history: строит валидное fixture-value из полной policy."""
    policy = field_policy.normalization
    field_name = field_policy.name
    if policy is NormalizationPolicy.INT:
        return 1
    if policy is NormalizationPolicy.FLOAT:
        return 1.5
    if policy is NormalizationPolicy.BOOL:
        return True
    if policy is NormalizationPolicy.STRING:
        if field_name == "timezone":
            return "Europe/Moscow"
        if field_policy.allowed_values:
            return field_policy.allowed_values[0]
        return field_name
    if policy is NormalizationPolicy.ENUM:
        return field_policy.allowed_values[0]
    if policy is NormalizationPolicy.INT_LIST:
        return [3, 1, 3]
    if policy is NormalizationPolicy.STRING_LIST:
        return ["beta", "alpha", "beta"]
    if policy is NormalizationPolicy.JSON_OBJECT:
        return {"b": 2, "a": 1}
    if policy is NormalizationPolicy.DATE:
        return date(2026, 1, 2)
    raise AssertionError(f"unexpected included normalization policy: {policy}")


def _raw(source_name: str, **overrides: object) -> dict[str, object]:
    """Spec campaign-settings-history: создаёт complete raw source для history-included fields."""
    result: dict[str, object] = {}
    for field_name, policy in REGISTERED_SOURCES[source_name].fields.items():
        if policy.history is HistoryPolicy.EXCLUDED:
            continue
        result[field_name] = _sample_value(policy)
    result.update(overrides)
    return result


def _build_default():
    """Spec campaign-settings-history: собирает representative complete campaign snapshot."""
    return build_canonical_snapshot(
        adv_setting=_raw(
            "AdvSetting",
            id=77,
            adv_id=123456,
            wb_cabinet_id=9,
            _search_adv_id=654321,
            name="Campaign",
            nmids=[300, 100, 300],
        ),
        keywords=[
            _raw("KeywordSetting", text="zeta", target_place=7),
            _raw("KeywordSetting", text="alpha", target_place=3),
        ],
        auto_shelf=[
            _raw("AutoShelfBidControlSettings", nmid=300),
            _raw("AutoShelfBidControlSettings", nmid=100),
        ],
        time_settings=_raw(
            "AdvTimeSettings",
            timezone="Europe/Moscow",
            date_start=date(2026, 1, 2),
            date_end=date(2026, 2, 3),
        ),
        week_masks=[
            _raw("AdvTimeWeekMask", dow=6, hours_mask=10),
            _raw("AdvTimeWeekMask", dow=1, hours_mask=20),
        ],
    )


def test_canonical_snapshot_has_version_payload_json_and_sha256() -> None:
    """Spec campaign-settings-history: snapshot несёт schema_version и hash canonical JSON."""
    snapshot = _build_default()

    assert snapshot.schema_version == 1
    assert snapshot.payload["schema_version"] == 1
    assert len(snapshot.state_hash) == 64
    assert snapshot.canonical_json.startswith('{"auto_shelf_by_nmid"')
    assert snapshot.payload["identity"]["nmids"] == [100, 300]


def test_reordering_nested_rows_and_set_like_lists_keeps_same_hash() -> None:
    """Spec campaign-settings-history: row/list order не создаёт ложную историю."""
    first = _build_default()
    second = build_canonical_snapshot(
        adv_setting=_raw(
            "AdvSetting",
            id=77,
            adv_id=123456,
            wb_cabinet_id=9,
            _search_adv_id=654321,
            name="Campaign",
            nmids=[100, 300],
            black_phrases=["alpha", "beta"],
        ),
        keywords=[
            _raw("KeywordSetting", text="alpha", target_place=3),
            _raw("KeywordSetting", text="zeta", target_place=7),
        ],
        auto_shelf=[
            _raw("AutoShelfBidControlSettings", nmid=100),
            _raw("AutoShelfBidControlSettings", nmid=300),
        ],
        time_settings=_raw(
            "AdvTimeSettings",
            timezone="Europe/Moscow",
            date_start=date(2026, 1, 2),
            date_end=date(2026, 2, 3),
        ),
        week_masks=[
            _raw("AdvTimeWeekMask", dow=1, hours_mask=20),
            _raw("AdvTimeWeekMask", dow=6, hours_mask=10),
        ],
    )
    third = build_canonical_snapshot(
        adv_setting=_raw(
            "AdvSetting",
            id=77,
            adv_id=123456,
            wb_cabinet_id=9,
            _search_adv_id=654321,
            name="Campaign",
            nmids=[300, 100, 300],
            black_phrases=["beta", "alpha", "beta"],
        ),
        keywords=list(reversed([
            _raw("KeywordSetting", text="zeta", target_place=7),
            _raw("KeywordSetting", text="alpha", target_place=3),
        ])),
        auto_shelf=list(reversed([
            _raw("AutoShelfBidControlSettings", nmid=300),
            _raw("AutoShelfBidControlSettings", nmid=100),
        ])),
        time_settings=_raw(
            "AdvTimeSettings",
            timezone="Europe/Moscow",
            date_start=date(2026, 1, 2),
            date_end=date(2026, 2, 3),
        ),
        week_masks=list(reversed([
            _raw("AdvTimeWeekMask", dow=6, hours_mask=10),
            _raw("AdvTimeWeekMask", dow=1, hours_mask=20),
        ])),
    )

    assert second.state_hash == third.state_hash
    assert second.canonical_json == third.canonical_json
    assert first.payload["keywords"][0]["text"] == "alpha"


def test_excluded_runtime_and_wb_fact_fields_do_not_change_hash() -> None:
    """Spec campaign-settings-history: excluded WB/runtime data не создают false snapshot."""
    base = _raw("AdvSetting", id=77, adv_id=123, wb_cabinet_id=9, _search_adv_id=0)
    first = build_canonical_snapshot(
        adv_setting={**base, "active_status": "active", "cpm": 100, "last_update": "old"},
        keywords=[],
        auto_shelf=[],
        time_settings=None,
        week_masks=[],
    )
    second = build_canonical_snapshot(
        adv_setting={**base, "active_status": "paused", "cpm": 999, "last_update": "new"},
        keywords=[],
        auto_shelf=[],
        time_settings=None,
        week_masks=[],
    )

    assert first.state_hash == second.state_hash


def test_schema_version_participates_in_hash(monkeypatch: pytest.MonkeyPatch) -> None:
    """Spec campaign-settings-history: semantic schema version меняет canonical state identity."""
    first = _build_default()
    monkeypatch.setattr(canonical_module, "SCHEMA_VERSION", 2)
    second = _build_default()

    assert second.schema_version == 2
    assert first.state_hash != second.state_hash


def test_enum_normalization_uses_symbolic_name() -> None:
    """Spec campaign-settings-history: enum сериализуется стабильным symbolic name."""
    assert normalize_value(NormalizationPolicy.ENUM, _DemoEnum.FOO) == "FOO"


@pytest.mark.parametrize(
    ("policy", "bad_value"),
    [
        (NormalizationPolicy.BOOL, 1),
        (NormalizationPolicy.INT, True),
        (NormalizationPolicy.ENUM, 7),
        (NormalizationPolicy.INT_LIST, [1, "2"]),
        (NormalizationPolicy.STRING_LIST, ["ok", 2]),
        (NormalizationPolicy.DATE, "2026-01-01"),
    ],
)
def test_unsupported_type_fails_closed(
    policy: NormalizationPolicy,
    bad_value: object,
) -> None:
    """Spec campaign-settings-history: unsupported typed value не записывается guessed."""
    with pytest.raises(ContractValidationError):
        normalize_value(policy, bad_value)


def test_duplicate_keyword_identity_fails_closed() -> None:
    """Spec campaign-settings-history: duplicate keyword text не нормализуется угадыванием."""
    with pytest.raises(ContractValidationError, match="duplicate canonical identity"):
        build_canonical_snapshot(
            adv_setting=_raw("AdvSetting"),
            keywords=[
                _raw("KeywordSetting", text="same"),
                _raw("KeywordSetting", text="same"),
            ],
            auto_shelf=[],
            time_settings=None,
            week_masks=[],
        )


def test_week_mask_without_time_settings_fails_closed() -> None:
    """Spec campaign-settings-history: orphan week-mask не создаёт частичный snapshot."""
    with pytest.raises(ContractValidationError, match="week masks exist without"):
        build_canonical_snapshot(
            adv_setting=_raw("AdvSetting"),
            keywords=[],
            auto_shelf=[],
            time_settings=None,
            week_masks=[_raw("AdvTimeWeekMask", dow=1)],
        )
