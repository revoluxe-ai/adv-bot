"""Capabilities tri-state and whole-ChangeSet rejection tests."""

from __future__ import annotations

import pytest

from app.modules.wb_sky_control_plane.kernel.capabilities_eval import evaluate_capabilities
from app.modules.wb_sky_control_plane.kernel.validate import validate_changeset
from app.modules.wb_sky_control_plane.models.capabilities import CampaignCapabilitiesV1
from app.modules.wb_sky_control_plane.models.changeset import (
    BudgetPolicyPayload,
    CampaignResourceRef,
    ChangeSetV1,
    LogicalScopeV1,
    SetBudgetPolicyOperation,
    SetSalesPolicyOperation,
    SalesPolicyPayload,
)
from app.modules.wb_sky_control_plane.models.enums import (
    CampaignTopology,
    MappingStatus,
    PaymentTypeAuthority,
    TriStateCapability,
)
from app.modules.wb_sky_control_plane.models.snapshot import (
    CampaignClassificationV1,
    CampaignResourceSnapshotV1,
)

pytestmark = pytest.mark.unit


def _eligible_caps() -> CampaignCapabilitiesV1:
    snap = CampaignResourceSnapshotV1(
        resource_id="cmp_test",
        wb_cabinet_id=1,
        classification=CampaignClassificationV1(
            topology=CampaignTopology.AUTO_ONLY,
            payment_type=PaymentTypeAuthority.CPM,
        ),
        mapping_status=MappingStatus.OK,
        state_token="st1_abc",
    )
    return evaluate_capabilities(snap)


def test_unknown_classification_never_write_eligible() -> None:
    """UNKNOWN capability must fail closed."""
    snap = CampaignResourceSnapshotV1(
        resource_id="cmp_u",
        wb_cabinet_id=1,
        classification=CampaignClassificationV1(
            has_unknown_authoritative_fields=True,
            payment_type=PaymentTypeAuthority.UNKNOWN,
        ),
        mapping_status=MappingStatus.OK,
    )
    caps = evaluate_capabilities(snap)
    assert caps.set_budget_policy.state == TriStateCapability.UNKNOWN
    assert not caps.is_write_eligible("campaign.set_budget_policy")


def test_unknown_product_membership_never_write_eligible() -> None:
    snap = CampaignResourceSnapshotV1(
        resource_id="cmp_pm",
        wb_cabinet_id=1,
        classification=CampaignClassificationV1(
            topology=CampaignTopology.AUTO_ONLY,
            payment_type=PaymentTypeAuthority.CPM,
            has_unknown_authoritative_fields=True,
            reason_codes=["AUTO_LEG_UNKNOWN_FIELDS"],
        ),
        mapping_status=MappingStatus.OK,
    )
    caps = evaluate_capabilities(snap)
    assert caps.set_budget_policy.state == TriStateCapability.UNKNOWN


def test_one_invalid_operation_rejects_whole_changeset() -> None:
    """Single invalid op produces validation error for whole ChangeSet path."""
    resource_id = "cmp_test"
    snapshot = CampaignResourceSnapshotV1(
        resource_id=resource_id,
        wb_cabinet_id=1,
        classification=CampaignClassificationV1(
            topology=CampaignTopology.AUTO_ONLY,
            payment_type=PaymentTypeAuthority.CPM,
        ),
        mapping_status=MappingStatus.OK,
        state_token="st1_abc",
    )
    caps = _eligible_caps()
    changeset = ChangeSetV1(
        changeset_id="cs-x",
        scope=LogicalScopeV1(shop_id="shop-1"),
        operations=[
            SetBudgetPolicyOperation(
                operation_id="op-1",
                resource=CampaignResourceRef(resource_id=resource_id),
                payload=BudgetPolicyPayload(auto_budget_daily_limit=100),
            ),
            SetSalesPolicyOperation(
                operation_id="op-2",
                resource=CampaignResourceRef(resource_id="cmp_missing"),
                payload=SalesPolicyPayload(plan_for_sales_for_day=5),
            ),
        ],
    )
    errors = validate_changeset(
        changeset,
        {resource_id: snapshot},
        {resource_id: caps},
    )
    assert any(error.code == "RESOURCE_SNAPSHOT_MISSING" for error in errors)
