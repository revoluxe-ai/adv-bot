"""Validate ChangeSet operations against snapshots and capabilities."""

from __future__ import annotations

from app.modules.wb_sky_control_plane.models.capabilities import CampaignCapabilitiesV1
from app.modules.wb_sky_control_plane.models.changeset import ChangeSetV1
from app.modules.wb_sky_control_plane.models.enums import CanonicalOperationKind
from app.modules.wb_sky_control_plane.models.errors import ControlPlaneError
from app.modules.wb_sky_control_plane.models.snapshot import CampaignResourceSnapshotV1


_SUPPORTED_OPS = {member.value for member in CanonicalOperationKind}


def validate_changeset(
    changeset: ChangeSetV1,
    snapshots: dict[str, CampaignResourceSnapshotV1],
    capabilities: dict[str, CampaignCapabilitiesV1],
) -> list[ControlPlaneError]:
    """One invalid operation rejects the whole ChangeSet."""
    errors: list[ControlPlaneError] = []
    for index, operation in enumerate(changeset.operations):
        op_name = operation.op
        if op_name not in _SUPPORTED_OPS:
            errors.append(
                ControlPlaneError(
                    code="UNSUPPORTED_OPERATION",
                    message=f"Operation {op_name!r} is not in A1 bounded subset",
                    operation_index=index,
                    resource_id=operation.resource.resource_id,
                )
            )
            continue

        resource_id = operation.resource.resource_id
        snapshot = snapshots.get(resource_id)
        if snapshot is None:
            errors.append(
                ControlPlaneError(
                    code="RESOURCE_SNAPSHOT_MISSING",
                    message="Snapshot missing for operation resource",
                    operation_index=index,
                    resource_id=resource_id,
                )
            )
            continue

        caps = capabilities.get(resource_id)
        if caps is None or not caps.is_write_eligible(op_name):
            assessment = caps.assessment_for_op(op_name) if caps else None
            reason = assessment.reason_code if assessment else "NO_CAPABILITIES"
            errors.append(
                ControlPlaneError(
                    code="CAPABILITY_NOT_ELIGIBLE",
                    message="Operation not write-eligible (fail-closed)",
                    operation_index=index,
                    resource_id=resource_id,
                    details={"reason_code": reason},
                )
            )
            continue

        if operation.preconditions is not None:
            expected = operation.preconditions.state_token
            actual = snapshot.state_token
            if actual is None or expected != actual:
                errors.append(
                    ControlPlaneError(
                        code="PRECONDITION_STATE_TOKEN_MISMATCH",
                        message="state_token precondition failed",
                        operation_index=index,
                        resource_id=resource_id,
                        details={"expected": expected, "actual": actual or ""},
                    )
                )
    return errors
