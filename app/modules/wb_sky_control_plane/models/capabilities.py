"""Tri-state capabilities с deterministic reason codes."""

from __future__ import annotations

from pydantic import BaseModel

from app.modules.wb_sky_control_plane.models.enums import TriStateCapability


class CapabilityAssessment(BaseModel):
    """Оценка одной capability."""

    state: TriStateCapability
    reason_code: str
    message: str | None = None


class CampaignCapabilitiesV1(BaseModel):
    """Per-resource capabilities для bounded operations."""

    set_budget_policy: CapabilityAssessment
    set_sales_policy: CapabilityAssessment
    set_bid_control_policy: CapabilityAssessment

    def assessment_for_op(self, op: str) -> CapabilityAssessment | None:
        mapping = {
            "campaign.set_budget_policy": self.set_budget_policy,
            "campaign.set_sales_policy": self.set_sales_policy,
            "campaign.set_bid_control_policy": self.set_bid_control_policy,
        }
        return mapping.get(op)

    def is_write_eligible(self, op: str) -> bool:
        """UNKNOWN и INELIGIBLE не write-eligible."""
        assessment = self.assessment_for_op(op)
        return (
            assessment is not None
            and assessment.state == TriStateCapability.ELIGIBLE
        )
