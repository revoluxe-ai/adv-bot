"""Bounded semantic planners (not raw WB API steps)."""

from __future__ import annotations

from pydantic import BaseModel

from app.modules.wb_sky_control_plane.models.changeset import (
    CampaignOperationV1,
    SetBidControlPolicyOperation,
    SetBudgetPolicyOperation,
    SetSalesPolicyOperation,
)
from app.modules.wb_sky_control_plane.models.plan import PlanEffectV1, PlanV1, SemanticDiffEntryV1
from app.modules.wb_sky_control_plane.models.snapshot import CampaignResourceSnapshotV1


def _payload_fields(payload: BaseModel) -> dict[str, object]:
    return payload.model_dump(exclude_unset=True)


def _diff_policy_fields(
    *,
    current: dict[str, object],
    desired: dict[str, object],
    prefix: str,
) -> list[SemanticDiffEntryV1]:
    diffs: list[SemanticDiffEntryV1] = []
    for key, desired_value in desired.items():
        field_path = f"{prefix}.{key}"
        current_value = current.get(key)
        if current_value == desired_value:
            continue
        diffs.append(
            SemanticDiffEntryV1(
                field_path=field_path,
                current=current_value,
                desired=desired_value,
                intent="set",
            )
        )
    return diffs


def plan_operation(
    operation: CampaignOperationV1,
    *,
    operation_index: int,
    snapshot: CampaignResourceSnapshotV1,
) -> PlanEffectV1:
    """Produce semantic plan effect for one bounded operation."""
    resource_id = operation.resource.resource_id
    if isinstance(operation, SetBudgetPolicyOperation):
        desired = _payload_fields(operation.payload)
        diffs = _diff_policy_fields(
            current=snapshot.local_policy.budget,
            desired=desired,
            prefix="budget",
        )
    elif isinstance(operation, SetSalesPolicyOperation):
        desired = _payload_fields(operation.payload)
        diffs = _diff_policy_fields(
            current=snapshot.local_policy.sales,
            desired=desired,
            prefix="sales",
        )
    else:
        assert isinstance(operation, SetBidControlPolicyOperation)
        desired = _payload_fields(operation.payload)
        diffs = _diff_policy_fields(
            current=snapshot.local_policy.bid_control,
            desired=desired,
            prefix="bid_control",
        )

    return PlanEffectV1(
        resource_id=resource_id,
        operation=operation.op,
        operation_index=operation_index,
        semantic_changes=diffs,
        is_no_op=len(diffs) == 0,
    )


def build_plan(
    changeset_operations: list[CampaignOperationV1],
    snapshots: dict[str, CampaignResourceSnapshotV1],
) -> PlanV1:
    """Build semantic plan for all operations."""
    effects: list[PlanEffectV1] = []
    for index, operation in enumerate(changeset_operations):
        snapshot = snapshots[operation.resource.resource_id]
        effects.append(
            plan_operation(operation, operation_index=index, snapshot=snapshot)
        )
    is_no_op = all(effect.is_no_op for effect in effects)
    return PlanV1(effects=effects, is_no_op=is_no_op)
