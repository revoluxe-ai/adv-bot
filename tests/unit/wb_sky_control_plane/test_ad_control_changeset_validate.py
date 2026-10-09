"""Dry-run validation for AdControlChangeSetV1."""

from __future__ import annotations

from decimal import Decimal

import pytest

pytestmark = pytest.mark.unit

from app.modules.ad_control_settings.domain.enums import (
    AdControlFeatureId,
    AdControlFeatureMode,
    ShopFeatureActivation,
)
from app.modules.ad_control_settings.persistence.payload_codec import encode_payload_json
from app.modules.ad_control_settings.domain.configured import DrrPolicyParamsV1
from app.modules.product_control.domain.drr_profile import drr_profile_from_percent
from app.modules.wb_sky_control_plane.kernel.ad_control_validate import (
    AdControlCampaignFeatureSnapshotV1,
    AdControlShopFeatureSnapshotV1,
    validate_ad_control_changeset,
)
from app.modules.wb_sky_control_plane.models.ad_control_changeset import (
    AdControlChangeSetV1,
    AdControlLogicalScopeV1,
    AdControlPreconditionV1,
    AdvertCampaignRefV1,
    CampaignAdControlFeaturePayloadV1,
    SetCampaignAdControlFeatureOperation,
    SetShopAdControlFeatureOperation,
    ShopAdControlFeaturePayloadV1,
)
from app.modules.wb_sky_control_plane.models.enums import DryRunStatus


def _drr_json() -> dict[str, object]:
    payload = DrrPolicyParamsV1(
        profile=drr_profile_from_percent(Decimal("15"), Decimal("20")),
    )
    return encode_payload_json(AdControlFeatureId.DRR_POLICY, payload)


def test_shop_feature_mutation_ok() -> None:
    drr_json = _drr_json()
    changeset = AdControlChangeSetV1(
        changeset_id="cs-1",
        scope=AdControlLogicalScopeV1(shop_id="shop-1"),
        operations=[
            SetShopAdControlFeatureOperation(
                operation_id="op-1",
                preconditions=AdControlPreconditionV1(state_token="acs_new"),
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
    assert len(result.diffs) >= 1


def test_shop_stale_token_rejected() -> None:
    drr_json = _drr_json()
    snap = AdControlShopFeatureSnapshotV1(
        feature_id=AdControlFeatureId.DRR_POLICY,
        schema_version=1,
        activation=ShopFeatureActivation.ENABLED,
        payload_json=drr_json,
        state_token="acs_live",
    )
    changeset = AdControlChangeSetV1(
        changeset_id="cs-2",
        scope=AdControlLogicalScopeV1(shop_id="shop-1"),
        operations=[
            SetShopAdControlFeatureOperation(
                operation_id="op-1",
                preconditions=AdControlPreconditionV1(state_token="acs_wrong"),
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
        shop_snapshots={(AdControlFeatureId.DRR_POLICY, 1): snap},
        campaign_snapshots={},
    )
    assert result.status == DryRunStatus.REJECTED
    assert any(err.code == "STATE_TOKEN_STALE" for err in result.errors)


def test_campaign_shop_mismatch_rejected() -> None:
    changeset = AdControlChangeSetV1(
        changeset_id="cs-3",
        scope=AdControlLogicalScopeV1(shop_id="shop-1"),
        operations=[
            SetCampaignAdControlFeatureOperation(
                operation_id="op-1",
                preconditions=AdControlPreconditionV1(state_token="acs_x"),
                resource=AdvertCampaignRefV1(shop_id="other-shop", advert_id=9),
                payload=CampaignAdControlFeaturePayloadV1(
                    feature_id=AdControlFeatureId.DRR_POLICY,
                    mode=AdControlFeatureMode.INHERIT,
                ),
            )
        ],
    )
    result = validate_ad_control_changeset(changeset, shop_snapshots={}, campaign_snapshots={})
    assert result.status == DryRunStatus.REJECTED
    assert any(err.code == "SCOPE_SHOP_MISMATCH" for err in result.errors)


def test_campaign_no_op_when_unchanged() -> None:
    snap = AdControlCampaignFeatureSnapshotV1(
        shop_id="shop-1",
        advert_id=100,
        feature_id=AdControlFeatureId.DRR_POLICY,
        schema_version=1,
        mode=AdControlFeatureMode.INHERIT,
        payload_json=None,
        state_token="acs_same",
    )
    changeset = AdControlChangeSetV1(
        changeset_id="cs-4",
        scope=AdControlLogicalScopeV1(shop_id="shop-1"),
        operations=[
            SetCampaignAdControlFeatureOperation(
                operation_id="op-1",
                preconditions=AdControlPreconditionV1(state_token="acs_same"),
                resource=AdvertCampaignRefV1(shop_id="shop-1", advert_id=100),
                payload=CampaignAdControlFeaturePayloadV1(
                    feature_id=AdControlFeatureId.DRR_POLICY,
                    mode=AdControlFeatureMode.INHERIT,
                ),
            )
        ],
    )
    key = ("shop-1", 100, AdControlFeatureId.DRR_POLICY, 1)
    result = validate_ad_control_changeset(
        changeset,
        shop_snapshots={},
        campaign_snapshots={key: snap},
    )
    assert result.status == DryRunStatus.NO_OP
