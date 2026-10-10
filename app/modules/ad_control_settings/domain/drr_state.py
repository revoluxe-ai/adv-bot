"""
DRR semantic triple: configured policy, observed fact, derived control state.

Derived state не является user setting и не персистится как authority.
"""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal

from app.modules.ad_control_settings.domain.enums import DataSufficiency
from app.modules.ad_control_settings.domain.provenance import ProvenanceEntry


@dataclass(frozen=True, slots=True)
class ConfiguredTargetDrr:
    """Owner-controlled configured target (resolved policy)."""

    target_drr_percent: Decimal
    max_drr_percent: Decimal
    provenance: ProvenanceEntry


@dataclass(frozen=True, slots=True)
class ActualDrrObservation:
    """Observed factual DRR за measurement window (read-only fact port)."""

    actual_drr_percent: Decimal | None
    measurement_window_id: str
    data_sufficiency: DataSufficiency
    attribution_lag_days: int | None


@dataclass(frozen=True, slots=True)
class ShopEffectiveControlDrr:
    """Derived shop controller state (recomputable)."""

    effective_control_drr_percent: Decimal | None
    derived_from_configured: bool


@dataclass(frozen=True, slots=True)
class CampaignEffectiveControlDrr:
    """Resolved campaign-level effective control DRR after inheritance/override."""

    effective_control_drr_percent: Decimal | None
    inherits_shop_control: bool
    provenance: ProvenanceEntry
