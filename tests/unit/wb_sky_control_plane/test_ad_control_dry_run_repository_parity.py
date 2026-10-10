"""Dry-run mutation classification MUST match repository CAS semantics."""

from __future__ import annotations

from datetime import UTC, datetime
from decimal import Decimal

import pytest

from app.modules.ad_control_settings.domain.campaign_ref import CampaignRef
from app.modules.ad_control_settings.domain.configured import DrrPolicyParamsV1
from app.modules.ad_control_settings.domain.enums import (
    AdControlFeatureId,
    AdControlFeatureMode,
    ShopFeatureActivation,
)
from app.modules.ad_control_settings.persistence.cas import AdControlMutationKind
from app.modules.ad_control_settings.persistence.models import (
    AdControlCampaignFeatureRow,
    AdControlShopFeatureRow,
)
from app.modules.ad_control_settings.persistence.payload_codec import encode_payload_json
from app.modules.ad_control_settings.persistence.repository import (
    CampaignDisableUpsert,
    CampaignOverrideUpsert,
    ShopFeatureUpsert,
    classify_campaign_disable_is_no_op,
    classify_campaign_override_is_no_op,
    classify_shop_mutation_kind,
)
from app.modules.product_control.domain.drr_profile import drr_profile_from_percent
from app.modules.wb_sky_control_plane.kernel.ad_control_validate import (
    AdControlCampaignFeatureSnapshotV1,
    AdControlShopFeatureSnapshotV1,
    validate_ad_control_changeset,
)
from app.modules.wb_sky_control_plane.models.ad_control_changeset import (
    AdControlChangeSetV1,
    AdControlLogicalScopeV1,
    AdControlRevisionPreconditionV1,
    AdvertCampaignRefV1,
    CampaignFeatureTargetV1,
    CampaignOverridePayloadV1,
    ClearCampaignAdControlFeatureOperation,
    DisableCampaignAdControlFeatureOperation,
    SetCampaignAdControlOverrideOperation,
    SetShopAdControlFeatureOperation,
    ShopAdControlFeaturePayloadV1,
)
from app.modules.wb_sky_control_plane.models.enums import DryRunStatus

pytestmark = pytest.mark.unit

_NOW = datetime.now(tz=UTC)


def _drr_profile(low: str = "15", high: str = "20") -> DrrPolicyParamsV1:
    return DrrPolicyParamsV1(
        profile=drr_profile_from_percent(Decimal(low), Decimal(high)),
    )


def _drr_json(low: str = "15", high: str = "20") -> dict[str, object]:
    return encode_payload_json(AdControlFeatureId.DRR_POLICY, _drr_profile(low, high))


def _shop_row(
    *,
    schema_version: int = 1,
    activation: ShopFeatureActivation = ShopFeatureActivation.ENABLED,
    payload_json: dict[str, object] | None = None,
    revision: int = 1,
) -> AdControlShopFeatureRow:
    return AdControlShopFeatureRow(
        shop_id="shop-1",
        feature_id=AdControlFeatureId.DRR_POLICY.value,
        schema_version=schema_version,
        activation=activation.value,
        payload_json=payload_json,
        revision=revision,
        state_token="tok",
        updated_at=_NOW,
    )


def _shop_snap(row: AdControlShopFeatureRow) -> AdControlShopFeatureSnapshotV1:
    return AdControlShopFeatureSnapshotV1(
        feature_id=AdControlFeatureId.DRR_POLICY,
        schema_version=row.schema_version,
        activation=ShopFeatureActivation(row.activation),
        payload_json=row.payload_json,
        revision=row.revision,
        state_token=row.state_token,
    )


def _campaign_row(
    *,
    mode: AdControlFeatureMode = AdControlFeatureMode.OVERRIDE,
    schema_version: int = 1,
    payload_json: dict[str, object] | None = None,
    revision: int = 1,
) -> AdControlCampaignFeatureRow:
    return AdControlCampaignFeatureRow(
        shop_id="shop-1",
        advert_id=9,
        feature_id=AdControlFeatureId.DRR_POLICY.value,
        schema_version=schema_version,
        mode=mode.value,
        payload_json=payload_json,
        revision=revision,
        state_token="tok",
        updated_at=_NOW,
    )


def _campaign_snap(
    row: AdControlCampaignFeatureRow,
) -> AdControlCampaignFeatureSnapshotV1:
    return AdControlCampaignFeatureSnapshotV1(
        shop_id=row.shop_id,
        advert_id=row.advert_id,
        feature_id=AdControlFeatureId.DRR_POLICY,
        schema_version=row.schema_version,
        mode=AdControlFeatureMode(row.mode),
        payload_json=row.payload_json,
        revision=row.revision,
        state_token=row.state_token,
    )


def _dry_run_shop(
    *,
    snapshot: AdControlShopFeatureSnapshotV1 | None,
    body: ShopAdControlFeaturePayloadV1,
    expected_revision: int | None,
) -> tuple[DryRunStatus, AdControlMutationKind | None, list[str]]:
    changeset = AdControlChangeSetV1(
        changeset_id="parity-shop",
        scope=AdControlLogicalScopeV1(shop_id="shop-1"),
        operations=[
            SetShopAdControlFeatureOperation(
                operation_id="op-1",
                preconditions=AdControlRevisionPreconditionV1(
                    expected_revision=expected_revision
                ),
                payload=body,
            )
        ],
    )
    shop_snaps = (
        {AdControlFeatureId.DRR_POLICY: snapshot} if snapshot is not None else {}
    )
    result = validate_ad_control_changeset(
        changeset, shop_snapshots=shop_snaps, campaign_snapshots={}
    )
    error_codes = [err.code for err in result.errors]
    if result.status == DryRunStatus.REJECTED:
        return result.status, None, error_codes
    if result.status == DryRunStatus.NO_OP:
        return result.status, AdControlMutationKind.NO_OP, error_codes
    return result.status, result.diffs[0].intent, error_codes


def _shop_upsert_from_body(body: ShopAdControlFeaturePayloadV1) -> ShopFeatureUpsert:
    decoded = None
    if body.payload is not None:
        decoded = _drr_profile()
        if body.payload != _drr_json():
            decoded = _drr_profile("10", "12")
    return ShopFeatureUpsert(
        shop_id="shop-1",
        feature_id=body.feature_id,
        schema_version=body.schema_version,
        activation=body.activation,
        payload=decoded,
    )


@pytest.mark.parametrize(
    ("name", "existing", "body", "expected_revision", "repo_kind"),
    [
        (
            "CREATE",
            None,
            ShopAdControlFeaturePayloadV1(
                feature_id=AdControlFeatureId.DRR_POLICY,
                schema_version=1,
                activation=ShopFeatureActivation.ENABLED,
                payload=_drr_json(),
            ),
            None,
            AdControlMutationKind.CREATE,
        ),
        (
            "UPDATE",
            _shop_row(payload_json=_drr_json("10", "12")),
            ShopAdControlFeaturePayloadV1(
                feature_id=AdControlFeatureId.DRR_POLICY,
                schema_version=1,
                activation=ShopFeatureActivation.ENABLED,
                payload=_drr_json(),
            ),
            1,
            AdControlMutationKind.UPDATE,
        ),
        (
            "DISABLE",
            _shop_row(payload_json=_drr_json()),
            ShopAdControlFeaturePayloadV1(
                feature_id=AdControlFeatureId.DRR_POLICY,
                schema_version=1,
                activation=ShopFeatureActivation.DISABLED,
            ),
            1,
            AdControlMutationKind.DISABLE,
        ),
        (
            "NO_OP",
            _shop_row(payload_json=_drr_json()),
            ShopAdControlFeaturePayloadV1(
                feature_id=AdControlFeatureId.DRR_POLICY,
                schema_version=1,
                activation=ShopFeatureActivation.ENABLED,
                payload=_drr_json(),
            ),
            1,
            AdControlMutationKind.NO_OP,
        ),
    ],
    ids=["CREATE", "UPDATE", "DISABLE", "NO_OP"],
)
def test_shop_dry_run_matches_repository_kind(
    name: str,
    existing: AdControlShopFeatureRow | None,
    body: ShopAdControlFeaturePayloadV1,
    expected_revision: int | None,
    repo_kind: AdControlMutationKind,
) -> None:
    if existing is None:
        repository_kind = repo_kind
    else:
        repository_kind = classify_shop_mutation_kind(
            existing, _shop_upsert_from_body(body)
        )

    status, dry_kind, _ = _dry_run_shop(
        snapshot=_shop_snap(existing) if existing else None,
        body=body,
        expected_revision=expected_revision,
    )
    assert repository_kind == repo_kind
    if repo_kind == AdControlMutationKind.NO_OP:
        assert status == DryRunStatus.NO_OP
        assert dry_kind == AdControlMutationKind.NO_OP
    else:
        assert status == DryRunStatus.OK
        assert dry_kind == repo_kind


def test_shop_repository_schema_version_breaks_no_op() -> None:
    row = _shop_row(schema_version=1, payload_json=_drr_json())
    upsert = ShopFeatureUpsert(
        shop_id="shop-1",
        feature_id=AdControlFeatureId.DRR_POLICY,
        schema_version=2,
        activation=ShopFeatureActivation.ENABLED,
        payload=_drr_profile(),
    )
    assert classify_shop_mutation_kind(row, upsert) == AdControlMutationKind.UPDATE


def test_shop_dry_run_same_payload_different_schema_version_not_no_op() -> None:
    row = _shop_row(schema_version=1, payload_json=_drr_json())
    body = ShopAdControlFeaturePayloadV1(
        feature_id=AdControlFeatureId.DRR_POLICY,
        schema_version=1,
        activation=ShopFeatureActivation.ENABLED,
        payload=_drr_json(),
    )
    body_v2 = body.model_copy(update={"schema_version": 2})
    status, kind, codes = _dry_run_shop(
        snapshot=_shop_snap(row),
        body=body_v2,
        expected_revision=1,
    )
    assert AdControlMutationKind.NO_OP != kind
    assert status == DryRunStatus.REJECTED
    assert "UNSUPPORTED_SCHEMA_VERSION" in codes


def test_shop_revision_conflict_when_row_exists_but_create_revision() -> None:
    status, _, codes = _dry_run_shop(
        snapshot=_shop_snap(_shop_row()),
        body=ShopAdControlFeaturePayloadV1(
            feature_id=AdControlFeatureId.DRR_POLICY,
            activation=ShopFeatureActivation.ENABLED,
            payload=_drr_json(),
        ),
        expected_revision=None,
    )
    assert status == DryRunStatus.REJECTED
    assert "REVISION_CONFLICT" in codes


def test_campaign_override_create_update_no_op_parity() -> None:
    drr = _drr_json()
    status, kind, _ = _dry_run_campaign_override(
        snapshot=None,
        body=CampaignOverridePayloadV1(
            feature_id=AdControlFeatureId.DRR_POLICY,
            schema_version=1,
            payload=drr,
        ),
        expected_revision=None,
    )
    assert status == DryRunStatus.OK
    assert kind == AdControlMutationKind.CREATE

    row = _campaign_row(payload_json=drr)
    snap = _campaign_snap(row)
    alt_json = _drr_json("10", "12")
    assert not classify_campaign_override_is_no_op(
        row,
        CampaignOverrideUpsert(
            campaign=CampaignRef(shop_id="shop-1", advert_id=9),
            feature_id=AdControlFeatureId.DRR_POLICY,
            schema_version=1,
            payload=_drr_profile("10", "12"),
        ),
        alt_json,
    )
    status, kind, _ = _dry_run_campaign_override(
        snapshot=snap,
        body=CampaignOverridePayloadV1(
            feature_id=AdControlFeatureId.DRR_POLICY,
            schema_version=1,
            payload=alt_json,
        ),
        expected_revision=1,
    )
    assert kind == AdControlMutationKind.UPDATE

    upsert = CampaignOverrideUpsert(
        campaign=CampaignRef(shop_id="shop-1", advert_id=9),
        feature_id=AdControlFeatureId.DRR_POLICY,
        schema_version=1,
        payload=_drr_profile(),
    )
    assert classify_campaign_override_is_no_op(row, upsert, drr)
    status, kind, _ = _dry_run_campaign_override(
        snapshot=snap,
        body=CampaignOverridePayloadV1(
            feature_id=AdControlFeatureId.DRR_POLICY,
            schema_version=1,
            payload=drr,
        ),
        expected_revision=1,
    )
    assert status == DryRunStatus.NO_OP
    assert kind == AdControlMutationKind.NO_OP


def _dry_run_campaign_override(
    *,
    snapshot: AdControlCampaignFeatureSnapshotV1 | None,
    body: CampaignOverridePayloadV1,
    expected_revision: int | None,
) -> tuple[DryRunStatus, AdControlMutationKind | None, list[str]]:
    changeset = AdControlChangeSetV1(
        changeset_id="parity-camp-ov",
        scope=AdControlLogicalScopeV1(shop_id="shop-1"),
        operations=[
            SetCampaignAdControlOverrideOperation(
                operation_id="op-1",
                preconditions=AdControlRevisionPreconditionV1(
                    expected_revision=expected_revision
                ),
                resource=AdvertCampaignRefV1(shop_id="shop-1", advert_id=9),
                payload=body,
            )
        ],
    )
    camp_snaps: dict[
        tuple[str, int, AdControlFeatureId],
        AdControlCampaignFeatureSnapshotV1,
    ] = {}
    if snapshot is not None:
        camp_snaps[("shop-1", 9, AdControlFeatureId.DRR_POLICY)] = snapshot
    result = validate_ad_control_changeset(
        changeset, shop_snapshots={}, campaign_snapshots=camp_snaps
    )
    error_codes = [err.code for err in result.errors]
    if result.status == DryRunStatus.REJECTED:
        return result.status, None, error_codes
    if result.status == DryRunStatus.NO_OP:
        return result.status, AdControlMutationKind.NO_OP, error_codes
    return result.status, result.diffs[0].intent, error_codes


def test_campaign_disable_no_op_requires_schema_version_match() -> None:
    row = _campaign_row(
        mode=AdControlFeatureMode.DISABLED,
        schema_version=1,
        payload_json=None,
    )
    snap = _campaign_snap(row)
    upsert = CampaignDisableUpsert(
        campaign=CampaignRef(shop_id="shop-1", advert_id=9),
        feature_id=AdControlFeatureId.DRR_POLICY,
        schema_version=1,
    )
    assert classify_campaign_disable_is_no_op(row, upsert)
    status, kind, _ = _dry_run_campaign_disable(
        snapshot=snap,
        schema_version=1,
        expected_revision=1,
    )
    assert status == DryRunStatus.NO_OP
    assert kind == AdControlMutationKind.NO_OP

    upsert_v2 = CampaignDisableUpsert(
        campaign=CampaignRef(shop_id="shop-1", advert_id=9),
        feature_id=AdControlFeatureId.DRR_POLICY,
        schema_version=2,
    )
    assert not classify_campaign_disable_is_no_op(row, upsert_v2)
    status, kind, _ = _dry_run_campaign_disable(
        snapshot=snap,
        schema_version=2,
        expected_revision=1,
    )
    assert status == DryRunStatus.REJECTED
    assert kind is None


def _dry_run_campaign_disable(
    *,
    snapshot: AdControlCampaignFeatureSnapshotV1 | None,
    schema_version: int,
    expected_revision: int | None,
) -> tuple[DryRunStatus, AdControlMutationKind | None, list[str]]:
    changeset = AdControlChangeSetV1(
        changeset_id="parity-camp-dis",
        scope=AdControlLogicalScopeV1(shop_id="shop-1"),
        operations=[
            DisableCampaignAdControlFeatureOperation(
                operation_id="op-1",
                preconditions=AdControlRevisionPreconditionV1(
                    expected_revision=expected_revision
                ),
                resource=AdvertCampaignRefV1(shop_id="shop-1", advert_id=9),
                payload=CampaignFeatureTargetV1(
                    feature_id=AdControlFeatureId.DRR_POLICY,
                    schema_version=schema_version,
                ),
            )
        ],
    )
    camp_snaps: dict[
        tuple[str, int, AdControlFeatureId],
        AdControlCampaignFeatureSnapshotV1,
    ] = {}
    if snapshot is not None:
        camp_snaps[("shop-1", 9, AdControlFeatureId.DRR_POLICY)] = snapshot
    result = validate_ad_control_changeset(
        changeset, shop_snapshots={}, campaign_snapshots=camp_snaps
    )
    error_codes = [err.code for err in result.errors]
    if result.status == DryRunStatus.REJECTED:
        return result.status, None, error_codes
    if result.status == DryRunStatus.NO_OP:
        return result.status, AdControlMutationKind.NO_OP, error_codes
    return result.status, result.diffs[0].intent, error_codes


def test_campaign_disable_create_and_clear_paths() -> None:
    status, kind, _ = _dry_run_campaign_disable(
        snapshot=None,
        schema_version=1,
        expected_revision=None,
    )
    assert status == DryRunStatus.OK
    assert kind == AdControlMutationKind.DISABLE

    snap = _campaign_snap(_campaign_row())
    changeset = AdControlChangeSetV1(
        changeset_id="parity-clear",
        scope=AdControlLogicalScopeV1(shop_id="shop-1"),
        operations=[
            ClearCampaignAdControlFeatureOperation(
                operation_id="op-1",
                preconditions=AdControlRevisionPreconditionV1(expected_revision=1),
                resource=AdvertCampaignRefV1(shop_id="shop-1", advert_id=9),
                payload=CampaignFeatureTargetV1(
                    feature_id=AdControlFeatureId.DRR_POLICY,
                ),
            )
        ],
    )
    camp_key: tuple[str, int, AdControlFeatureId] = (
        "shop-1",
        9,
        AdControlFeatureId.DRR_POLICY,
    )
    result = validate_ad_control_changeset(
        changeset,
        shop_snapshots={},
        campaign_snapshots={camp_key: snap},
    )
    assert result.diffs[0].intent == AdControlMutationKind.CLEAR_TO_INHERIT

    absent_changeset = AdControlChangeSetV1(
        changeset_id="parity-clear-absent",
        scope=AdControlLogicalScopeV1(shop_id="shop-1"),
        operations=[
            ClearCampaignAdControlFeatureOperation(
                operation_id="op-clear-absent",
                preconditions=AdControlRevisionPreconditionV1(expected_revision=None),
                resource=AdvertCampaignRefV1(shop_id="shop-1", advert_id=9),
                payload=CampaignFeatureTargetV1(
                    feature_id=AdControlFeatureId.DRR_POLICY,
                ),
            )
        ],
    )
    absent = validate_ad_control_changeset(
        absent_changeset,
        shop_snapshots={},
        campaign_snapshots={},
    )
    assert absent.status == DryRunStatus.NO_OP
