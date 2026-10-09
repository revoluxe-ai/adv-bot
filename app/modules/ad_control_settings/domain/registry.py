"""
Versioned feature registry: supported scopes, schema versions, validation.

Unknown feature / unsupported scope => fail closed.
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass

from app.modules.ad_control_settings.domain.configured import (
    ConfiguredFeaturePayload,
    CpoDecreaseOnOverspendParamsV1,
    CpoIncreaseOnHeadroomParamsV1,
    CpoSafetyBoundsParamsV1,
    DrrPolicyParamsV1,
    DynamicDrrControlParamsV1,
)
from app.modules.ad_control_settings.domain.enums import (
    AdControlFeatureId,
    AdControlScope,
)
from app.modules.ad_control_settings.domain.min_data_sufficiency import (
    MinObservedDataSufficiencyRequirement,
    validate_min_observed_requirement,
)
from app.modules.ad_control_settings.domain.reason_codes import AdControlReasonCode


class FeatureValidationError(ValueError):
    """Fail-closed validation для configured payload."""


@dataclass(frozen=True, slots=True)
class FeatureDefinition:
    """Registry entry для одного AdControlFeatureId."""

    feature_id: AdControlFeatureId
    schema_version: int
    supported_scopes: frozenset[AdControlScope]
    validate_payload: Callable[[ConfiguredFeaturePayload], None]


def _validate_min_observed_field(value: object) -> None:
    if not isinstance(value, MinObservedDataSufficiencyRequirement):
        raise FeatureValidationError("min_data_sufficiency must be bounded enum")
    validate_min_observed_requirement(value)


def _validate_drr_policy(payload: ConfiguredFeaturePayload) -> None:
    if not isinstance(payload, DrrPolicyParamsV1):
        raise FeatureValidationError("DRR_POLICY requires DrrPolicyParamsV1")
    if payload.schema_version != 1:
        raise FeatureValidationError("unsupported DRR_POLICY schema_version")


def _validate_dynamic_drr(payload: ConfiguredFeaturePayload) -> None:
    if not isinstance(payload, DynamicDrrControlParamsV1):
        raise FeatureValidationError("DYNAMIC_DRR_CONTROL requires DynamicDrrControlParamsV1")
    if payload.max_effective_delta_percent < 0:
        raise FeatureValidationError("max_effective_delta_percent must be >= 0")


def _validate_cpo_increase(payload: ConfiguredFeaturePayload) -> None:
    if not isinstance(payload, CpoIncreaseOnHeadroomParamsV1):
        raise FeatureValidationError("CPO_INCREASE_ON_HEADROOM requires v1 payload")
    if payload.cooldown_ticks < 0:
        raise FeatureValidationError("cooldown_ticks must be >= 0")
    if payload.maximum_increase_per_iteration_rub < 0:
        raise FeatureValidationError("maximum_increase_per_iteration must be >= 0")
    _validate_min_observed_field(payload.min_data_sufficiency)


def _validate_cpo_decrease(payload: ConfiguredFeaturePayload) -> None:
    if not isinstance(payload, CpoDecreaseOnOverspendParamsV1):
        raise FeatureValidationError("CPO_DECREASE_ON_OVERSPEND requires v1 payload")
    if payload.cooldown_ticks < 0:
        raise FeatureValidationError("cooldown_ticks must be >= 0")
    _validate_min_observed_field(payload.min_data_sufficiency)


def _validate_cpo_bounds(payload: ConfiguredFeaturePayload) -> None:
    if not isinstance(payload, CpoSafetyBoundsParamsV1):
        raise FeatureValidationError("CPO_SAFETY_BOUNDS requires v1 payload")


FEATURE_REGISTRY: dict[AdControlFeatureId, FeatureDefinition] = {
    AdControlFeatureId.DRR_POLICY: FeatureDefinition(
        feature_id=AdControlFeatureId.DRR_POLICY,
        schema_version=1,
        supported_scopes=frozenset(
            {
                AdControlScope.SHOP,
                AdControlScope.CAMPAIGN,
                AdControlScope.PRODUCT,
            }
        ),
        validate_payload=_validate_drr_policy,
    ),
    AdControlFeatureId.DYNAMIC_DRR_CONTROL: FeatureDefinition(
        feature_id=AdControlFeatureId.DYNAMIC_DRR_CONTROL,
        schema_version=1,
        supported_scopes=frozenset({AdControlScope.SHOP, AdControlScope.CAMPAIGN}),
        validate_payload=_validate_dynamic_drr,
    ),
    AdControlFeatureId.CPO_INCREASE_ON_HEADROOM: FeatureDefinition(
        feature_id=AdControlFeatureId.CPO_INCREASE_ON_HEADROOM,
        schema_version=1,
        supported_scopes=frozenset({AdControlScope.SHOP, AdControlScope.CAMPAIGN}),
        validate_payload=_validate_cpo_increase,
    ),
    AdControlFeatureId.CPO_DECREASE_ON_OVERSPEND: FeatureDefinition(
        feature_id=AdControlFeatureId.CPO_DECREASE_ON_OVERSPEND,
        schema_version=1,
        supported_scopes=frozenset({AdControlScope.SHOP, AdControlScope.CAMPAIGN}),
        validate_payload=_validate_cpo_decrease,
    ),
    AdControlFeatureId.CPO_SAFETY_BOUNDS: FeatureDefinition(
        feature_id=AdControlFeatureId.CPO_SAFETY_BOUNDS,
        schema_version=1,
        supported_scopes=frozenset({AdControlScope.SHOP, AdControlScope.CAMPAIGN}),
        validate_payload=_validate_cpo_bounds,
    ),
}


def get_feature_definition(feature_id: AdControlFeatureId) -> FeatureDefinition:
    """Вернуть registry entry или fail closed."""
    try:
        return FEATURE_REGISTRY[feature_id]
    except KeyError:
        raise FeatureValidationError(f"unknown feature: {feature_id}") from None


def assert_scope_supported(
    feature_id: AdControlFeatureId,
    scope: AdControlScope,
) -> AdControlReasonCode | None:
    """None если scope поддерживается; иначе reason code."""
    definition = get_feature_definition(feature_id)
    if scope not in definition.supported_scopes:
        return AdControlReasonCode.UNSUPPORTED_SCOPE_FOR_FEATURE
    return None


def validate_feature_payload(
    feature_id: AdControlFeatureId,
    payload: ConfiguredFeaturePayload,
) -> None:
    """Validate payload against registry (deterministic, domain-owned)."""
    definition = get_feature_definition(feature_id)
    definition.validate_payload(payload)
    if payload.schema_version != definition.schema_version:
        raise FeatureValidationError(
            f"schema_version mismatch for {feature_id}: "
            f"expected {definition.schema_version}"
        )


def configuration_identity(
    scope: AdControlScope,
    feature_id: AdControlFeatureId,
    schema_version: int,
) -> tuple[AdControlScope, AdControlFeatureId, int]:
    """Versioned configuration identity для будущей persistence."""
    return (scope, feature_id, schema_version)
