"""
Dry-run validation для AdControlChangeSetV1.

Не пишет в PostgreSQL и не вызывает Apply Authority (Slice B contract only).
"""

from __future__ import annotations

import hashlib
import json

from pydantic import BaseModel

from app.modules.ad_control_settings.domain.campaign_ref import CampaignRef
from app.modules.ad_control_settings.domain.enums import (
    AdControlFeatureId,
    AdControlFeatureMode,
    AdControlScope,
    ShopFeatureActivation,
)
from app.modules.ad_control_settings.domain.registry import (
    assert_scope_supported,
    get_feature_definition,
)
from app.modules.ad_control_settings.persistence.cas import AdControlMutationKind
from app.modules.ad_control_settings.persistence.payload_codec import (
    PayloadCodecError,
    decode_payload_json,
    encode_payload_json,
)
from app.modules.ad_control_settings.persistence.repository import (
    AdControlPersistenceError,
    CampaignDisableUpsert,
    CampaignOverrideUpsert,
    ShopFeatureUpsert,
    validate_campaign_override_upsert,
    validate_shop_upsert,
)
from app.modules.wb_sky_control_plane.models.ad_control_changeset import (
    AdControlChangeSetV1,
    AdControlOperationV1,
    ClearCampaignAdControlFeatureOperation,
    DisableCampaignAdControlFeatureOperation,
    SetCampaignAdControlOverrideOperation,
    SetShopAdControlFeatureOperation,
)
from app.modules.wb_sky_control_plane.models.enums import DryRunStatus
from app.modules.wb_sky_control_plane.models.errors import ControlPlaneError


class AdControlShopFeatureSnapshotV1(BaseModel):
    """Authoritative shop configured row slice для dry-run."""

    model_config = {"frozen": True}

    feature_id: AdControlFeatureId
    schema_version: int
    activation: ShopFeatureActivation
    payload_json: dict[str, object] | None
    revision: int
    state_token: str


class AdControlCampaignFeatureSnapshotV1(BaseModel):
    """Authoritative campaign configured row slice (never INHERIT)."""

    model_config = {"frozen": True}

    shop_id: str
    advert_id: int
    feature_id: AdControlFeatureId
    schema_version: int
    mode: AdControlFeatureMode
    payload_json: dict[str, object] | None
    revision: int
    state_token: str


class AdControlSemanticDiffV1(BaseModel):
    """Configured mutation diff entry."""

    model_config = {"frozen": True}

    target_key: str
    intent: AdControlMutationKind
    field_path: str
    current: str | None
    desired: str | None
    effective_source_after: str | None = None


class AdControlValidationResult(BaseModel):
    """Итог dry-run ad control ChangeSet."""

    model_config = {"frozen": True}

    status: DryRunStatus
    changeset_id: str
    semantic_digest: str
    errors: list[ControlPlaneError] = []
    diffs: list[AdControlSemanticDiffV1] = []


KNOWN_AD_CONTROL_OPS: frozenset[str] = frozenset(
    {
        "shop.set_ad_control_feature",
        "campaign.set_ad_control_override",
        "campaign.disable_ad_control_feature",
        "campaign.clear_ad_control_feature",
    }
)


def compute_ad_control_semantic_digest(changeset: AdControlChangeSetV1) -> str:
    """Canonical hash для idempotency / receipt binding (future Apply)."""
    payload = changeset.model_dump(mode="json")
    canonical = json.dumps(payload, sort_keys=True, separators=(",", ":"))
    digest = hashlib.sha256(canonical.encode("utf-8")).hexdigest()
    return f"acs1_{digest}"


def validate_ad_control_changeset(
    changeset: AdControlChangeSetV1,
    *,
    shop_snapshots: dict[AdControlFeatureId, AdControlShopFeatureSnapshotV1],
    campaign_snapshots: dict[
        tuple[str, int, AdControlFeatureId],
        AdControlCampaignFeatureSnapshotV1,
    ],
) -> AdControlValidationResult:
    """Проверить ChangeSet; любая ошибка => REJECTED."""
    digest = compute_ad_control_semantic_digest(changeset)
    errors: list[ControlPlaneError] = []
    diffs: list[AdControlSemanticDiffV1] = []

    errors.extend(_duplicate_operation_ids(changeset))
    if errors:
        return _rejected(changeset.changeset_id, digest, errors)

    seen_slots: set[str] = set()
    for index, operation in enumerate(changeset.operations):
        slot_key = _operation_slot_key(operation)
        if slot_key in seen_slots:
            errors.append(
                ControlPlaneError(
                    code="DUPLICATE_TARGET",
                    message="duplicate ad control operation slot",
                    operation_index=index,
                    details={"slot": slot_key},
                )
            )
            continue
        seen_slots.add(slot_key)

        if operation.op not in KNOWN_AD_CONTROL_OPS:
            errors.append(
                ControlPlaneError(
                    code="UNSUPPORTED_OPERATION",
                    message=f"unknown op {operation.op!r}",
                    operation_index=index,
                )
            )
            continue

        op_diffs, op_errors = _validate_operation(
            changeset=changeset,
            operation=operation,
            index=index,
            shop_snapshots=shop_snapshots,
            campaign_snapshots=campaign_snapshots,
        )
        errors.extend(op_errors)
        if not op_errors:
            diffs.extend(op_diffs)

    if errors:
        return _rejected(changeset.changeset_id, digest, errors)

    actionable = [d for d in diffs if d.intent != AdControlMutationKind.NO_OP]
    status = DryRunStatus.NO_OP if not actionable else DryRunStatus.OK
    return AdControlValidationResult(
        status=status,
        changeset_id=changeset.changeset_id,
        semantic_digest=digest,
        diffs=actionable,
    )


def _validate_operation(
    *,
    changeset: AdControlChangeSetV1,
    operation: AdControlOperationV1,
    index: int,
    shop_snapshots: dict[AdControlFeatureId, AdControlShopFeatureSnapshotV1],
    campaign_snapshots: dict[
        tuple[str, int, AdControlFeatureId],
        AdControlCampaignFeatureSnapshotV1,
    ],
) -> tuple[list[AdControlSemanticDiffV1], list[ControlPlaneError]]:
    if isinstance(operation, SetShopAdControlFeatureOperation):
        return _validate_shop_operation(
            changeset=changeset,
            operation=operation,
            index=index,
            shop_snapshots=shop_snapshots,
        )
    if isinstance(operation, SetCampaignAdControlOverrideOperation):
        return _validate_campaign_override(
            changeset=changeset,
            operation=operation,
            index=index,
            campaign_snapshots=campaign_snapshots,
        )
    if isinstance(operation, DisableCampaignAdControlFeatureOperation):
        return _validate_campaign_disable(
            changeset=changeset,
            operation=operation,
            index=index,
            campaign_snapshots=campaign_snapshots,
        )
    assert isinstance(operation, ClearCampaignAdControlFeatureOperation)
    return _validate_campaign_clear(
        changeset=changeset,
        operation=operation,
        index=index,
        campaign_snapshots=campaign_snapshots,
    )


def _rejected(
    changeset_id: str,
    digest: str,
    errors: list[ControlPlaneError],
) -> AdControlValidationResult:
    return AdControlValidationResult(
        status=DryRunStatus.REJECTED,
        changeset_id=changeset_id,
        semantic_digest=digest,
        errors=errors,
        diffs=[],
    )


def _duplicate_operation_ids(changeset: AdControlChangeSetV1) -> list[ControlPlaneError]:
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


def _operation_slot_key(operation: AdControlOperationV1) -> str:
    if isinstance(operation, SetShopAdControlFeatureOperation):
        body = operation.payload
        return f"shop:{body.feature_id}"
    ref = operation.resource
    body = operation.payload
    return f"campaign:{ref.shop_id}:{ref.advert_id}:{body.feature_id}"


def _check_revision_precondition(
    *,
    index: int,
    expected_revision: int | None,
    snapshot_revision: int | None,
    feature_label: str,
) -> ControlPlaneError | None:
    if snapshot_revision is None:
        if expected_revision is not None:
            return ControlPlaneError(
                code="REVISION_CONFLICT",
                message="authoritative row absent but revision precondition set",
                operation_index=index,
                details={"feature": feature_label},
            )
        return None
    if expected_revision is None:
        return ControlPlaneError(
            code="REVISION_CONFLICT",
            message="authoritative row exists but absent-slot revision expected",
            operation_index=index,
            details={"feature": feature_label, "actual_revision": str(snapshot_revision)},
        )
    if expected_revision != snapshot_revision:
        return ControlPlaneError(
            code="REVISION_CONFLICT",
            message="stale revision precondition",
            operation_index=index,
            details={
                "feature": feature_label,
                "expected": str(expected_revision),
                "actual": str(snapshot_revision),
            },
        )
    return None


def _validate_shop_operation(
    *,
    changeset: AdControlChangeSetV1,
    operation: SetShopAdControlFeatureOperation,
    index: int,
    shop_snapshots: dict[AdControlFeatureId, AdControlShopFeatureSnapshotV1],
) -> tuple[list[AdControlSemanticDiffV1], list[ControlPlaneError]]:
    errors: list[ControlPlaneError] = []
    body = operation.payload
    feature_id = body.feature_id
    schema_version = body.schema_version
    scope_reason = assert_scope_supported(feature_id, AdControlScope.SHOP)
    if scope_reason is not None:
        errors.append(
            ControlPlaneError(
                code=scope_reason.value,
                message="feature not supported at SHOP scope",
                operation_index=index,
            )
        )
        return [], errors

    try:
        get_feature_definition(feature_id)
    except Exception:
        errors.append(
            ControlPlaneError(
                code="UNKNOWN_FEATURE",
                message="unknown feature_id",
                operation_index=index,
            )
        )
        return [], errors

    decoded = None
    if body.payload is not None:
        try:
            decoded = decode_payload_json(feature_id, body.payload)
        except PayloadCodecError as exc:
            errors.append(
                ControlPlaneError(
                    code="INVALID_PAYLOAD",
                    message=str(exc),
                    operation_index=index,
                )
            )
            return [], errors

    try:
        validate_shop_upsert(
            ShopFeatureUpsert(
                shop_id=changeset.scope.shop_id,
                feature_id=feature_id,
                schema_version=schema_version,
                activation=body.activation,
                payload=decoded,
            )
        )
    except AdControlPersistenceError as exc:
        errors.append(
            ControlPlaneError(
                code="INVALID_CONFIGURATION",
                message=str(exc),
                operation_index=index,
            )
        )
        return [], errors

    snapshot = shop_snapshots.get(feature_id)
    rev_err = _check_revision_precondition(
        index=index,
        expected_revision=operation.preconditions.expected_revision,
        snapshot_revision=snapshot.revision if snapshot else None,
        feature_label=feature_id.value,
    )
    if rev_err is not None:
        return [], [rev_err]

    desired_json = (
        encode_payload_json(feature_id, decoded) if decoded is not None else None
    )
    if snapshot is None:
        intent = (
            AdControlMutationKind.DISABLE
            if body.activation == ShopFeatureActivation.DISABLED
            else AdControlMutationKind.CREATE
        )
        return [
            AdControlSemanticDiffV1(
                target_key=f"shop:{feature_id.value}",
                intent=intent,
                field_path="activation",
                current=None,
                desired=body.activation.value,
            )
        ], errors

    current_activation = snapshot.activation.value
    desired_activation = body.activation.value
    current_json = snapshot.payload_json
    if current_activation == desired_activation and current_json == desired_json:
        return [
            AdControlSemanticDiffV1(
                target_key=f"shop:{feature_id.value}",
                intent=AdControlMutationKind.NO_OP,
                field_path="row",
                current="unchanged",
                desired="unchanged",
            )
        ], errors

    intent = (
        AdControlMutationKind.DISABLE
        if body.activation == ShopFeatureActivation.DISABLED
        else AdControlMutationKind.UPDATE
    )
    diffs = [
        AdControlSemanticDiffV1(
            target_key=f"shop:{feature_id.value}",
            intent=intent,
            field_path="activation",
            current=current_activation,
            desired=desired_activation,
        )
    ]
    if desired_json != current_json:
        diffs.append(
            AdControlSemanticDiffV1(
                target_key=f"shop:{feature_id.value}",
                intent=intent,
                field_path="payload",
                current=_json_preview(current_json),
                desired=_json_preview(desired_json),
            )
        )
    return diffs, errors


def _validate_campaign_override(
    *,
    changeset: AdControlChangeSetV1,
    operation: SetCampaignAdControlOverrideOperation,
    index: int,
    campaign_snapshots: dict[
        tuple[str, int, AdControlFeatureId],
        AdControlCampaignFeatureSnapshotV1,
    ],
) -> tuple[list[AdControlSemanticDiffV1], list[ControlPlaneError]]:
    errors: list[ControlPlaneError] = []
    ref, body, scope_err = _campaign_scope_check(changeset, operation, index)
    if scope_err is not None:
        return [], [scope_err]

    feature_id = body.feature_id
    schema_version = body.schema_version
    scope_reason = assert_scope_supported(feature_id, AdControlScope.CAMPAIGN)
    if scope_reason is not None:
        errors.append(
            ControlPlaneError(
                code=scope_reason.value,
                message="feature not supported at CAMPAIGN scope",
                operation_index=index,
            )
        )
        return [], errors

    try:
        decoded = decode_payload_json(feature_id, body.payload)
    except PayloadCodecError as exc:
        errors.append(
            ControlPlaneError(
                code="INVALID_PAYLOAD",
                message=str(exc),
                operation_index=index,
            )
        )
        return [], errors

    campaign = CampaignRef(shop_id=ref.shop_id, advert_id=ref.advert_id)
    try:
        validate_campaign_override_upsert(
            CampaignOverrideUpsert(
                campaign=campaign,
                feature_id=feature_id,
                schema_version=schema_version,
                payload=decoded,
            )
        )
    except AdControlPersistenceError as exc:
        errors.append(
            ControlPlaneError(
                code="INVALID_CONFIGURATION",
                message=str(exc),
                operation_index=index,
            )
        )
        return [], errors

    key = (ref.shop_id, ref.advert_id, feature_id)
    snapshot = campaign_snapshots.get(key)
    rev_err = _check_revision_precondition(
        index=index,
        expected_revision=operation.preconditions.expected_revision,
        snapshot_revision=snapshot.revision if snapshot else None,
        feature_label=feature_id.value,
    )
    if rev_err is not None:
        return [], [rev_err]

    desired_json = encode_payload_json(feature_id, decoded)
    if snapshot is None:
        return [
            AdControlSemanticDiffV1(
                target_key=f"campaign:{ref.advert_id}:{feature_id.value}",
                intent=AdControlMutationKind.CREATE,
                field_path="mode",
                current=None,
                desired=AdControlFeatureMode.OVERRIDE.value,
                effective_source_after="CAMPAIGN_OVERRIDE",
            )
        ], errors

    if (
        snapshot.mode == AdControlFeatureMode.OVERRIDE
        and snapshot.payload_json == desired_json
        and snapshot.schema_version == schema_version
    ):
        return [
            AdControlSemanticDiffV1(
                target_key=f"campaign:{ref.advert_id}:{feature_id.value}",
                intent=AdControlMutationKind.NO_OP,
                field_path="row",
                current="unchanged",
                desired="unchanged",
            )
        ], errors

    return [
        AdControlSemanticDiffV1(
            target_key=f"campaign:{ref.advert_id}:{feature_id.value}",
            intent=AdControlMutationKind.UPDATE,
            field_path="override",
            current=_json_preview(snapshot.payload_json),
            desired=_json_preview(desired_json),
            effective_source_after="CAMPAIGN_OVERRIDE",
        )
    ], errors


def _validate_campaign_disable(
    *,
    changeset: AdControlChangeSetV1,
    operation: DisableCampaignAdControlFeatureOperation,
    index: int,
    campaign_snapshots: dict[
        tuple[str, int, AdControlFeatureId],
        AdControlCampaignFeatureSnapshotV1,
    ],
) -> tuple[list[AdControlSemanticDiffV1], list[ControlPlaneError]]:
    ref, body, scope_err = _campaign_scope_check(changeset, operation, index)
    if scope_err is not None:
        return [], [scope_err]

    feature_id = body.feature_id
    key = (ref.shop_id, ref.advert_id, feature_id)
    snapshot = campaign_snapshots.get(key)
    rev_err = _check_revision_precondition(
        index=index,
        expected_revision=operation.preconditions.expected_revision,
        snapshot_revision=snapshot.revision if snapshot else None,
        feature_label=feature_id.value,
    )
    if rev_err is not None:
        return [], [rev_err]

    if snapshot is None:
        return [
            AdControlSemanticDiffV1(
                target_key=f"campaign:{ref.advert_id}:{feature_id.value}",
                intent=AdControlMutationKind.DISABLE,
                field_path="mode",
                current=None,
                desired=AdControlFeatureMode.DISABLED.value,
                effective_source_after="CAMPAIGN_DISABLED",
            )
        ], []

    if snapshot.mode == AdControlFeatureMode.DISABLED:
        return [
            AdControlSemanticDiffV1(
                target_key=f"campaign:{ref.advert_id}:{feature_id.value}",
                intent=AdControlMutationKind.NO_OP,
                field_path="row",
                current="disabled",
                desired="disabled",
            )
        ], []

    return [
        AdControlSemanticDiffV1(
            target_key=f"campaign:{ref.advert_id}:{feature_id.value}",
            intent=AdControlMutationKind.DISABLE,
            field_path="mode",
            current=snapshot.mode.value,
            desired=AdControlFeatureMode.DISABLED.value,
            effective_source_after="CAMPAIGN_DISABLED",
        )
    ], []


def _validate_campaign_clear(
    *,
    changeset: AdControlChangeSetV1,
    operation: ClearCampaignAdControlFeatureOperation,
    index: int,
    campaign_snapshots: dict[
        tuple[str, int, AdControlFeatureId],
        AdControlCampaignFeatureSnapshotV1,
    ],
) -> tuple[list[AdControlSemanticDiffV1], list[ControlPlaneError]]:
    ref, body, scope_err = _campaign_scope_check(changeset, operation, index)
    if scope_err is not None:
        return [], [scope_err]

    feature_id = body.feature_id
    key = (ref.shop_id, ref.advert_id, feature_id)
    snapshot = campaign_snapshots.get(key)
    rev_err = _check_revision_precondition(
        index=index,
        expected_revision=operation.preconditions.expected_revision,
        snapshot_revision=snapshot.revision if snapshot else None,
        feature_label=feature_id.value,
    )
    if rev_err is not None:
        return [], [rev_err]

    if snapshot is None:
        return [
            AdControlSemanticDiffV1(
                target_key=f"campaign:{ref.advert_id}:{feature_id.value}",
                intent=AdControlMutationKind.NO_OP,
                field_path="authority",
                current="absent",
                desired="absent",
                effective_source_after="SHOP_POLICY_OR_INHERIT",
            )
        ], []

    prior_mode = snapshot.mode.value
    return [
        AdControlSemanticDiffV1(
            target_key=f"campaign:{ref.advert_id}:{feature_id.value}",
            intent=AdControlMutationKind.CLEAR_TO_INHERIT,
            field_path="authority",
            current=prior_mode,
            desired="absent",
            effective_source_after="SHOP_POLICY_OR_INHERIT",
        )
    ], []


def _campaign_scope_check(
    changeset: AdControlChangeSetV1,
    operation: AdControlOperationV1,
    index: int,
) -> tuple[
    object,
    object,
    ControlPlaneError | None,
]:
    ref = operation.resource  # type: ignore[attr-defined]
    body = operation.payload  # type: ignore[attr-defined]
    if ref.shop_id != changeset.scope.shop_id:
        return ref, body, ControlPlaneError(
            code="SCOPE_SHOP_MISMATCH",
            message="campaign resource shop_id must match changeset scope",
            operation_index=index,
        )
    return ref, body, None


def _json_preview(data: dict[str, object] | None) -> str | None:
    if data is None:
        return None
    return json.dumps(data, sort_keys=True, separators=(",", ":"))
