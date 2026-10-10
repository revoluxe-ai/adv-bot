"""
Configured policy payloads (owner-controlled), typed per feature.

Schema version привязан к registry entry; invariants в Python, не только JSON Schema.
"""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal

from app.modules.ad_control_settings.domain.min_data_sufficiency import (
    MinObservedDataSufficiencyRequirement,
)
from app.modules.product_control.domain.models import DrrProfile


@dataclass(frozen=True, slots=True)
class DrrPolicyParamsV1:
    """Configured target DRR policy (atomic profile)."""

    profile: DrrProfile
    schema_version: int = 1


@dataclass(frozen=True, slots=True)
class DynamicDrrControlParamsV1:
    """Параметры dynamic DRR / control pressure (без price actuation)."""

    enabled: bool
    max_effective_delta_percent: Decimal
    schema_version: int = 1


@dataclass(frozen=True, slots=True)
class CpoIncreaseOnHeadroomParamsV1:
    """Независимые параметы увеличения CPO при положительном headroom."""

    minimum_headroom_rub: Decimal
    maximum_increase_per_iteration_rub: Decimal
    cooldown_ticks: int
    min_data_sufficiency: MinObservedDataSufficiencyRequirement
    schema_version: int = 1


@dataclass(frozen=True, slots=True)
class CpoDecreaseOnOverspendParamsV1:
    """Независимые параметы уменьшения CPO при отрицательном headroom."""

    maximum_decrease_per_iteration_rub: Decimal
    cooldown_ticks: int
    min_data_sufficiency: MinObservedDataSufficiencyRequirement
    schema_version: int = 1


@dataclass(frozen=True, slots=True)
class CpoSafetyBoundsParamsV1:
    """Границы безопасности CPO (policy only, не production actuation)."""

    absolute_min_cpo_rub: Decimal | None
    absolute_max_cpo_rub: Decimal | None
    max_step_up_rub: Decimal | None
    max_step_down_rub: Decimal | None
    schema_version: int = 1


ConfiguredFeaturePayload = (
    DrrPolicyParamsV1
    | DynamicDrrControlParamsV1
    | CpoIncreaseOnHeadroomParamsV1
    | CpoDecreaseOnOverspendParamsV1
    | CpoSafetyBoundsParamsV1
)
