"""Фаза A: чистая pre-I/O проверка ChangeSetV1 без PG/WB/resolver.

Отклонения здесь не должны вызывать ``resolve_changeset_snapshots``.
"""

from __future__ import annotations

from app.modules.wb_sky_control_plane.kernel.mutation_policy import (
    KNOWN_CAPABILITIES,
    policy_for,
)
from app.modules.wb_sky_control_plane.kernel.semantic_digest import (
    compute_semantic_digest,
)
from app.modules.wb_sky_control_plane.models.changeset import (
    CampaignOperationV1,
    ChangeSetV1,
)
from app.modules.wb_sky_control_plane.models.errors import ControlPlaneError
from app.modules.wb_sky_control_plane.models.plan import PriorChangeSetRecord


def collect_pure_preflight_errors(
    changeset: ChangeSetV1,
    *,
    prior: PriorChangeSetRecord | None = None,
    capability_grants: frozenset[str] | None = None,
) -> tuple[str, list[ControlPlaneError]]:
    """Собрать ошибки фазы A. Второй элемент непустой => resolver не вызывать."""
    digest = compute_semantic_digest(changeset)
    errors: list[ControlPlaneError] = []

    errors.extend(_duplicate_operation_ids(changeset))
    if (
        prior is not None
        and prior.changeset_id == changeset.changeset_id
        and prior.canonical_hash != digest
    ):
        errors.append(
            ControlPlaneError(
                code="CHANGESET_ID_CONFLICT",
                message="changeset_id replay has a different canonical hash",
                details={"changeset_id": changeset.changeset_id},
            )
        )

    if capability_grants is not None:
        unknown = sorted(
            token for token in capability_grants if token not in KNOWN_CAPABILITIES
        )
        if unknown:
            errors.append(
                ControlPlaneError(
                    code="UNKNOWN_CAPABILITY",
                    message="capability token is outside the known catalog",
                    details={"tokens": ",".join(unknown)},
                )
            )

    seen_slots: set[tuple[str, str]] = set()
    for index, operation in enumerate(changeset.operations):
        errors.extend(
            _pure_operation_errors(
                operation,
                index=index,
                seen_slots=seen_slots,
            )
        )

    return digest, errors


def _duplicate_operation_ids(changeset: ChangeSetV1) -> list[ControlPlaneError]:
    seen: set[str] = set()
    dupes: set[str] = set()
    for operation in changeset.operations:
        if operation.operation_id in seen:
            dupes.add(operation.operation_id)
        seen.add(operation.operation_id)
    if not dupes:
        return []
    return [
        ControlPlaneError(
            code="DUPLICATE_OPERATION_ID",
            message="duplicate operation_id",
            details={"operation_id": ",".join(sorted(dupes))},
        )
    ]


def _presented_token(operation: CampaignOperationV1) -> str | None:
    preconditions = operation.preconditions
    if preconditions is None:
        return None
    token = preconditions.state_token.strip()
    if not token:
        return None
    return token


def _pure_operation_errors(
    operation: CampaignOperationV1,
    *,
    index: int,
    seen_slots: set[tuple[str, str]],
) -> list[ControlPlaneError]:
    """Проверки одной операции без authoritative snapshot."""
    errors: list[ControlPlaneError] = []
    op_name = operation.op
    resource_id = operation.resource.resource_id
    policy = policy_for(op_name)
    if policy is None or op_name not in KNOWN_CAPABILITIES:
        errors.append(
            ControlPlaneError(
                code="UNSUPPORTED_OPERATION",
                message=f"Operation {op_name!r} is not in the bounded set",
                operation_index=index,
                resource_id=resource_id,
            )
        )
        return errors
    if policy.required_capability not in KNOWN_CAPABILITIES:
        errors.append(
            ControlPlaneError(
                code="UNKNOWN_CAPABILITY",
                message="policy names a capability outside the known catalog",
                operation_index=index,
                resource_id=resource_id,
                details={"capability": policy.required_capability},
            )
        )
        return errors

    slot = (resource_id, op_name)
    if slot in seen_slots:
        errors.append(
            ControlPlaneError(
                code="DUPLICATE_TARGET",
                message="duplicate operation slot for the same resource",
                operation_index=index,
                resource_id=resource_id,
                details={"operation": op_name},
            )
        )
    seen_slots.add(slot)

    if _presented_token(operation) is None:
        errors.append(
            ControlPlaneError(
                code="STATE_TOKEN_MISSING",
                message="state_token is missing",
                operation_index=index,
                resource_id=resource_id,
            )
        )
    return errors
