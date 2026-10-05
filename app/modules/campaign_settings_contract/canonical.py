"""Deterministic canonical snapshot для истории настроек.

Spec: campaign-settings-history.
Нормализация строится только из registry policy и не сериализует raw ORM object.
"""

from __future__ import annotations

import hashlib
import json
from collections.abc import Iterable, Mapping, Sequence
from dataclasses import dataclass
from datetime import date, datetime
from enum import Enum
from typing import Any, cast
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from .registry import (
    REGISTERED_SOURCES,
    ContractValidationError,
    FieldPolicy,
    HistoryPolicy,
    NormalizationPolicy,
)

SCHEMA_VERSION = 1
CanonicalizationError = ContractValidationError


@dataclass(frozen=True, slots=True)
class CampaignSettingsSources:
    """Complete raw settings aggregate before canonical normalization."""

    adv_setting: Mapping[str, object]
    keyword_settings: Sequence[Mapping[str, object]]
    auto_shelf_settings: Sequence[Mapping[str, object]]
    adv_time_settings: Mapping[str, object] | None
    adv_time_week_masks: Sequence[Mapping[str, object]]


@dataclass(frozen=True, slots=True)
class CanonicalSettingsSnapshot:
    """Canonical change-only state ready for ClickHouse history."""

    schema_version: int
    payload: Mapping[str, Any]
    payload_json: str
    state_hash: str

    @property
    def canonical_json(self) -> str:
        """Compatibility alias for the same exact canonical JSON bytes."""
        return self.payload_json


def _normalize_json_object(value: object) -> dict[str, Any]:
    """Deterministically normalize nested JSON-compatible object."""
    if not isinstance(value, Mapping):
        raise CanonicalizationError(
            f"expected JSON object, got {type(value).__name__}"
        )

    def normalize(item: object) -> Any:
        if item is None or type(item) in {bool, int, float, str}:
            return item
        if isinstance(item, Enum):
            return item.name
        if isinstance(item, datetime):
            return item.isoformat()
        if isinstance(item, date):
            return item.isoformat()
        if isinstance(item, Mapping):
            mapping = cast(Mapping[object, object], item)
            return {
                str(key): normalize(mapping[key])
                for key in sorted(mapping, key=str)
            }
        if isinstance(item, (list, tuple)):
            sequence = cast(Sequence[object], item)
            return [normalize(element) for element in sequence]
        raise CanonicalizationError(
            f"unsupported JSON value type: {type(item).__name__}"
        )

    mapping = cast(Mapping[object, object], value)
    return {
        str(key): normalize(mapping[key])
        for key in sorted(mapping, key=str)
    }


def normalize_value(policy: NormalizationPolicy, value: object) -> Any:
    """Low-level typed normalizer; field-specific allowlists are applied separately."""
    if value is None:
        return None
    if policy is NormalizationPolicy.BOOL:
        if type(value) is not bool:
            raise CanonicalizationError(
                f"expected bool, got {type(value).__name__}"
            )
        return value
    if policy is NormalizationPolicy.INT:
        if type(value) is not int:
            raise CanonicalizationError(
                f"expected int, got {type(value).__name__}"
            )
        return value
    if policy is NormalizationPolicy.FLOAT:
        if isinstance(value, bool) or not isinstance(value, (int, float)):
            raise CanonicalizationError(
                f"expected float, got {type(value).__name__}"
            )
        return float(value)
    if policy is NormalizationPolicy.STRING:
        if not isinstance(value, str):
            raise CanonicalizationError(
                f"expected str, got {type(value).__name__}"
            )
        return value
    if policy is NormalizationPolicy.ENUM:
        if isinstance(value, Enum):
            return value.name
        if isinstance(value, str) and value:
            return value
        raise CanonicalizationError(
            f"expected enum/string, got {type(value).__name__}"
        )
    if policy is NormalizationPolicy.INT_LIST:
        if not isinstance(value, (list, tuple, set, frozenset)):
            raise CanonicalizationError(
                f"expected int collection, got {type(value).__name__}"
            )
        normalized: list[int] = []
        iterable = cast(Iterable[object], value)
        for item in iterable:
            if type(item) is not int:
                raise CanonicalizationError(
                    f"expected int items, got {type(item).__name__}"
                )
            normalized.append(item)
        return sorted(set(normalized))
    if policy is NormalizationPolicy.STRING_LIST:
        if not isinstance(value, (list, tuple, set, frozenset)):
            raise CanonicalizationError(
                f"expected string collection, got {type(value).__name__}"
            )
        normalized_str: list[str] = []
        iterable = cast(Iterable[object], value)
        for item in iterable:
            if not isinstance(item, str):
                raise CanonicalizationError(
                    f"expected string items, got {type(item).__name__}"
                )
            normalized_str.append(item)
        return sorted(set(normalized_str))
    if policy is NormalizationPolicy.JSON_OBJECT:
        return _normalize_json_object(value)
    if policy is NormalizationPolicy.DATE:
        if not isinstance(value, date) or isinstance(value, datetime):
            raise CanonicalizationError(
                f"expected date, got {type(value).__name__}"
            )
        return value.isoformat()
    if policy is NormalizationPolicy.DATETIME:
        if not isinstance(value, datetime):
            raise CanonicalizationError(
                f"expected datetime, got {type(value).__name__}"
            )
        return value.isoformat()
    raise CanonicalizationError(
        f"unsupported normalization policy: {policy}"
    )


def _normalize_field(policy: FieldPolicy, value: object) -> Any:
    """Apply field-specific enum/literal/timezone contract on top of typed normalization."""
    if value is None:
        return None

    normalizer = policy.normalizer
    allowed = policy.allowed_values

    if normalizer == "enum_name":
        candidate = value.name if isinstance(value, Enum) else value
        if not isinstance(candidate, str) or candidate not in allowed:
            raise CanonicalizationError(
                f"unsupported enum value for {policy.name}: {candidate!r}"
            )
        return candidate

    if normalizer == "enum_value":
        candidate = value.value if isinstance(value, Enum) else value
        if not isinstance(candidate, str) or candidate not in allowed:
            raise CanonicalizationError(
                f"unsupported enum value for {policy.name}: {candidate!r}"
            )
        return candidate

    if normalizer == "literal_str":
        if not isinstance(value, str) or value not in allowed:
            raise CanonicalizationError(
                f"unsupported literal value for {policy.name}: {value!r}"
            )
        return value

    if normalizer == "timezone_name":
        if not isinstance(value, str) or not value:
            raise CanonicalizationError(
                f"invalid timezone for {policy.name}: {value!r}"
            )
        try:
            ZoneInfo(value)
        except ZoneInfoNotFoundError as exc:
            raise CanonicalizationError(
                f"unsupported timezone for {policy.name}: {value!r}"
            ) from exc
        return value

    return normalize_value(policy.normalization, value)


def _project_source(
    source_name: str,
    raw: Mapping[str, object],
    *,
    history: HistoryPolicy,
) -> dict[str, Any]:
    """Project one source using only explicit registry policy."""
    source = REGISTERED_SOURCES[source_name]
    required = [
        name
        for name, policy in source.fields.items()
        if policy.history is history
    ]
    missing = [name for name in required if name not in raw]
    if missing:
        raise CanonicalizationError(
            f"missing canonical fields for {source_name}: {sorted(missing)}"
        )

    return {
        field_name: _normalize_field(source.fields[field_name], raw[field_name])
        for field_name in required
    }


def _unique_sorted_rows(
    source_name: str,
    rows: Sequence[Mapping[str, object]],
    *,
    identity_field: str,
) -> list[dict[str, Any]]:
    """Sort nested rows and reject ambiguous duplicate canonical identity."""
    projected: list[dict[str, Any]] = []
    seen: set[object] = set()
    for raw in rows:
        metadata = _project_source(
            source_name,
            raw,
            history=HistoryPolicy.METADATA,
        )
        state = _project_source(
            source_name,
            raw,
            history=HistoryPolicy.STATE,
        )
        identity = metadata.get(identity_field)
        if identity is None:
            raise CanonicalizationError(
                f"missing canonical identity: {source_name}.{identity_field}"
            )
        if identity in seen:
            raise CanonicalizationError(
                "duplicate canonical identity: "
                f"{source_name}.{identity_field}; "
                f"duplicate canonical {identity_field}={identity!r}"
            )
        seen.add(identity)
        projected.append({**metadata, **state})
    return sorted(projected, key=lambda row: row[identity_field])


def _canonical_json(payload: Mapping[str, Any]) -> str:
    try:
        return json.dumps(
            payload,
            ensure_ascii=False,
            sort_keys=True,
            separators=(",", ":"),
            allow_nan=False,
        )
    except (TypeError, ValueError) as exc:
        raise CanonicalizationError(
            f"payload is not canonical-json serializable: {exc}"
        ) from exc


def canonical_state_hash(payload: Mapping[str, Any]) -> str:
    """SHA-256 of exact deterministic canonical JSON bytes."""
    encoded = _canonical_json(payload).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def _build_canonical_snapshot(
    *,
    adv_setting: Mapping[str, object],
    keywords: Sequence[Mapping[str, object]],
    auto_shelf: Sequence[Mapping[str, object]],
    time_settings: Mapping[str, object] | None,
    week_masks: Sequence[Mapping[str, object]],
    schema_version: int,
) -> CanonicalSettingsSnapshot:
    raw_identity = _project_source(
        "AdvSetting",
        adv_setting,
        history=HistoryPolicy.METADATA,
    )
    identity = dict(raw_identity)
    identity["adv_setting_id"] = identity.pop("id")
    identity["search_adv_id"] = identity.pop("_search_adv_id")

    campaign = _project_source(
        "AdvSetting",
        adv_setting,
        history=HistoryPolicy.STATE,
    )
    keyword_rows = _unique_sorted_rows(
        "KeywordSetting",
        keywords,
        identity_field="text",
    )
    shelf_rows = _unique_sorted_rows(
        "AutoShelfBidControlSettings",
        auto_shelf,
        identity_field="nmid",
    )

    schedule: dict[str, Any] | None = None
    if time_settings is not None:
        schedule = _project_source(
            "AdvTimeSettings",
            time_settings,
            history=HistoryPolicy.STATE,
        )
        schedule["week_mask"] = _unique_sorted_rows(
            "AdvTimeWeekMask",
            week_masks,
            identity_field="dow",
        )
    elif week_masks:
        raise CanonicalizationError(
            "week masks exist without AdvTimeSettings"
        )

    payload: dict[str, Any] = {
        "schema_version": schema_version,
        "identity": identity,
        "campaign": campaign,
        "keywords": keyword_rows,
        "auto_shelf_by_nmid": shelf_rows,
        "schedule": schedule,
    }
    payload_json = _canonical_json(payload)
    state_hash = hashlib.sha256(
        payload_json.encode("utf-8")
    ).hexdigest()
    return CanonicalSettingsSnapshot(
        schema_version=schema_version,
        payload=payload,
        payload_json=payload_json,
        state_hash=state_hash,
    )


def build_canonical_snapshot(
    *,
    adv_setting: Mapping[str, object],
    keywords: Sequence[Mapping[str, object]],
    auto_shelf: Sequence[Mapping[str, object]],
    time_settings: Mapping[str, object] | None,
    week_masks: Sequence[Mapping[str, object]],
) -> CanonicalSettingsSnapshot:
    """Low-level schema-current builder used by source adapters and focused unit tests."""
    return _build_canonical_snapshot(
        adv_setting=adv_setting,
        keywords=keywords,
        auto_shelf=auto_shelf,
        time_settings=time_settings,
        week_masks=week_masks,
        schema_version=SCHEMA_VERSION,
    )


def build_canonical_settings_snapshot(
    sources: CampaignSettingsSources,
    *,
    schema_version: int = SCHEMA_VERSION,
) -> CanonicalSettingsSnapshot:
    """Version-gated aggregate builder for history collector."""
    if schema_version != SCHEMA_VERSION:
        raise CanonicalizationError(
            f"unsupported schema_version={schema_version}; "
            f"supported={SCHEMA_VERSION}"
        )
    return _build_canonical_snapshot(
        adv_setting=sources.adv_setting,
        keywords=sources.keyword_settings,
        auto_shelf=sources.auto_shelf_settings,
        time_settings=sources.adv_time_settings,
        week_masks=sources.adv_time_week_masks,
        schema_version=schema_version,
    )
