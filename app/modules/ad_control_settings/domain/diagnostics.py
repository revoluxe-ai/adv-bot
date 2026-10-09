"""
Diagnostics / test mode contract (same resolver semantics, no writes).
"""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal

from app.modules.ad_control_settings.domain.campaign_ref import CampaignRef
from app.modules.ad_control_settings.domain.drr_state import (
    ActualDrrObservation,
    CampaignEffectiveControlDrr,
    ConfiguredTargetDrr,
    ShopEffectiveControlDrr,
)
from app.modules.ad_control_settings.domain.headroom import (
    BoundedCpoProposal,
    ShopHeadroomState,
)
from app.modules.ad_control_settings.domain.provenance import ProvenanceEntry
from app.modules.ad_control_settings.domain.reason_codes import AdControlReasonCode
from app.modules.ad_control_settings.domain.resolver_models import ResolvedFeaturePolicy


@dataclass(frozen=True, slots=True)
class AdControlDiagnosticsReportV1:
    """
    Read-only diagnostic snapshot для Owner test view.

    Production resolver + headroom pure functions MUST populate this structure.
    """

    shop_id: str
    campaign: CampaignRef | None
    configured_shop_features: tuple[ResolvedFeaturePolicy, ...]
    configured_campaign_overrides: tuple[ResolvedFeaturePolicy, ...]
    effective_features: tuple[ResolvedFeaturePolicy, ...]
    configured_target_drr: ConfiguredTargetDrr | None
    actual_drr: ActualDrrObservation | None
    shop_effective_control_drr: ShopEffectiveControlDrr | None
    campaign_effective_control_drr: CampaignEffectiveControlDrr | None
    shop_headroom: ShopHeadroomState | None
    current_max_cpo_rub: Decimal | None
    proposed_cpo: BoundedCpoProposal | None
    decision: str
    reason_codes: tuple[AdControlReasonCode, ...]
    blockers: tuple[str, ...]
    dry_run_diff_available: bool
    provenance_index: tuple[ProvenanceEntry, ...]
