"""Tri-state capability evaluation (fail-closed on UNKNOWN)."""

from __future__ import annotations

from app.modules.wb_sky_control_plane.models.capabilities import (
    CampaignCapabilitiesV1,
    CapabilityAssessment,
)
from app.modules.wb_sky_control_plane.models.enums import (
    MappingStatus,
    PaymentTypeAuthority,
    TriStateCapability,
)
from app.modules.wb_sky_control_plane.models.snapshot import CampaignResourceSnapshotV1


def _unknown(reason_code: str, message: str) -> CapabilityAssessment:
    return CapabilityAssessment(
        state=TriStateCapability.UNKNOWN,
        reason_code=reason_code,
        message=message,
    )


def _ineligible(reason_code: str, message: str) -> CapabilityAssessment:
    return CapabilityAssessment(
        state=TriStateCapability.INELIGIBLE,
        reason_code=reason_code,
        message=message,
    )


def _eligible(reason_code: str = "OK") -> CapabilityAssessment:
    return CapabilityAssessment(
        state=TriStateCapability.ELIGIBLE,
        reason_code=reason_code,
        message=None,
    )


def evaluate_capabilities(snapshot: CampaignResourceSnapshotV1) -> CampaignCapabilitiesV1:
    """Deterministic tri-state capabilities with reason codes."""
    if snapshot.mapping_status != MappingStatus.OK:
        base = _unknown("MAPPING_BROKEN", "WB mapping broken or missing")
        return CampaignCapabilitiesV1(
            set_budget_policy=base,
            set_sales_policy=base,
            set_bid_control_policy=base,
        )

    if snapshot.classification.has_unknown_authoritative_fields:
        base = _unknown(
            "AUTHORITATIVE_UNKNOWN",
            "Missing/unknown authoritative WB fields",
        )
        return CampaignCapabilitiesV1(
            set_budget_policy=base,
            set_sales_policy=base,
            set_bid_control_policy=base,
        )

    if snapshot.classification.payment_type != PaymentTypeAuthority.CPM:
        base = _ineligible(
            "UNSUPPORTED_PAYMENT_TYPE",
            "A1 supports CPM authoritative campaigns only",
        )
        return CampaignCapabilitiesV1(
            set_budget_policy=base,
            set_sales_policy=base,
            set_bid_control_policy=base,
        )

    return CampaignCapabilitiesV1(
        set_budget_policy=_eligible("BUDGET_POLICY_SUPPORTED"),
        set_sales_policy=_eligible("SALES_POLICY_SUPPORTED"),
        set_bid_control_policy=_eligible("BID_CONTROL_POLICY_SUPPORTED"),
    )
