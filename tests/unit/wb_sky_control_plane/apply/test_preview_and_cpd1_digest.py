"""pd1/cpd1 determinism tests."""

from __future__ import annotations

import pytest

from app.modules.wb_sky_control_plane.apply.digest.capability_projection_digest import (
    compute_capability_projection_digest,
)
from app.modules.wb_sky_control_plane.apply.digest.preview_digest import (
    compute_preview_digest,
)
from app.modules.wb_sky_control_plane.models.capabilities import (
    CampaignCapabilitiesV1,
    CapabilityAssessment,
)
from app.modules.wb_sky_control_plane.models.enums import (
    DryRunStatus,
    TriStateCapability,
)
from app.modules.wb_sky_control_plane.models.plan import (
    PlanEffectV1,
    PlanV1,
    SemanticDiffEntryV1,
)

pytestmark = pytest.mark.unit


def _eligible() -> CapabilityAssessment:
    return CapabilityAssessment(
        state=TriStateCapability.ELIGIBLE,
        reason_code="OK",
        message=None,
    )


def test_cpd1_stable_and_prefix() -> None:
    caps = {
        "cmp_a": CampaignCapabilitiesV1(
            set_budget_policy=_eligible(),
            set_sales_policy=_eligible(),
            set_bid_control_policy=_eligible(),
        )
    }
    d1 = compute_capability_projection_digest(caps)
    d2 = compute_capability_projection_digest(caps)
    assert d1 == d2
    assert d1.startswith("cpd1_")


def test_pd1_includes_cpd1_and_plan_effects() -> None:
    caps = {
        "cmp_a": CampaignCapabilitiesV1(
            set_budget_policy=_eligible(),
            set_sales_policy=_eligible(),
            set_bid_control_policy=_eligible(),
        )
    }
    cpd1 = compute_capability_projection_digest(caps)
    diff = SemanticDiffEntryV1(
        field_path="budget.auto_budget_daily_limit",
        resource_id="cmp_a",
        intent="set",
        current=1,
        desired=2,
        normalized=2,
    )
    plan = PlanV1(
        effects=[
            PlanEffectV1(
                resource_id="cmp_a",
                operation="campaign.set_budget_policy",
                operation_index=0,
                semantic_changes=[diff],
            )
        ]
    )
    pd1 = compute_preview_digest(
        status=DryRunStatus.OK,
        semantic_digest="sd1_abc",
        state_tokens={"cmp_a": "st1_xyz"},
        capability_projection_digest=cpd1,
        plan=plan,
        diffs=[diff],
    )
    assert pd1.startswith("pd1_")
    pd1_again = compute_preview_digest(
        status=DryRunStatus.OK,
        semantic_digest="sd1_abc",
        state_tokens={"cmp_a": "st1_xyz"},
        capability_projection_digest=cpd1,
        plan=plan,
        diffs=[diff],
    )
    assert pd1 == pd1_again
