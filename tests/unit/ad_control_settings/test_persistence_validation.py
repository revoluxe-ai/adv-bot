"""Unit tests shop/campaign upsert validation (no PG)."""

from __future__ import annotations

from decimal import Decimal

import pytest

pytestmark = pytest.mark.unit

from app.modules.ad_control_settings.domain.campaign_ref import CampaignRef
from app.modules.ad_control_settings.domain.configured import DrrPolicyParamsV1
from app.modules.ad_control_settings.domain.enums import (
    AdControlFeatureId,
    AdControlFeatureMode,
    ShopFeatureActivation,
)
from app.modules.ad_control_settings.persistence.repository import (
    AdControlPersistenceError,
    CampaignFeatureUpsert,
    ShopFeatureUpsert,
    validate_campaign_upsert,
    validate_shop_upsert,
)
from app.modules.product_control.domain.drr_profile import drr_profile_from_percent


def test_shop_enabled_requires_payload() -> None:
    with pytest.raises(AdControlPersistenceError):
        validate_shop_upsert(
            ShopFeatureUpsert(
                shop_id="s1",
                feature_id=AdControlFeatureId.DRR_POLICY,
                schema_version=1,
                activation=ShopFeatureActivation.ENABLED,
                payload=None,
            )
        )


def test_campaign_override_requires_payload() -> None:
    drr = DrrPolicyParamsV1(
        profile=drr_profile_from_percent(Decimal("8"), Decimal("12")),
    )
    validate_campaign_upsert(
        CampaignFeatureUpsert(
            campaign=CampaignRef(shop_id="s1", advert_id=42),
            feature_id=AdControlFeatureId.DRR_POLICY,
            schema_version=1,
            mode=AdControlFeatureMode.OVERRIDE,
            payload=drr,
        )
    )


def test_campaign_inherit_rejects_payload() -> None:
    drr = DrrPolicyParamsV1(
        profile=drr_profile_from_percent(Decimal("8"), Decimal("12")),
    )
    with pytest.raises(AdControlPersistenceError):
        validate_campaign_upsert(
            CampaignFeatureUpsert(
                campaign=CampaignRef(shop_id="s1", advert_id=42),
                feature_id=AdControlFeatureId.DRR_POLICY,
                schema_version=1,
                mode=AdControlFeatureMode.INHERIT,
                payload=drr,
            )
        )
