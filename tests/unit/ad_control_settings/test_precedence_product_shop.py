"""CAMPAIGN > PRODUCT > SHOP precedence and headroom eligibility."""

from __future__ import annotations

from decimal import Decimal

import pytest

from app.modules.ad_control_settings.domain.campaign_ref import CampaignRef
from app.modules.ad_control_settings.domain.configured import DrrPolicyParamsV1
from app.modules.ad_control_settings.domain.drr_state import ActualDrrObservation
from app.modules.ad_control_settings.domain.enums import (
    AdControlFeatureId,
    AdControlFeatureMode,
    ControlPathKind,
    DataSufficiency,
    HierarchicalEnrollment,
    ShopFeatureActivation,
)
from app.modules.ad_control_settings.domain.headroom_eval import (
    campaign_headroom_eligibility,
)
from app.modules.ad_control_settings.domain.product_adapter import (
    ProductDrrPolicyAdapterBlocked,
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


@pytest.mark.unit
def test_product_adapter_blocked_falls_through_to_shop_drr() -> None:
    shop_policy = DrrPolicyParamsV1(
        profile=drr_profile_from_percent(Decimal(15), Decimal(20)),
    )
    ctx = ResolverContext(
        enrollment=HierarchicalEnrollment.ENROLLED,
        control_path=ControlPathKind.HIERARCHICAL,
        shop_id="s",
        shop_features={
            AdControlFeatureId.DRR_POLICY: ShopFeatureSlot(
                activation=ShopFeatureActivation.ENABLED,
                payload=shop_policy,
            ),
        },
        campaign=CampaignRef(shop_id="s", advert_id=1),
        campaign_features={
            AdControlFeatureId.DRR_POLICY: CampaignFeatureSlot(
                mode=AdControlFeatureMode.INHERIT,
                payload=None,
            ),
        },
        product_drr=ProductDrrPolicyAdapterBlocked(
            reason=AdControlReasonCode.PRODUCT_DRR_ADAPTER_BLOCKED,
        ),
    )
    resolved = AdControlSettingsResolver.resolve_feature(
        ctx,
        AdControlFeatureId.DRR_POLICY,
    )
    assert not isinstance(resolved, ResolverBlocked)
    assert isinstance(resolved.payload, DrrPolicyParamsV1)
    assert resolved.payload.profile.target_drr_percent == Decimal(15)


@pytest.mark.unit
def test_legacy_passthrough_headroom_uses_legacy_reason_not_not_enrolled() -> None:
    eligibility = campaign_headroom_eligibility(
        CampaignRef(shop_id="s", advert_id=1),
        ActualDrrObservation(
            actual_drr_percent=Decimal(10),
            measurement_window_id="7d",
            data_sufficiency=DataSufficiency.SUFFICIENT,
            attribution_lag_days=1,
        ),
        enrollment=HierarchicalEnrollment.ENROLLED,
        control_path=ControlPathKind.LEGACY_PASSTHROUGH,
        hierarchical_resolver_available=False,
    )
    assert AdControlReasonCode.LEGACY_PASSTHROUGH_ACTIVE in eligibility.reason_codes
    assert AdControlReasonCode.NOT_ENROLLED_FAIL_CLOSED not in eligibility.reason_codes
