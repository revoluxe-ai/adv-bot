"""semantic_digest sd1 and state_token st1 determinism tests."""

from __future__ import annotations

import copy

import pytest

from app.modules.wb_sky_control_plane.kernel.canonical_json import canonical_sha256
from app.modules.wb_sky_control_plane.kernel.semantic_digest import (
    build_semantic_projection,
    compute_semantic_digest,
)
from app.modules.wb_sky_control_plane.kernel.state_token import (
    build_state_projection,
    compute_state_token,
)
from app.modules.wb_sky_control_plane.models.changeset import (
    BudgetPolicyPayload,
    CampaignResourceRef,
    ChangeSetMetadataV1,
    ChangeSetV1,
    LogicalScopeV1,
    OperationPreconditionV1,
    SetBudgetPolicyOperation,
    SetSalesPolicyOperation,
    SalesPolicyPayload,
)
from app.modules.wb_sky_control_plane.models.enums import (
    CampaignLegRole,
    CampaignTopology,
    MappingStatus,
    PaymentTypeAuthority,
    PlacementFlagAuthority,
    ProductMembershipAuthority,
)
from app.modules.wb_sky_control_plane.models.snapshot import (
    CampaignClassificationV1,
    CampaignLegSnapshotV1,
    CampaignResourceSnapshotV1,
    LocalPolicyStateV1,
    PlacementAuthorityV1,
)

pytestmark = pytest.mark.unit


def _snapshot(**policy_overrides: object) -> CampaignResourceSnapshotV1:
    budget = {"auto_budget_daily_limit": 100}
    sales = {"plan_for_sales_for_day": 5}
    bid_control = {"auto_shelf_bid_control_enabled": False}
    if "budget" in policy_overrides:
        budget = policy_overrides["budget"]  # type: ignore[assignment]
    if "sales" in policy_overrides:
        sales = policy_overrides["sales"]  # type: ignore[assignment]
    if "bid_control" in policy_overrides:
        bid_control = policy_overrides["bid_control"]  # type: ignore[assignment]
    return CampaignResourceSnapshotV1(
        resource_id="cmp_abc123",
        wb_cabinet_id=42,
        auto_leg=CampaignLegSnapshotV1(
            wb_adv_id=9001,
            role=CampaignLegRole.AUTO,
            product_membership=ProductMembershipAuthority.KNOWN,
            nm_ids=[111],
        ),
        local_policy=LocalPolicyStateV1(
            budget=budget,
            sales=sales,
            bid_control=bid_control,
        ),
        classification=CampaignClassificationV1(
            topology=CampaignTopology.AUTO_ONLY,
            payment_type=PaymentTypeAuthority.CPM,
        ),
        mapping_status=MappingStatus.OK,
    )


def test_semantic_digest_excludes_audit_metadata_and_changeset_id() -> None:
    """sd1 excludes changeset_id, metadata audit fields, operation.reason."""
    base_op = SetBudgetPolicyOperation(
        operation_id="op-budget",
        resource=CampaignResourceRef(resource_id="cmp_abc123"),
        payload=BudgetPolicyPayload(auto_budget_daily_limit=200),
        reason="owner tweak",
    )
    cs_a = ChangeSetV1(
        changeset_id="cs-1",
        scope=LogicalScopeV1(shop_id="shop-42"),
        operations=[base_op],
        metadata=ChangeSetMetadataV1(origin="excel", reason="r1"),
    )
    cs_b = ChangeSetV1(
        changeset_id="cs-2",
        scope=LogicalScopeV1(shop_id="shop-42"),
        operations=[
            SetBudgetPolicyOperation(
                operation_id="op-budget",
                resource=CampaignResourceRef(resource_id="cmp_abc123"),
                payload=BudgetPolicyPayload(auto_budget_daily_limit=200),
                reason="different reason",
            )
        ],
        metadata=ChangeSetMetadataV1(
            origin="telegram",
            reason="r2",
            decision_id="d1",
            experiment_id="e1",
        ),
    )
    assert compute_semantic_digest(cs_a) == compute_semantic_digest(cs_b)
    assert compute_semantic_digest(cs_a).startswith("sd1_")


def test_semantic_digest_json_key_order_independent() -> None:
    """Canonical hash ignores JSON key order in projection."""
    projection_a = {
        "version": "sd1",
        "scope": {"provider": "wildberries", "shop_id": "s1"},
        "operations": [{"op": "campaign.set_budget_policy", "operation_id": "x"}],
    }
    projection_b = {
        "operations": [{"operation_id": "x", "op": "campaign.set_budget_policy"}],
        "scope": {"shop_id": "s1", "provider": "wildberries"},
        "version": "sd1",
    }
    assert canonical_sha256(projection_a, prefix="sd1_") == canonical_sha256(
        projection_b, prefix="sd1_"
    )


def test_semantic_digest_changes_on_operation_order_and_id() -> None:
    op_a = SetBudgetPolicyOperation(
        operation_id="op-a",
        resource=CampaignResourceRef(resource_id="cmp_abc123"),
        payload=BudgetPolicyPayload(auto_budget_daily_limit=100),
    )
    op_b = SetSalesPolicyOperation(
        operation_id="op-b",
        resource=CampaignResourceRef(resource_id="cmp_abc123"),
        payload=SalesPolicyPayload(plan_for_sales_for_day=10),
    )
    cs_ab = ChangeSetV1(
        changeset_id="cs",
        scope=LogicalScopeV1(shop_id="shop-1"),
        operations=[op_a, op_b],
    )
    cs_ba = ChangeSetV1(
        changeset_id="cs",
        scope=LogicalScopeV1(shop_id="shop-1"),
        operations=[
            SetSalesPolicyOperation(
                operation_id="op-a",
                resource=CampaignResourceRef(resource_id="cmp_abc123"),
                payload=SalesPolicyPayload(plan_for_sales_for_day=10),
            ),
            SetBudgetPolicyOperation(
                operation_id="op-b",
                resource=CampaignResourceRef(resource_id="cmp_abc123"),
                payload=BudgetPolicyPayload(auto_budget_daily_limit=100),
            ),
        ],
    )
    assert compute_semantic_digest(cs_ab) != compute_semantic_digest(cs_ba)


def test_semantic_digest_preserves_omitted_vs_explicit_payload_fields() -> None:
    """exclude_unset: omitted field vs explicit null must differ in digest."""
    cs_omitted = ChangeSetV1(
        changeset_id="cs",
        scope=LogicalScopeV1(shop_id="shop-1"),
        operations=[
            SetBudgetPolicyOperation(
                operation_id="op-1",
                resource=CampaignResourceRef(resource_id="cmp_abc123"),
                payload=BudgetPolicyPayload(auto_budget_daily_limit=100),
            )
        ],
    )
    cs_explicit_null = ChangeSetV1(
        changeset_id="cs",
        scope=LogicalScopeV1(shop_id="shop-1"),
        operations=[
            SetBudgetPolicyOperation(
                operation_id="op-1",
                resource=CampaignResourceRef(resource_id="cmp_abc123"),
                payload=BudgetPolicyPayload(
                    auto_budget_daily_limit=100,
                    auto_budget_watchdog_enabled=None,
                ),
            )
        ],
    )
    assert compute_semantic_digest(cs_omitted) != compute_semantic_digest(cs_explicit_null)


def test_semantic_digest_includes_preconditions_and_scope() -> None:
    cs_no_pre = ChangeSetV1(
        changeset_id="cs",
        scope=LogicalScopeV1(shop_id="shop-a"),
        operations=[
            SetBudgetPolicyOperation(
                operation_id="op-1",
                resource=CampaignResourceRef(resource_id="cmp_abc123"),
                payload=BudgetPolicyPayload(auto_budget_daily_limit=100),
            )
        ],
    )
    cs_with_pre = ChangeSetV1(
        changeset_id="cs",
        scope=LogicalScopeV1(shop_id="shop-a"),
        operations=[
            SetBudgetPolicyOperation(
                operation_id="op-1",
                resource=CampaignResourceRef(resource_id="cmp_abc123"),
                payload=BudgetPolicyPayload(auto_budget_daily_limit=100),
                preconditions=OperationPreconditionV1(state_token="st1_abc"),
            )
        ],
    )
    cs_other_shop = ChangeSetV1(
        changeset_id="cs",
        scope=LogicalScopeV1(shop_id="shop-b"),
        operations=cs_no_pre.operations,
    )
    assert compute_semantic_digest(cs_no_pre) != compute_semantic_digest(cs_with_pre)
    assert compute_semantic_digest(cs_no_pre) != compute_semantic_digest(cs_other_shop)
    projection = build_semantic_projection(cs_with_pre)
    assert projection["preconditions"]["cmp_abc123"] == "st1_abc"


def test_state_token_same_relevant_state_same_token() -> None:
    snap = _snapshot()
    token_a = compute_state_token(snap, target_op_kinds=frozenset({"campaign.set_budget_policy"}))
    token_b = compute_state_token(snap, target_op_kinds=frozenset({"campaign.set_budget_policy"}))
    assert token_a == token_b
    assert token_a.startswith("st1_")


def test_state_token_unrelated_policy_change_same_token_for_budget_op() -> None:
    """Sales/bid_control drift must not invalidate budget-only token."""
    snap = _snapshot()
    snap_changed = copy.deepcopy(snap)
    snap_changed.local_policy = LocalPolicyStateV1(
        budget=snap.local_policy.budget,
        sales={"plan_for_sales_for_day": 999},
        bid_control={"auto_shelf_bid_control_enabled": True},
    )
    token_base = compute_state_token(
        snap, target_op_kinds=frozenset({"campaign.set_budget_policy"})
    )
    token_changed = compute_state_token(
        snap_changed, target_op_kinds=frozenset({"campaign.set_budget_policy"})
    )
    assert token_base == token_changed


def test_state_token_relevant_policy_change_changes_token() -> None:
    snap = _snapshot()
    snap_changed = copy.deepcopy(snap)
    snap_changed.local_policy = LocalPolicyStateV1(
        budget={"auto_budget_daily_limit": 500},
        sales=snap.local_policy.sales,
        bid_control=snap.local_policy.bid_control,
    )
    token_base = compute_state_token(
        snap, target_op_kinds=frozenset({"campaign.set_budget_policy"})
    )
    token_changed = compute_state_token(
        snap_changed, target_op_kinds=frozenset({"campaign.set_budget_policy"})
    )
    assert token_base != token_changed


def test_state_token_multi_op_same_resource_unions_dependencies() -> None:
    snap = _snapshot()
    budget_only = compute_state_token(
        snap, target_op_kinds=frozenset({"campaign.set_budget_policy"})
    )
    sales_only = compute_state_token(
        snap, target_op_kinds=frozenset({"campaign.set_sales_policy"})
    )
    union = compute_state_token(
        snap,
        target_op_kinds=frozenset(
            {"campaign.set_budget_policy", "campaign.set_sales_policy"}
        ),
    )
    assert union != budget_only
    assert union != sales_only
    proj = build_state_projection(
        snap,
        target_op_kinds=frozenset(
            {"campaign.set_budget_policy", "campaign.set_sales_policy"}
        ),
    )
    policy = proj["local_policy"]
    assert isinstance(policy, dict)
    assert "budget" in policy
    assert "sales" in policy
    assert "bid_control" not in policy
