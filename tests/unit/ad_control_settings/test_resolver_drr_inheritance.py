"""Live DRR inheritance и Owner scenarios (foundation slice)."""

from __future__ import annotations

from decimal import Decimal

import pytest

from app.modules.ad_control_settings.domain.campaign_ref import CampaignRef
from app.modules.ad_control_settings.domain.configured import DrrPolicyParamsV1
from app.modules.ad_control_settings.domain.enums import (
    AdControlFeatureId,
    AdControlFeatureMode,
    ControlPathKind,
    HierarchicalEnrollment,
    ShopFeatureActivation,
)
from app.modules.ad_control_settings.domain.reason_codes import AdControlReasonCode
from app.modules.ad_control_settings.domain.resolver import AdControlSettingsResolver
from app.modules.ad_control_settings.domain.resolver_models import (
    CampaignFeatureSlot,
    ResolverBlocked,
    ResolverContext,
    ShopFeatureSlot,
)
from app.modules.product_control.domain.drr_profile import drr_profile_from_percent


def _shop_drr(target: str, max_drr: str) -> DrrPolicyParamsV1:
    return DrrPolicyParamsV1(
        profile=drr_profile_from_percent(Decimal(target), Decimal(max_drr)),
    )


def _ctx(
    shop_features: dict,
    campaign_features: dict,
    *,
    shop_id: str = "shop-1",
    advert_id: int = 1001,
) -> ResolverContext:
    return ResolverContext(
        enrollment=HierarchicalEnrollment.ENROLLED,
        control_path=ControlPathKind.HIERARCHICAL,
        shop_id=shop_id,
        shop_features=shop_features,
        campaign=CampaignRef(shop_id=shop_id, advert_id=advert_id),
        campaign_features=campaign_features,
    )


@pytest.mark.unit
def test_campaign_inherit_tracks_live_shop_target() -> None:
    """Campaign A INHERIT: shop 15% -> 13% меняет effective без copy в campaign row."""
    shop_payload = _shop_drr("15", "20")
    campaign_features = {
        AdControlFeatureId.DRR_POLICY: CampaignFeatureSlot(
            mode=AdControlFeatureMode.INHERIT,
            payload=None,
        ),
    }
    ctx_15 = _ctx(
        {
            AdControlFeatureId.DRR_POLICY: ShopFeatureSlot(
                activation=ShopFeatureActivation.ENABLED,
                payload=shop_payload,
            ),
        },
        campaign_features,
    )
    resolved_15 = AdControlSettingsResolver.resolve_feature(
        ctx_15,
        AdControlFeatureId.DRR_POLICY,
    )
    assert not isinstance(resolved_15, ResolverBlocked)
    assert isinstance(resolved_15.payload, DrrPolicyParamsV1)
    assert resolved_15.payload.profile.target_drr_percent == Decimal(15)

    shop_payload_13 = _shop_drr("13", "20")
    ctx_13 = _ctx(
        {
            AdControlFeatureId.DRR_POLICY: ShopFeatureSlot(
                activation=ShopFeatureActivation.ENABLED,
                payload=shop_payload_13,
            ),
        },
        campaign_features,
    )
    resolved_13 = AdControlSettingsResolver.resolve_feature(
        ctx_13,
        AdControlFeatureId.DRR_POLICY,
    )
    assert not isinstance(resolved_13, ResolverBlocked)
    assert isinstance(resolved_13.payload, DrrPolicyParamsV1)
    assert resolved_13.payload.profile.target_drr_percent == Decimal(13)


@pytest.mark.unit
def test_campaign_override_stays_8_percent_when_shop_changes() -> None:
    campaign_features = {
        AdControlFeatureId.DRR_POLICY: CampaignFeatureSlot(
            mode=AdControlFeatureMode.OVERRIDE,
            payload=_shop_drr("8", "12"),
        ),
    }
    ctx = _ctx(
        {
            AdControlFeatureId.DRR_POLICY: ShopFeatureSlot(
                activation=ShopFeatureActivation.ENABLED,
                payload=_shop_drr("13", "20"),
            ),
        },
        campaign_features,
    )
    resolved = AdControlSettingsResolver.resolve_feature(
        ctx,
        AdControlFeatureId.DRR_POLICY,
    )
    assert not isinstance(resolved, ResolverBlocked)
    assert isinstance(resolved.payload, DrrPolicyParamsV1)
    assert resolved.payload.profile.target_drr_percent == Decimal(8)


@pytest.mark.unit
def test_campaign_disabled_unmanaged() -> None:
    ctx = _ctx(
        {
            AdControlFeatureId.DRR_POLICY: ShopFeatureSlot(
                activation=ShopFeatureActivation.ENABLED,
                payload=_shop_drr("15", "20"),
            ),
        },
        {
            AdControlFeatureId.DRR_POLICY: CampaignFeatureSlot(
                mode=AdControlFeatureMode.DISABLED,
                payload=None,
            ),
        },
    )
    resolved = AdControlSettingsResolver.resolve_feature(
        ctx,
        AdControlFeatureId.DRR_POLICY,
    )
    assert not isinstance(resolved, ResolverBlocked)
    assert resolved.active is False
    assert AdControlReasonCode.FEATURE_DISABLED_AT_CAMPAIGN in resolved.reason_codes


@pytest.mark.unit
def test_not_enrolled_fail_closed() -> None:
    ctx = ResolverContext(
        enrollment=HierarchicalEnrollment.NOT_ENROLLED,
        control_path=ControlPathKind.HIERARCHICAL,
        shop_id="s",
        shop_features={},
        campaign=CampaignRef(shop_id="s", advert_id=1),
        campaign_features={},
    )
    blocked = AdControlSettingsResolver.resolve_feature(
        ctx,
        AdControlFeatureId.DRR_POLICY,
    )
    assert isinstance(blocked, ResolverBlocked)
    assert AdControlReasonCode.NOT_ENROLLED_FAIL_CLOSED in blocked.reason_codes


@pytest.mark.unit
def test_legacy_passthrough_blocks_hierarchical_resolver() -> None:
    ctx = ResolverContext(
        enrollment=HierarchicalEnrollment.ENROLLED,
        control_path=ControlPathKind.LEGACY_PASSTHROUGH,
        shop_id="s",
        shop_features={},
        campaign=CampaignRef(shop_id="s", advert_id=1),
        campaign_features={},
    )
    blocked = AdControlSettingsResolver.resolve_feature(
        ctx,
        AdControlFeatureId.DRR_POLICY,
    )
    assert isinstance(blocked, ResolverBlocked)
    assert AdControlReasonCode.LEGACY_PASSTHROUGH_ACTIVE in blocked.reason_codes
