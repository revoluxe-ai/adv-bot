"""cpd1 — digest domain capability projection only (no auth/principal)."""

from __future__ import annotations

from app.modules.wb_sky_control_plane.kernel.canonical_json import canonical_sha256
from app.modules.wb_sky_control_plane.models.capabilities import (
    CampaignCapabilitiesV1,
    CapabilityAssessment,
)

CAPABILITY_PROJECTION_DIGEST_VERSION = "cpd1"


def _capability_entry(assessment: CapabilityAssessment) -> dict[str, object]:
    return {
        "state": assessment.state.value,
        "reason_code": assessment.reason_code,
        "message": assessment.message,
    }


def build_capability_projection(
    capabilities_by_resource: dict[str, CampaignCapabilitiesV1],
) -> dict[str, object]:
    """Per-resource tri-state projection sorted by resource_id."""
    resources: dict[str, object] = {}
    for resource_id in sorted(capabilities_by_resource):
        caps = capabilities_by_resource[resource_id]
        resources[resource_id] = {
            "set_budget_policy": _capability_entry(caps.set_budget_policy),
            "set_sales_policy": _capability_entry(caps.set_sales_policy),
            "set_bid_control_policy": _capability_entry(caps.set_bid_control_policy),
        }
    return {
        "version": CAPABILITY_PROJECTION_DIGEST_VERSION,
        "resources": resources,
    }


def compute_capability_projection_digest(
    capabilities_by_resource: dict[str, CampaignCapabilitiesV1],
) -> str:
    """cpd1_: deterministic hash without permission_grants or principal."""
    return canonical_sha256(
        build_capability_projection(capabilities_by_resource),
        prefix="cpd1_",
    )
