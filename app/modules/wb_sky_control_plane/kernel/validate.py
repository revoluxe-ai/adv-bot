"""Dry-run проверка ChangeSetV1. Не пишет в WB, PostgreSQL или ClickHouse.

Фаза C (после authoritative resolve): stale ``state_token`` → mutation policy →
нормализация → domain → capability → ``expected_current_value`` → diff.
Фаза A — ``kernel.preflight`` (до I/O).
"""

from __future__ import annotations

from pydantic import BaseModel

from app.modules.wb_sky_control_plane.kernel.domain_validators import (
    DomainContext,
    run_declared_validators,
)
from app.modules.wb_sky_control_plane.kernel.mutation_policy import (
    NormalizationFailure,
    policy_for,
    normalize_registered_value,
)
from app.modules.wb_sky_control_plane.kernel.preflight import (
    collect_pure_preflight_errors,
)
from app.modules.wb_sky_control_plane.kernel.semantic_digest import (
    compute_semantic_digest,
)
from app.modules.wb_sky_control_plane.models.capabilities import CampaignCapabilitiesV1
from app.modules.wb_sky_control_plane.models.changeset import CampaignOperationV1
from app.modules.wb_sky_control_plane.models.changeset import ChangeSetV1
from app.modules.wb_sky_control_plane.models.enums import DryRunStatus, MappingStatus
from app.modules.wb_sky_control_plane.models.errors import ControlPlaneError
from app.modules.wb_sky_control_plane.models.plan import (
    ChangeSetValidationResult,
    PlanEffectV1,
    PlanV1,
    PriorChangeSetRecord,
    SemanticDiffEntryV1,
)
from app.modules.wb_sky_control_plane.models.snapshot import CampaignResourceSnapshotV1

_Scalar = str | int | float | bool | None


def validate_changeset(
    changeset: ChangeSetV1,
    snapshots: dict[str, CampaignResourceSnapshotV1],
    capabilities: dict[str, CampaignCapabilitiesV1],
    *,
    prior: PriorChangeSetRecord | None = None,
    capability_grants: frozenset[str] | None = None,
    skip_pure_checks: bool = False,
) -> ChangeSetValidationResult:
    """Проверить ChangeSet целиком. Любая ошибка — REJECTED без diff действия.

    ``skip_pure_checks=True`` — фаза A уже выполнена в ``dry_run`` до resolver.
    """
    if skip_pure_checks:
        digest = compute_semantic_digest(changeset)
    else:
        digest, pure_errors = collect_pure_preflight_errors(
            changeset,
            prior=prior,
            capability_grants=capability_grants,
        )
        if pure_errors:
            return _rejected(changeset, digest, pure_errors)

    errors: list[ControlPlaneError] = []
    prepared: list[PlanEffectV1] = []
    diffs: list[SemanticDiffEntryV1] = []

    for index, operation in enumerate(changeset.operations):
        before = len(errors)
        effect = _validate_operation_semantic(
            changeset_errors=errors,
            operation=operation,
            index=index,
            snapshots=snapshots,
            capabilities=capabilities,
            capability_grants=capability_grants,
        )
        if effect is None or len(errors) != before:
            continue
        prepared.append(effect)
        diffs.extend(effect.semantic_changes)

    if errors:
        return _rejected(changeset, digest, errors)

    is_no_op = all(effect.is_no_op for effect in prepared)
    plan = PlanV1(effects=prepared, is_no_op=is_no_op)
    status = DryRunStatus.NO_OP if is_no_op else DryRunStatus.OK
    actionable = [] if is_no_op else diffs
    return ChangeSetValidationResult(
        status=status,
        changeset_id=changeset.changeset_id,
        semantic_digest=digest,
        diffs=actionable,
        plan=plan,
    )


def _rejected(
    changeset: ChangeSetV1,
    digest: str,
    errors: list[ControlPlaneError],
) -> ChangeSetValidationResult:
    return ChangeSetValidationResult(
        status=DryRunStatus.REJECTED,
        changeset_id=changeset.changeset_id,
        semantic_digest=digest,
        errors=errors,
        diffs=[],
        plan=None,
    )


def _presented_token(operation: CampaignOperationV1) -> str | None:
    preconditions = operation.preconditions
    if preconditions is None:
        return None
    token = preconditions.state_token.strip()
    if not token:
        return None
    return token


def _require_presented_token(
    operation: CampaignOperationV1,
    *,
    index: int,
    resource_id: str,
    changeset_errors: list[ControlPlaneError],
) -> str | None:
    token = _presented_token(operation)
    if token is None:
        changeset_errors.append(
            ControlPlaneError(
                code="STATE_TOKEN_MISSING",
                message="state_token is missing",
                operation_index=index,
                resource_id=resource_id,
            )
        )
        return None
    return token


def _payload_values(payload: BaseModel) -> dict[str, object]:
    dumped = payload.model_dump(exclude_unset=True)
    values: dict[str, object] = {}
    for key, raw in dumped.items():
        values[str(key)] = raw
    return values


def _bucket(
    snapshot: CampaignResourceSnapshotV1,
    bucket: str,
) -> dict[str, object]:
    local = snapshot.local_policy
    if bucket == "budget":
        return dict(local.budget)
    if bucket == "sales":
        return dict(local.sales)
    return dict(local.bid_control)


def _as_scalar(value: object) -> _Scalar | None:
    """Вернуть JSON-скаляр либо None, если значение нескалярное."""
    if value is None or isinstance(value, (str, int, float, bool)):
        return value
    return None


def _failure_error(
    failure: NormalizationFailure,
    *,
    index: int,
    resource_id: str,
    field_name: str,
) -> ControlPlaneError:
    return ControlPlaneError(
        code=failure.code,
        message=failure.message,
        operation_index=index,
        resource_id=resource_id,
        details={"field": field_name},
    )


def _validate_operation_semantic(
    *,
    changeset_errors: list[ControlPlaneError],
    operation: CampaignOperationV1,
    index: int,
    snapshots: dict[str, CampaignResourceSnapshotV1],
    capabilities: dict[str, CampaignCapabilitiesV1],
    capability_grants: frozenset[str] | None,
) -> PlanEffectV1 | None:
    op_name = operation.op
    resource_id = operation.resource.resource_id
    policy = policy_for(op_name)
    assert policy is not None

    snapshot = snapshots.get(resource_id)
    if snapshot is None:
        changeset_errors.append(
            ControlPlaneError(
                code="RESOURCE_SNAPSHOT_MISSING",
                message="CampaignResourceRef does not resolve in the snapshot",
                operation_index=index,
                resource_id=resource_id,
            )
        )
        return None

    if snapshot.mapping_status != MappingStatus.OK:
        changeset_errors.append(
            ControlPlaneError(
                code="MAPPING_NOT_OK",
                message="campaign resource mapping is unknown or broken",
                operation_index=index,
                resource_id=resource_id,
                details={"mapping_status": snapshot.mapping_status.value},
            )
        )
        return None

    token = _require_presented_token(
        operation,
        index=index,
        resource_id=resource_id,
        changeset_errors=changeset_errors,
    )
    if token is None:
        return None

    actual = snapshot.state_token
    if actual is None or actual != token:
        changeset_errors.append(
            ControlPlaneError(
                code="STATE_TOKEN_STALE",
                message="stale or invalid generation token",
                operation_index=index,
                resource_id=resource_id,
                details={"expected": token, "actual": actual or ""},
            )
        )
        return None

    requested_raw = _payload_values(operation.payload)
    for field_name in requested_raw:
        if field_name not in policy.fields:
            changeset_errors.append(
                ControlPlaneError(
                    code="UNKNOWN_FIELD",
                    message=f"field {field_name} is not mutable for {op_name}",
                    operation_index=index,
                    resource_id=resource_id,
                    details={"field": field_name},
                )
            )
    if _op_failed(changeset_errors, index):
        return None

    bucket = _bucket(snapshot, policy.bucket)
    normalized_map: dict[str, object] = {}
    for field_name, raw_value in requested_raw.items():
        if field_name not in policy.fields:
            continue
        normalized, failure = normalize_registered_value(field_name, raw_value)
        if failure is not None:
            changeset_errors.append(
                _failure_error(
                    failure,
                    index=index,
                    resource_id=resource_id,
                    field_name=field_name,
                )
            )
            continue
        normalized_map[field_name] = normalized

    if _op_failed(changeset_errors, index):
        return None

    merged = dict(bucket)
    for field_name, normalized in normalized_map.items():
        merged[field_name] = normalized
    domain_errors = run_declared_validators(
        policy.domain_validators,
        DomainContext(
            operation_index=index,
            resource_id=resource_id,
            bucket=policy.bucket,
            requested=normalized_map,
            merged=merged,
        ),
    )
    if domain_errors:
        changeset_errors.extend(domain_errors)
        return None

    if (
        capability_grants is not None
        and policy.required_capability not in capability_grants
    ):
        changeset_errors.append(
            ControlPlaneError(
                code="CAPABILITY_NOT_ELIGIBLE",
                message="required capability is not granted",
                operation_index=index,
                resource_id=resource_id,
                details={"capability": policy.required_capability},
            )
        )
        return None

    caps = capabilities.get(resource_id)
    if caps is None or not caps.is_write_eligible(op_name):
        assessment = caps.assessment_for_op(op_name) if caps else None
        reason = assessment.reason_code if assessment else "NO_CAPABILITIES"
        changeset_errors.append(
            ControlPlaneError(
                code="CAPABILITY_NOT_ELIGIBLE",
                message="Operation not write-eligible (fail-closed)",
                operation_index=index,
                resource_id=resource_id,
                details={"reason_code": reason},
            )
        )
        return None

    expected = (
        None
        if operation.preconditions is None
        else operation.preconditions.expected_current_value
    )
    if expected is not None:
        for field_name, expected_raw in expected.items():
            if field_name not in policy.fields:
                changeset_errors.append(
                    ControlPlaneError(
                        code="UNKNOWN_FIELD",
                        message=f"field {field_name} is not mutable for {op_name}",
                        operation_index=index,
                        resource_id=resource_id,
                        details={"field": field_name},
                    )
                )
                continue
            current_norm, current_failure = normalize_registered_value(
                field_name,
                bucket.get(field_name),
            )
            expected_norm, expected_failure = normalize_registered_value(
                field_name,
                expected_raw,
            )
            failure = current_failure or expected_failure
            if failure is not None:
                changeset_errors.append(
                    _failure_error(
                        failure,
                        index=index,
                        resource_id=resource_id,
                        field_name=field_name,
                    )
                )
                continue
            if expected_norm != current_norm:
                changeset_errors.append(
                    ControlPlaneError(
                        code="EXPECTED_CURRENT_VALUE_MISMATCH",
                        message=(
                            "expected_current_value does not match the "
                            "state_token generation"
                        ),
                        operation_index=index,
                        resource_id=resource_id,
                        details={"field": field_name},
                    )
                )

    if _op_failed(changeset_errors, index):
        return None

    semantic_changes = _semantic_changes(
        resource_id=resource_id,
        bucket_name=policy.bucket,
        bucket=bucket,
        requested_raw=requested_raw,
        normalized_map=normalized_map,
        index=index,
        errors=changeset_errors,
    )
    if _op_failed(changeset_errors, index):
        return None
    return PlanEffectV1(
        resource_id=resource_id,
        operation=op_name,
        operation_index=index,
        semantic_changes=semantic_changes,
        is_no_op=len(semantic_changes) == 0,
    )


def _op_failed(errors: list[ControlPlaneError], index: int) -> bool:
    return any(error.operation_index == index for error in errors)


def _semantic_changes(
    *,
    resource_id: str,
    bucket_name: str,
    bucket: dict[str, object],
    requested_raw: dict[str, object],
    normalized_map: dict[str, object],
    index: int,
    errors: list[ControlPlaneError],
) -> list[SemanticDiffEntryV1]:
    changes: list[SemanticDiffEntryV1] = []
    for field_name, raw_value in requested_raw.items():
        if field_name not in normalized_map:
            continue
        normalized = normalized_map[field_name]
        current_norm, failure = normalize_registered_value(
            field_name,
            bucket.get(field_name),
        )
        if failure is not None:
            errors.append(
                _failure_error(
                    failure,
                    index=index,
                    resource_id=resource_id,
                    field_name=field_name,
                )
            )
            continue
        if current_norm == normalized:
            continue
        old = _as_scalar(current_norm)
        requested = _as_scalar(raw_value)
        canonical = _as_scalar(normalized)
        if requested is None and raw_value is not None:
            errors.append(
                ControlPlaneError(
                    code="INVALID_VALUE",
                    message=f"requested value for {field_name} is not a scalar",
                    operation_index=index,
                    resource_id=resource_id,
                    details={"field": field_name},
                )
            )
            continue
        if canonical is None and normalized is not None:
            errors.append(
                ControlPlaneError(
                    code="INVALID_VALUE",
                    message=f"normalized value for {field_name} is not a scalar",
                    operation_index=index,
                    resource_id=resource_id,
                    details={"field": field_name},
                )
            )
            continue
        changes.append(
            SemanticDiffEntryV1(
                field_path=f"{resource_id}.{bucket_name}.{field_name}",
                resource_id=resource_id,
                current=old,
                desired=canonical,
                old=old,
                requested=requested,
                normalized=canonical,
                intent="set",
            )
        )
    return changes
