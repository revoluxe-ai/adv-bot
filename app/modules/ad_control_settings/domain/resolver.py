"""
Pure Shop/Campaign resolver: INHERIT | OVERRIDE | DISABLED per feature.

Live inheritance: campaign INHERIT читает текущий shop payload без copy-on-write.
"""

from __future__ import annotations

from app.modules.ad_control_settings.domain.configured import DrrPolicyParamsV1
from app.modules.ad_control_settings.domain.enums import (
    AdControlFeatureId,
    AdControlFeatureMode,
    AdControlScope,
    ControlPathKind,
    EffectiveSourceKind,
    HierarchicalEnrollment,
    ShopFeatureActivation,
)
from app.modules.ad_control_settings.domain.product_adapter import (
    ProductDrrPolicyAdapterBlocked,
    ProductDrrPolicyAdapterSuccess,
)
from app.modules.ad_control_settings.domain.provenance import ProvenanceEntry
from app.modules.ad_control_settings.domain.reason_codes import AdControlReasonCode
from app.modules.ad_control_settings.domain.registry import (
    assert_scope_supported,
    validate_feature_payload,
)
from app.modules.ad_control_settings.domain.resolver_models import (
    CampaignFeatureSlot,
    ResolvedFeaturePolicy,
    ResolverBlocked,
    ResolverContext,
    ShopFeatureSlot,
)


class AdControlSettingsResolver:
    """Разрешает effective configured policy per feature (без derived DRR/headroom)."""

    @staticmethod
    def assert_hierarchical_path(context: ResolverContext) -> ResolverBlocked | None:
        if context.control_path == ControlPathKind.LEGACY_PASSTHROUGH:
            return ResolverBlocked(
                reason_codes=(AdControlReasonCode.LEGACY_PASSTHROUGH_ACTIVE,),
                blockers=("hierarchical_resolver_not_applicable",),
            )
        if context.enrollment == HierarchicalEnrollment.NOT_ENROLLED:
            return ResolverBlocked(
                reason_codes=(AdControlReasonCode.NOT_ENROLLED_FAIL_CLOSED,),
                blockers=("hierarchical_automation_not_enrolled",),
            )
        return None

    @staticmethod
    def resolve_feature(
        context: ResolverContext,
        feature_id: AdControlFeatureId,
    ) -> ResolvedFeaturePolicy | ResolverBlocked:
        """Resolve one feature for campaign context."""
        blocked = AdControlSettingsResolver.assert_hierarchical_path(context)
        if blocked is not None:
            return blocked

        scope_err = assert_scope_supported(feature_id, AdControlScope.CAMPAIGN)
        if scope_err is not None:
            return ResolverBlocked(
                reason_codes=(scope_err,),
                blockers=(f"scope_not_supported:{feature_id}",),
            )

        campaign_slot = context.campaign_features.get(
            feature_id,
            CampaignFeatureSlot(mode=AdControlFeatureMode.INHERIT, payload=None),
        )
        shop_slot = context.shop_features.get(
            feature_id,
            ShopFeatureSlot(activation=ShopFeatureActivation.DISABLED, payload=None),
        )

        if campaign_slot.mode == AdControlFeatureMode.DISABLED:
            return ResolvedFeaturePolicy(
                feature_id=feature_id,
                active=False,
                payload=None,
                provenance=ProvenanceEntry(
                    feature_id=feature_id,
                    source_kind=EffectiveSourceKind.CAMPAIGN_DISABLED,
                    source_scope=AdControlScope.CAMPAIGN,
                    schema_version=1,
                ),
                reason_codes=(AdControlReasonCode.FEATURE_DISABLED_AT_CAMPAIGN,),
            )

        if campaign_slot.mode == AdControlFeatureMode.OVERRIDE:
            if campaign_slot.payload is None:
                return ResolverBlocked(
                    reason_codes=(AdControlReasonCode.INVALID_CONFIGURATION,),
                    blockers=(f"campaign_override_missing_payload:{feature_id}",),
                )
            validate_feature_payload(feature_id, campaign_slot.payload)
            return ResolvedFeaturePolicy(
                feature_id=feature_id,
                active=True,
                payload=campaign_slot.payload,
                provenance=ProvenanceEntry(
                    feature_id=feature_id,
                    source_kind=EffectiveSourceKind.CAMPAIGN_OVERRIDE,
                    source_scope=AdControlScope.CAMPAIGN,
                    schema_version=1,
                ),
                reason_codes=(AdControlReasonCode.OK,),
            )

        # INHERIT — live fall-through CAMPAIGN > PRODUCT > SHOP > SYSTEM
        product_policy = AdControlSettingsResolver._resolve_product_tier(
            context,
            feature_id,
        )
        if product_policy is not None:
            return product_policy

        if shop_slot.activation == ShopFeatureActivation.DISABLED:
            return ResolvedFeaturePolicy(
                feature_id=feature_id,
                active=False,
                payload=None,
                provenance=ProvenanceEntry(
                    feature_id=feature_id,
                    source_kind=EffectiveSourceKind.SHOP_DISABLED,
                    source_scope=AdControlScope.SHOP,
                    schema_version=1,
                ),
                reason_codes=(AdControlReasonCode.FEATURE_DISABLED_AT_SHOP,),
            )

        if shop_slot.payload is None:
            return ResolvedFeaturePolicy(
                feature_id=feature_id,
                active=False,
                payload=None,
                provenance=ProvenanceEntry(
                    feature_id=feature_id,
                    source_kind=EffectiveSourceKind.SYSTEM_LEGACY_DEFAULT,
                    source_scope=AdControlScope.SYSTEM_LEGACY,
                    schema_version=1,
                ),
                reason_codes=(AdControlReasonCode.OK,),
            )

        validate_feature_payload(feature_id, shop_slot.payload)
        return ResolvedFeaturePolicy(
            feature_id=feature_id,
            active=True,
            payload=shop_slot.payload,
            provenance=ProvenanceEntry(
                feature_id=feature_id,
                source_kind=EffectiveSourceKind.SHOP_POLICY,
                source_scope=AdControlScope.SHOP,
                schema_version=1,
            ),
            reason_codes=(AdControlReasonCode.OK,),
        )

    @staticmethod
    def _resolve_product_tier(
        context: ResolverContext,
        feature_id: AdControlFeatureId,
    ) -> ResolvedFeaturePolicy | None:
        if feature_id != AdControlFeatureId.DRR_POLICY:
            return None
        scope_err = assert_scope_supported(feature_id, AdControlScope.PRODUCT)
        if scope_err is not None:
            return None
        if context.product_drr is None:
            return None
        if isinstance(context.product_drr, ProductDrrPolicyAdapterBlocked):
            # Fall through to SHOP tier (CAMPAIGN > PRODUCT > SHOP); adapter block
            # is not the same as product feature DISABLED.
            return None
        assert isinstance(context.product_drr, ProductDrrPolicyAdapterSuccess)
        validate_feature_payload(feature_id, context.product_drr.params)
        return ResolvedFeaturePolicy(
            feature_id=feature_id,
            active=True,
            payload=context.product_drr.params,
            provenance=context.product_drr.provenance,
            reason_codes=(AdControlReasonCode.OK,),
        )

    @staticmethod
    def resolve_configured_target_drr(
        context: ResolverContext,
    ) -> DrrPolicyParamsV1 | ResolverBlocked:
        """Convenience: configured DRR policy для кампании."""
        resolved = AdControlSettingsResolver.resolve_feature(
            context,
            AdControlFeatureId.DRR_POLICY,
        )
        if isinstance(resolved, ResolverBlocked):
            return resolved
        if not resolved.active or resolved.payload is None:
            return ResolverBlocked(
                reason_codes=resolved.reason_codes,
                blockers=("drr_policy_inactive",),
            )
        if not isinstance(resolved.payload, DrrPolicyParamsV1):
            return ResolverBlocked(
                reason_codes=(AdControlReasonCode.INVALID_CONFIGURATION,),
                blockers=("drr_policy_wrong_payload_type",),
            )
        return resolved.payload
