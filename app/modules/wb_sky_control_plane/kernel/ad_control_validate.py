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
from app.modules.ad_control_settings.persistence.payload_codec import (
    PayloadCodecError,
    decode_payload_json,
    encode_payload_json,
)
from app.modules.ad_control_settings.persistence.repository import (
    AdControlPersistenceError,
    CampaignFeatureUpsert,
    ShopFeatureUpsert,
    validate_campaign_upsert,
    validate_shop_upsert,
)
from app.modules.wb_sky_control_plane.models.ad_control_changeset import (
    AdControlChangeSetV1,
    AdControlOperationV1,
    SetCampaignAdControlFeatureOperation,
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
    state_token: str


class AdControlCampaignFeatureSnapshotV1(BaseModel):
    """Authoritative campaign configured row slice."""

    model_config = {"frozen": True}

    shop_id: str
    advert_id: int
    feature_id: AdControlFeatureId
    schema_version: int
    mode: AdControlFeatureMode
    payload_json: dict[str, object] | None
    state_token: str


class AdControlSemanticDiffV1(BaseModel):
    """Scalar diff entry для configured mutation."""

    model_config = {"frozen": True}

    target_key: str
    field_path: str
    current: str | None
    desired: str | None


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
        "campaign.set_ad_control_feature",
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
    shop_snapshots: dict[tuple[AdControlFeatureId, int], AdControlShopFeatureSnapshotV1],
    campaign_snapshots: dict[
        tuple[str, int, AdControlFeatureId, int],
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

        if isinstance(operation, SetShopAdControlFeatureOperation):
            diff, op_errors = _validate_shop_operation(
                changeset=changeset,
                operation=operation,
                index=index,
                shop_snapshots=shop_snapshots,
            )
        else:
            diff, op_errors = _validate_campaign_operation(
                changeset=changeset,
                operation=operation,
                index=index,
                campaign_snapshots=campaign_snapshots,
            )
        errors.extend(op_errors)
        if not op_errors and diff is not None:
            diffs.extend(diff)

    if errors:
        return _rejected(changeset.changeset_id, digest, errors)

    status = DryRunStatus.NO_OP if not diffs else DryRunStatus.OK
    return AdControlValidationResult(
        status=status,
        changeset_id=changeset.changeset_id,
        semantic_digest=digest,
        diffs=diffs,
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
        return f"shop:{body.feature_id}:{body.schema_version}"
    body = operation.payload
    ref = operation.resource
    return (
        f"campaign:{ref.shop_id}:{ref.advert_id}:"
        f"{body.feature_id}:{body.schema_version}"
    )


def _validate_shop_operation(
    *,
    changeset: AdControlChangeSetV1,
    operation: SetShopAdControlFeatureOperation,
    index: int,
    shop_snapshots: dict[tuple[AdControlFeatureId, int], AdControlShopFeatureSnapshotV1],
) -> tuple[list[AdControlSemanticDiffV1] | None, list[ControlPlaneError]]:
    errors: list[ControlPlaneError] = []
    body = operation.payload
    if changeset.scope.shop_id != changeset.scope.shop_id:
        pass  # scope always matches pydantic model
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
        return None, errors

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
        return None, errors

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
            return None, errors

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
        return None, errors

    key = (feature_id, schema_version)
    snapshot = shop_snapshots.get(key)
    token = operation.preconditions.state_token
    if snapshot is not None and snapshot.state_token != token:
        errors.append(
            ControlPlaneError(
                code="STATE_TOKEN_STALE",
                message="stale shop feature state_token",
                operation_index=index,
                details={"feature_id": feature_id.value},
            )
        )
        return None, errors

    desired_json = (
        encode_payload_json(feature_id, decoded) if decoded is not None else None
    )
    current_activation = snapshot.activation.value if snapshot else None
    desired_activation = body.activation.value
    current_json = snapshot.payload_json if snapshot else None

    if current_activation == desired_activation and current_json == desired_json:
        return [], errors

    diffs = [
        AdControlSemanticDiffV1(
            target_key=f"shop:{feature_id.value}:{schema_version}",
            field_path="activation",
            current=current_activation,
            desired=desired_activation,
        )
    ]
    if desired_json != current_json:
        diffs.append(
            AdControlSemanticDiffV1(
                target_key=f"shop:{feature_id.value}:{schema_version}",
                field_path="payload",
                current=_json_preview(current_json),
                desired=_json_preview(desired_json),
            )
        )
    return diffs, errors


def _validate_campaign_operation(
    *,
    changeset: AdControlChangeSetV1,
    operation: SetCampaignAdControlFeatureOperation,
    index: int,
    campaign_snapshots: dict[
        tuple[str, int, AdControlFeatureId, int],
        AdControlCampaignFeatureSnapshotV1,
    ],
) -> tuple[list[AdControlSemanticDiffV1] | None, list[ControlPlaneError]]:
    errors: list[ControlPlaneError] = []
    ref = operation.resource
    if ref.shop_id != changeset.scope.shop_id:
        errors.append(
            ControlPlaneError(
                code="SCOPE_SHOP_MISMATCH",
                message="campaign resource shop_id must match changeset scope",
                operation_index=index,
            )
        )
        return None, errors

    body = operation.payload
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
        return None, errors

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
            return None, errors

    campaign = CampaignRef(shop_id=ref.shop_id, advert_id=ref.advert_id)
    try:
        validate_campaign_upsert(
            CampaignFeatureUpsert(
                campaign=campaign,
                feature_id=feature_id,
                schema_version=schema_version,
                mode=body.mode,
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
        return None, errors

    key = (ref.shop_id, ref.advert_id, feature_id, schema_version)
    snapshot = campaign_snapshots.get(key)
    token = operation.preconditions.state_token
    if snapshot is not None and snapshot.state_token != token:
        errors.append(
            ControlPlaneError(
                code="STATE_TOKEN_STALE",
                message="stale campaign feature state_token",
                operation_index=index,
                details={"advert_id": str(ref.advert_id)},
            )
        )
        return None, errors

    desired_json = (
        encode_payload_json(feature_id, decoded) if decoded is not None else None
    )
    current_mode = snapshot.mode.value if snapshot else None
    desired_mode = body.mode.value
    current_json = snapshot.payload_json if snapshot else None

    if current_mode == desired_mode and current_json == desired_json:
        return [], errors

    diffs = [
        AdControlSemanticDiffV1(
            target_key=(
                f"campaign:{ref.advert_id}:{feature_id.value}:{schema_version}"
            ),
            field_path="mode",
            current=current_mode,
            desired=desired_mode,
        )
    ]
    if desired_json != current_json:
        diffs.append(
            AdControlSemanticDiffV1(
                target_key=(
                    f"campaign:{ref.advert_id}:{feature_id.value}:{schema_version}"
                ),
                field_path="payload",
                current=_json_preview(current_json),
                desired=_json_preview(desired_json),
            )
        )
    return diffs, errors


def _json_preview(data: dict[str, object] | None) -> str | None:
    if data is None:
        return None
    return json.dumps(data, sort_keys=True, separators=(",", ":"))
