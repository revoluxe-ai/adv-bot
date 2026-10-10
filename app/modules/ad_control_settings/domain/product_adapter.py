"""
Adapter boundary к accepted Product Control DrrProfile semantics.

Не дублирует ProductControl persistence; читает уже разрешённый product outcome.
"""

from __future__ import annotations

from dataclasses import dataclass

from app.modules.ad_control_settings.domain.configured import DrrPolicyParamsV1
from app.modules.ad_control_settings.domain.enums import (
    AdControlFeatureId,
    AdControlScope,
    EffectiveSourceKind,
)
from app.modules.ad_control_settings.domain.provenance import ProvenanceEntry
from app.modules.ad_control_settings.domain.reason_codes import AdControlReasonCode
from app.modules.product_control.domain.enums import EffectiveControlOutcomeKind
from app.modules.product_control.domain.models import EffectiveControlResult


@dataclass(frozen=True, slots=True)
class ProductDrrPolicyAdapterSuccess:
    """Configured DRR policy с PRODUCT provenance."""

    params: DrrPolicyParamsV1
    provenance: ProvenanceEntry


@dataclass(frozen=True, slots=True)
class ProductDrrPolicyAdapterBlocked:
    """Product tier недоступен для DRR_POLICY inherit/override."""

    reason: AdControlReasonCode


ProductDrrPolicyAdapterResult = (
    ProductDrrPolicyAdapterSuccess | ProductDrrPolicyAdapterBlocked
)


class ProductDrrPolicyAdapter:
    """Маппинг EffectiveControlResolver → DrrPolicyParamsV1."""

    @staticmethod
    def from_effective_control(
        effective: EffectiveControlResult,
    ) -> ProductDrrPolicyAdapterResult:
        from app.modules.product_control.domain.models import (
            EffectiveControlBlocked,
            EffectiveControlSuccess,
        )

        if isinstance(effective, EffectiveControlBlocked):
            return ProductDrrPolicyAdapterBlocked(
                reason=AdControlReasonCode.PRODUCT_DRR_ADAPTER_BLOCKED,
            )

        assert isinstance(effective, EffectiveControlSuccess)
        if effective.kind != EffectiveControlOutcomeKind.ACTIVE_DRR_PROFILE:
            return ProductDrrPolicyAdapterBlocked(
                reason=AdControlReasonCode.PRODUCT_DRR_ADAPTER_BLOCKED,
            )
        if effective.profile is None:
            return ProductDrrPolicyAdapterBlocked(
                reason=AdControlReasonCode.INVALID_CONFIGURATION,
            )

        params = DrrPolicyParamsV1(profile=effective.profile)
        provenance = ProvenanceEntry(
            feature_id=AdControlFeatureId.DRR_POLICY,
            source_kind=EffectiveSourceKind.PRODUCT_OVERRIDE,
            source_scope=AdControlScope.PRODUCT,
            schema_version=1,
        )
        return ProductDrrPolicyAdapterSuccess(params=params, provenance=provenance)
