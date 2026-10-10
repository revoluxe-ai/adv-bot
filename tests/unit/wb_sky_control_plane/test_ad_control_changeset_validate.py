"""Dry-run validation for AdControlChangeSetV1."""

from __future__ import annotations

from decimal import Decimal

import pytest

from app.modules.ad_control_settings.domain.enums import (
    AdControlFeatureId,
    AdControlFeatureMode,
    ShopFeatureActivation,
)
from app.modules.ad_control_settings.domain.configured import DrrPolicyParamsV1
from app.modules.ad_control_settings.persistence.cas import AdControlMutationKind
from app.modules.ad_control_settings.persistence.payload_codec import encode_payload_json
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


def _drr_json() -> dict[str, object]:
    payload = DrrPolicyParamsV1(
        profile=drr_profile_from_percent(Decimal("15"), Decimal("20")),
    )
    return encode_payload_json(AdControlFeatureId.DRR_POLICY, payload)


def test_shop_create_requires_absent_revision() -> None:
    drr_json = _drr_json()
    changeset = AdControlChangeSetV1(
        changeset_id="cs-1",
        scope=AdControlLogicalScopeV1(shop_id="shop-1"),
        operations=[
            SetShopAdControlFeatureOperation(
                operation_id="op-1",
                preconditions=AdControlRevisionPreconditionV1(expected_revision=None),
                payload=ShopAdControlFeaturePayloadV1(
                    feature_id=AdControlFeatureId.DRR_POLICY,
                    activation=ShopFeatureActivation.ENABLED,
                    payload=drr_json,
                ),
            )
        ],
    )
    result = validate_ad_control_changeset(changeset, shop_snapshots={}, campaign_snapshots={})
    assert result.status == DryRunStatus.OK
    assert result.diffs[0].intent == AdControlMutationKind.CREATE


def test_shop_create_rejects_wrong_revision_precondition() -> None:
    changeset = AdControlChangeSetV1(
        changeset_id="cs-2",
        scope=AdControlLogicalScopeV1(shop_id="shop-1"),
        operations=[
            SetShopAdControlFeatureOperation(
                operation_id="op-1",
                preconditions=AdControlRevisionPreconditionV1(expected_revision=1),
                payload=ShopAdControlFeaturePayloadV1(
                    feature_id=AdControlFeatureId.DRR_POLICY,
                    activation=ShopFeatureActivation.DISABLED,
                ),
            )
        ],
    )
    result = validate_ad_control_changeset(changeset, shop_snapshots={}, campaign_snapshots={})
    assert result.status == DryRunStatus.REJECTED
    assert any(err.code == "REVISION_CONFLICT" for err in result.errors)


def test_shop_stale_revision_rejected() -> None:
    drr_json = _drr_json()
    snap = AdControlShopFeatureSnapshotV1(
        feature_id=AdControlFeatureId.DRR_POLICY,
        schema_version=1,
        activation=ShopFeatureActivation.ENABLED,
        payload_json=drr_json,
        revision=3,
        state_token="acs_x",
    )
    changeset = AdControlChangeSetV1(
        changeset_id="cs-3",
        scope=AdControlLogicalScopeV1(shop_id="shop-1"),
        operations=[
            SetShopAdControlFeatureOperation(
                operation_id="op-1",
                preconditions=AdControlRevisionPreconditionV1(expected_revision=2),
                payload=ShopAdControlFeaturePayloadV1(
                    feature_id=AdControlFeatureId.DRR_POLICY,
                    activation=ShopFeatureActivation.ENABLED,
                    payload=drr_json,
                ),
            )
        ],
    )
    result = validate_ad_control_changeset(
        changeset,
        shop_snapshots={AdControlFeatureId.DRR_POLICY: snap},
        campaign_snapshots={},
    )
    assert result.status == DryRunStatus.REJECTED
    assert any(err.code == "REVISION_CONFLICT" for err in result.errors)


def test_clear_to_inherit_shows_authority_removed() -> None:
    snap = AdControlCampaignFeatureSnapshotV1(
        shop_id="shop-1",
        advert_id=100,
        feature_id=AdControlFeatureId.DRR_POLICY,
        schema_version=1,
        mode=AdControlFeatureMode.OVERRIDE,
        payload_json=_drr_json(),
        revision=2,
        state_token="acs_y",
    )
    changeset = AdControlChangeSetV1(
        changeset_id="cs-4",
        scope=AdControlLogicalScopeV1(shop_id="shop-1"),
        operations=[
            ClearCampaignAdControlFeatureOperation(
                operation_id="op-1",
                preconditions=AdControlRevisionPreconditionV1(expected_revision=2),
                resource=AdvertCampaignRefV1(shop_id="shop-1", advert_id=100),
                payload=CampaignFeatureTargetV1(feature_id=AdControlFeatureId.DRR_POLICY),
            )
        ],
    )
    key = ("shop-1", 100, AdControlFeatureId.DRR_POLICY)
    result = validate_ad_control_changeset(
        changeset,
        shop_snapshots={},
        campaign_snapshots={key: snap},
    )
    assert result.status == DryRunStatus.OK
    assert result.diffs[0].intent == AdControlMutationKind.CLEAR_TO_INHERIT
    assert result.diffs[0].desired == "absent"


def test_clear_idempotent_when_already_absent() -> None:
    changeset = AdControlChangeSetV1(
        changeset_id="cs-5",
        scope=AdControlLogicalScopeV1(shop_id="shop-1"),
        operations=[
            ClearCampaignAdControlFeatureOperation(
                operation_id="op-1",
                preconditions=AdControlRevisionPreconditionV1(expected_revision=None),
                resource=AdvertCampaignRefV1(shop_id="shop-1", advert_id=100),
                payload=CampaignFeatureTargetV1(feature_id=AdControlFeatureId.DRR_POLICY),
            )
        ],
    )
    result = validate_ad_control_changeset(changeset, shop_snapshots={}, campaign_snapshots={})
    assert result.status == DryRunStatus.NO_OP


def test_campaign_override_create() -> None:
    changeset = AdControlChangeSetV1(
        changeset_id="cs-6",
        scope=AdControlLogicalScopeV1(shop_id="shop-1"),
        operations=[
            SetCampaignAdControlOverrideOperation(
                operation_id="op-1",
                preconditions=AdControlRevisionPreconditionV1(expected_revision=None),
                resource=AdvertCampaignRefV1(shop_id="shop-1", advert_id=9),
                payload=CampaignOverridePayloadV1(
                    feature_id=AdControlFeatureId.DRR_POLICY,
                    payload=_drr_json(),
                ),
            )
        ],
    )
    result = validate_ad_control_changeset(changeset, shop_snapshots={}, campaign_snapshots={})
    assert result.status == DryRunStatus.OK
    assert result.diffs[0].intent == AdControlMutationKind.CREATE


def test_campaign_disable() -> None:
    changeset = AdControlChangeSetV1(
        changeset_id="cs-7",
        scope=AdControlLogicalScopeV1(shop_id="shop-1"),
        operations=[
            DisableCampaignAdControlFeatureOperation(
                operation_id="op-1",
                preconditions=AdControlRevisionPreconditionV1(expected_revision=None),
                resource=AdvertCampaignRefV1(shop_id="shop-1", advert_id=9),
                payload=CampaignFeatureTargetV1(feature_id=AdControlFeatureId.DRR_POLICY),
            )
        ],
    )
    result = validate_ad_control_changeset(changeset, shop_snapshots={}, campaign_snapshots={})
    assert result.status == DryRunStatus.OK
    assert result.diffs[0].intent == AdControlMutationKind.DISABLE
