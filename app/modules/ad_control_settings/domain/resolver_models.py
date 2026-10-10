"""Input/output models для AdControlSettingsResolver."""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass

from app.modules.ad_control_settings.domain.campaign_ref import CampaignRef
from app.modules.ad_control_settings.domain.configured import ConfiguredFeaturePayload
from app.modules.ad_control_settings.domain.enums import (
    AdControlFeatureId,
    AdControlFeatureMode,
    ControlPathKind,
    HierarchicalEnrollment,
    ShopFeatureActivation,
)
from app.modules.ad_control_settings.domain.product_adapter import (
    ProductDrrPolicyAdapterResult,
)
from app.modules.ad_control_settings.domain.provenance import ProvenanceEntry
from app.modules.ad_control_settings.domain.reason_codes import AdControlReasonCode


@dataclass(frozen=True, slots=True)
class ShopFeatureSlot:
    """Shop-level configured policy slot."""

    activation: ShopFeatureActivation
    payload: ConfiguredFeaturePayload | None


@dataclass(frozen=True, slots=True)
class CampaignFeatureSlot:
    """Campaign-level mode + optional override payload."""

    mode: AdControlFeatureMode
    payload: ConfiguredFeaturePayload | None


@dataclass(frozen=True, slots=True)
class ResolverContext:
    """Pure resolver input (configured only, no I/O)."""

    enrollment: HierarchicalEnrollment
    control_path: ControlPathKind
    shop_id: str
    shop_features: Mapping[AdControlFeatureId, ShopFeatureSlot]
    campaign: CampaignRef
    campaign_features: Mapping[AdControlFeatureId, CampaignFeatureSlot]
    product_drr: ProductDrrPolicyAdapterResult | None = None


@dataclass(frozen=True, slots=True)
class ResolvedFeaturePolicy:
    """Effective configured policy slice для одного feature."""

    feature_id: AdControlFeatureId
    active: bool
    payload: ConfiguredFeaturePayload | None
    provenance: ProvenanceEntry
    reason_codes: tuple[AdControlReasonCode, ...]


@dataclass(frozen=True, slots=True)
class ResolverBlocked:
    """Hierarchical resolver fail-closed."""

    reason_codes: tuple[AdControlReasonCode, ...]
    blockers: tuple[str, ...]
