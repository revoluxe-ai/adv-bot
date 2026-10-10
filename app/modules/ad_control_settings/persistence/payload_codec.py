"""
Сериализация configured payload ↔ JSONB (representation only).

Доменные инварианты — ``validate_feature_payload`` в registry.
"""

from __future__ import annotations

from decimal import Decimal
from typing import Any, cast

from app.modules.ad_control_settings.domain.configured import (
    ConfiguredFeaturePayload,
    CpoDecreaseOnOverspendParamsV1,
    CpoIncreaseOnHeadroomParamsV1,
    CpoSafetyBoundsParamsV1,
    DrrPolicyParamsV1,
    DynamicDrrControlParamsV1,
)
from app.modules.ad_control_settings.domain.enums import AdControlFeatureId
from app.modules.ad_control_settings.domain.min_data_sufficiency import (
    MinObservedDataSufficiencyRequirement,
)
from app.modules.ad_control_settings.domain.registry import (
    FeatureValidationError,
    get_feature_definition,
    validate_feature_payload,
)
from app.modules.product_control.domain.models import DrrProfile


class PayloadCodecError(ValueError):
    """Некорректный JSON representation configured payload."""


def _decimal_str(value: Decimal) -> str:
    return format(value, "f")


def _parse_decimal(raw: object, field: str) -> Decimal:
    if isinstance(raw, Decimal):
        return raw
    if isinstance(raw, (int, float, str)):
        try:
            return Decimal(str(raw))
        except Exception as exc:
            raise PayloadCodecError(f"{field}: invalid decimal") from exc
    raise PayloadCodecError(f"{field}: expected decimal scalar")


def _encode_drr_profile(profile: DrrProfile) -> dict[str, str]:
    return {
        "target_drr_percent": _decimal_str(profile.target_drr_percent),
        "max_drr_percent": _decimal_str(profile.max_drr_percent),
    }


def _decode_drr_profile(data: object) -> DrrProfile:
    if not isinstance(data, dict):
        raise PayloadCodecError("DRR profile must be an object")
    return DrrProfile(
        target_drr_percent=_parse_decimal(data.get("target_drr_percent"), "target_drr_percent"),
        max_drr_percent=_parse_decimal(data.get("max_drr_percent"), "max_drr_percent"),
    )


def encode_payload_json(
    feature_id: AdControlFeatureId,
    payload: ConfiguredFeaturePayload,
) -> dict[str, object]:
    """Сериализовать typed payload в JSON-совместимый dict."""
    validate_feature_payload(feature_id, payload)
    body: dict[str, object]
    if isinstance(payload, DrrPolicyParamsV1):
        body = {
            "kind": "DrrPolicyParamsV1",
            "schema_version": payload.schema_version,
            "profile": _encode_drr_profile(payload.profile),
        }
    elif isinstance(payload, DynamicDrrControlParamsV1):
        body = {
            "kind": "DynamicDrrControlParamsV1",
            "schema_version": payload.schema_version,
            "enabled": payload.enabled,
            "max_effective_delta_percent": _decimal_str(
                payload.max_effective_delta_percent
            ),
        }
    elif isinstance(payload, CpoIncreaseOnHeadroomParamsV1):
        body = {
            "kind": "CpoIncreaseOnHeadroomParamsV1",
            "schema_version": payload.schema_version,
            "minimum_headroom_rub": _decimal_str(payload.minimum_headroom_rub),
            "maximum_increase_per_iteration_rub": _decimal_str(
                payload.maximum_increase_per_iteration_rub
            ),
            "cooldown_ticks": payload.cooldown_ticks,
            "min_data_sufficiency": payload.min_data_sufficiency.value,
        }
    elif isinstance(payload, CpoDecreaseOnOverspendParamsV1):
        body = {
            "kind": "CpoDecreaseOnOverspendParamsV1",
            "schema_version": payload.schema_version,
            "maximum_decrease_per_iteration_rub": _decimal_str(
                payload.maximum_decrease_per_iteration_rub
            ),
            "cooldown_ticks": payload.cooldown_ticks,
            "min_data_sufficiency": payload.min_data_sufficiency.value,
        }
    elif isinstance(payload, CpoSafetyBoundsParamsV1):
        body = {
            "kind": "CpoSafetyBoundsParamsV1",
            "schema_version": payload.schema_version,
            "absolute_min_cpo_rub": (
                _decimal_str(payload.absolute_min_cpo_rub)
                if payload.absolute_min_cpo_rub is not None
                else None
            ),
            "absolute_max_cpo_rub": (
                _decimal_str(payload.absolute_max_cpo_rub)
                if payload.absolute_max_cpo_rub is not None
                else None
            ),
            "max_step_up_rub": (
                _decimal_str(payload.max_step_up_rub)
                if payload.max_step_up_rub is not None
                else None
            ),
            "max_step_down_rub": (
                _decimal_str(payload.max_step_down_rub)
                if payload.max_step_down_rub is not None
                else None
            ),
        }
    else:
        raise PayloadCodecError(f"unsupported payload type: {type(payload)!r}")
    return body


def decode_payload_json(
    feature_id: AdControlFeatureId,
    data: dict[str, object] | None,
) -> ConfiguredFeaturePayload | None:
    """Десериализовать JSONB в typed payload; ``None`` если data пуст."""
    if data is None:
        return None
    kind = data.get("kind")
    schema_raw = data.get("schema_version")
    if not isinstance(kind, str):
        raise PayloadCodecError("payload kind must be a string")
    if not isinstance(schema_raw, int):
        raise PayloadCodecError("schema_version must be int")

    definition = get_feature_definition(feature_id)
    if schema_raw != definition.schema_version:
        raise PayloadCodecError(
            f"schema_version {schema_raw} != registry {definition.schema_version}"
        )

    payload: ConfiguredFeaturePayload
    if kind == "DrrPolicyParamsV1":
        payload = DrrPolicyParamsV1(
            profile=_decode_drr_profile(data.get("profile")),
            schema_version=schema_raw,
        )
    elif kind == "DynamicDrrControlParamsV1":
        enabled = data.get("enabled")
        if not isinstance(enabled, bool):
            raise PayloadCodecError("enabled must be bool")
        payload = DynamicDrrControlParamsV1(
            enabled=enabled,
            max_effective_delta_percent=_parse_decimal(
                data.get("max_effective_delta_percent"),
                "max_effective_delta_percent",
            ),
            schema_version=schema_raw,
        )
    elif kind == "CpoIncreaseOnHeadroomParamsV1":
        min_raw = data.get("min_data_sufficiency")
        if not isinstance(min_raw, str):
            raise PayloadCodecError("min_data_sufficiency must be string enum")
        payload = CpoIncreaseOnHeadroomParamsV1(
            minimum_headroom_rub=_parse_decimal(
                data.get("minimum_headroom_rub"),
                "minimum_headroom_rub",
            ),
            maximum_increase_per_iteration_rub=_parse_decimal(
                data.get("maximum_increase_per_iteration_rub"),
                "maximum_increase_per_iteration_rub",
            ),
            cooldown_ticks=_as_int(data.get("cooldown_ticks"), "cooldown_ticks"),
            min_data_sufficiency=MinObservedDataSufficiencyRequirement(min_raw),
            schema_version=schema_raw,
        )
    elif kind == "CpoDecreaseOnOverspendParamsV1":
        min_raw = data.get("min_data_sufficiency")
        if not isinstance(min_raw, str):
            raise PayloadCodecError("min_data_sufficiency must be string enum")
        payload = CpoDecreaseOnOverspendParamsV1(
            maximum_decrease_per_iteration_rub=_parse_decimal(
                data.get("maximum_decrease_per_iteration_rub"),
                "maximum_decrease_per_iteration_rub",
            ),
            cooldown_ticks=_as_int(data.get("cooldown_ticks"), "cooldown_ticks"),
            min_data_sufficiency=MinObservedDataSufficiencyRequirement(min_raw),
            schema_version=schema_raw,
        )
    elif kind == "CpoSafetyBoundsParamsV1":
        payload = CpoSafetyBoundsParamsV1(
            absolute_min_cpo_rub=_optional_decimal(
                data.get("absolute_min_cpo_rub"),
                "absolute_min_cpo_rub",
            ),
            absolute_max_cpo_rub=_optional_decimal(
                data.get("absolute_max_cpo_rub"),
                "absolute_max_cpo_rub",
            ),
            max_step_up_rub=_optional_decimal(
                data.get("max_step_up_rub"),
                "max_step_up_rub",
            ),
            max_step_down_rub=_optional_decimal(
                data.get("max_step_down_rub"),
                "max_step_down_rub",
            ),
            schema_version=schema_raw,
        )
    else:
        raise PayloadCodecError(f"unknown payload kind: {kind!r}")

    try:
        validate_feature_payload(feature_id, payload)
    except FeatureValidationError as exc:
        raise PayloadCodecError(str(exc)) from exc
    return payload


def _as_int(raw: object, field: str) -> int:
    if isinstance(raw, bool) or not isinstance(raw, int):
        raise PayloadCodecError(f"{field} must be int")
    return raw


def _optional_decimal(raw: object, field: str) -> Decimal | None:
    if raw is None:
        return None
    return _parse_decimal(raw, field)


def payload_json_from_untyped(
    feature_id: AdControlFeatureId,
    raw: Any,
) -> ConfiguredFeaturePayload | None:
    """Принять JSONB из ORM (``dict``) и вернуть domain payload."""
    if raw is None:
        return None
    if not isinstance(raw, dict):
        raise PayloadCodecError("payload_json must be object or null")
    return decode_payload_json(feature_id, cast(dict[str, object], raw))
