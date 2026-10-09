"""Diagnostics configured vs effective state (Owner contract A–F)."""

from __future__ import annotations

from decimal import Decimal

import pytest

from app.modules.ad_control_settings.domain.campaign_ref import CampaignRef
from app.modules.ad_control_settings.domain.configured import DrrPolicyParamsV1
from app.modules.ad_control_settings.domain.diagnostics_builder import (
    AdControlDiagnosticsBuilder,
)
from app.modules.ad_control_settings.domain.drr_state import ActualDrrObservation
from app.modules.ad_control_settings.domain.enums import (
    AdControlFeatureId,
    AdControlFeatureMode,
    ControlPathKind,
    DataSufficiency,
    EffectiveSourceKind,
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


def _drr(target: str, max_d: str) -> DrrPolicyParamsV1:
    return DrrPolicyParamsV1(
        profile=drr_profile_from_percent(Decimal(target), Decimal(max_d)),
    )


def _base_ctx(
    shop_features: dict[AdControlFeatureId, ShopFeatureSlot],
    campaign_features: dict[AdControlFeatureId, CampaignFeatureSlot],
) -> ResolverContext:
    return ResolverContext(
        enrollment=HierarchicalEnrollment.ENROLLED,
        control_path=ControlPathKind.HIERARCHICAL,
        shop_id="shop-a",
        shop_features=shop_features,
        campaign=CampaignRef(shop_id="shop-a", advert_id=42),
        campaign_features=campaign_features,
    )


@pytest.mark.unit
def test_a_shop_configured_feature_in_diagnostics() -> None:
    ctx = _base_ctx(
        {AdControlFeatureId.DRR_POLICY: ShopFeatureSlot(
            activation=ShopFeatureActivation.ENABLED,
            payload=_drr("15", "20"),
        )},
        {AdControlFeatureId.DRR_POLICY: CampaignFeatureSlot(
            mode=AdControlFeatureMode.INHERIT,
            payload=None,
        )},
    )
    report = AdControlDiagnosticsBuilder.build(ctx, None)
    shop_drr = next(
        r for r in report.configured_shop_features
        if r.feature_id == AdControlFeatureId.DRR_POLICY
    )
    assert shop_drr.activation == ShopFeatureActivation.ENABLED
    assert shop_drr.payload is not None
    assert shop_drr.schema_version == 1


@pytest.mark.unit
def test_b_campaign_override_in_diagnostics() -> None:
    override = _drr("8", "12")
    ctx = _base_ctx(
        {AdControlFeatureId.DRR_POLICY: ShopFeatureSlot(
            activation=ShopFeatureActivation.ENABLED,
            payload=_drr("15", "20"),
        )},
        {AdControlFeatureId.DRR_POLICY: CampaignFeatureSlot(
            mode=AdControlFeatureMode.OVERRIDE,
            payload=override,
        )},
    )
    report = AdControlDiagnosticsBuilder.build(ctx, None)
    camp = next(
        r for r in report.configured_campaign_overrides
        if r.feature_id == AdControlFeatureId.DRR_POLICY
    )
    assert camp.mode == AdControlFeatureMode.OVERRIDE
    assert camp.override_payload is override
    assert camp.schema_version == 1


@pytest.mark.unit
def test_c_inherit_does_not_fabricate_campaign_configured_value() -> None:
    ctx = _base_ctx(
        {AdControlFeatureId.DRR_POLICY: ShopFeatureSlot(
            activation=ShopFeatureActivation.ENABLED,
            payload=_drr("15", "20"),
        )},
        {AdControlFeatureId.DRR_POLICY: CampaignFeatureSlot(
            mode=AdControlFeatureMode.INHERIT,
            payload=None,
        )},
    )
    report = AdControlDiagnosticsBuilder.build(ctx, None)
    camp = next(
        r for r in report.configured_campaign_overrides
        if r.feature_id == AdControlFeatureId.DRR_POLICY
    )
    assert camp.mode == AdControlFeatureMode.INHERIT
    assert camp.override_payload is None


@pytest.mark.unit
def test_d_campaign_disabled_truthful() -> None:
    ctx = _base_ctx(
        {AdControlFeatureId.DRR_POLICY: ShopFeatureSlot(
            activation=ShopFeatureActivation.ENABLED,
            payload=_drr("15", "20"),
        )},
        {AdControlFeatureId.DRR_POLICY: CampaignFeatureSlot(
            mode=AdControlFeatureMode.DISABLED,
            payload=None,
        )},
    )
    report = AdControlDiagnosticsBuilder.build(ctx, None)
    camp = next(
        r for r in report.configured_campaign_overrides
        if r.feature_id == AdControlFeatureId.DRR_POLICY
    )
    assert camp.mode == AdControlFeatureMode.DISABLED
    eff = next(
        e for e in report.effective_features if e.feature_id == AdControlFeatureId.DRR_POLICY
    )
    assert eff.active is False
    assert AdControlReasonCode.FEATURE_DISABLED_AT_CAMPAIGN in eff.reason_codes


@pytest.mark.unit
def test_e_f_effective_differs_from_configured_without_ambiguity() -> None:
    ctx = _base_ctx(
        {AdControlFeatureId.DRR_POLICY: ShopFeatureSlot(
            activation=ShopFeatureActivation.ENABLED,
            payload=_drr("13", "20"),
        )},
        {AdControlFeatureId.DRR_POLICY: CampaignFeatureSlot(
            mode=AdControlFeatureMode.INHERIT,
            payload=None,
        )},
    )
    report = AdControlDiagnosticsBuilder.build(
        ctx,
        ActualDrrObservation(
            actual_drr_percent=Decimal(10),
            measurement_window_id="7d",
            data_sufficiency=DataSufficiency.SUFFICIENT,
            attribution_lag_days=1,
        ),
    )
    shop_row = next(
        r for r in report.configured_shop_features
        if r.feature_id == AdControlFeatureId.DRR_POLICY
    )
    assert isinstance(shop_row.payload, DrrPolicyParamsV1)
    assert shop_row.payload.profile.target_drr_percent == Decimal(13)

    camp_row = next(
        r for r in report.configured_campaign_overrides
        if r.feature_id == AdControlFeatureId.DRR_POLICY
    )
    assert camp_row.override_payload is None

    eff = next(
        e for e in report.effective_features if e.feature_id == AdControlFeatureId.DRR_POLICY
    )
    assert eff.active is True
    assert eff.provenance.source_kind == EffectiveSourceKind.SHOP_POLICY
    assert isinstance(eff.payload, DrrPolicyParamsV1)
    assert eff.payload.profile.target_drr_percent == Decimal(13)


@pytest.mark.unit
def test_shop_enabled_missing_payload_fail_closed() -> None:
    ctx = _base_ctx(
        {AdControlFeatureId.DRR_POLICY: ShopFeatureSlot(
            activation=ShopFeatureActivation.ENABLED,
            payload=None,
        )},
        {AdControlFeatureId.DRR_POLICY: CampaignFeatureSlot(
            mode=AdControlFeatureMode.INHERIT,
            payload=None,
        )},
    )
    blocked = AdControlSettingsResolver.resolve_feature(
        ctx,
        AdControlFeatureId.DRR_POLICY,
    )
    assert isinstance(blocked, ResolverBlocked)
    assert AdControlReasonCode.SHOP_ENABLED_MISSING_PAYLOAD in blocked.reason_codes
