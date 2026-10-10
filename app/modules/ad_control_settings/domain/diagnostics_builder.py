"""
Сборка AdControlDiagnosticsReportV1 из pure resolver + headroom (без I/O).
"""

from __future__ import annotations

from decimal import Decimal

from app.modules.ad_control_settings.domain.configured import DrrPolicyParamsV1
from app.modules.ad_control_settings.domain.configured_state import (
    project_configured_campaign_features,
    project_configured_shop_features,
)
from app.modules.ad_control_settings.domain.diagnostics import (
    AdControlDiagnosticsReportV1,
)
from app.modules.ad_control_settings.domain.drr_state import (
    ActualDrrObservation,
    CampaignEffectiveControlDrr,
    ConfiguredTargetDrr,
)
from app.modules.ad_control_settings.domain.enums import (
    AdControlFeatureId,
    AdControlScope,
    EffectiveSourceKind,
)
from app.modules.ad_control_settings.domain.headroom import BoundedCpoProposal
from app.modules.ad_control_settings.domain.headroom_eval import (
    campaign_headroom_eligibility,
    control_action_allowed,
    derive_shop_effective_control_drr,
    evaluate_shop_headroom_state,
)
from app.modules.ad_control_settings.domain.provenance import ProvenanceEntry
from app.modules.ad_control_settings.domain.reason_codes import AdControlReasonCode
from app.modules.ad_control_settings.domain.registry import FEATURE_REGISTRY
from app.modules.ad_control_settings.domain.resolver import AdControlSettingsResolver
from app.modules.ad_control_settings.domain.resolver_models import (
    ResolvedFeaturePolicy,
    ResolverBlocked,
    ResolverContext,
)


class AdControlDiagnosticsBuilder:
    """Строит diagnostic report; не выполняет production writes."""

    @staticmethod
    def build(
        context: ResolverContext,
        actual_drr: ActualDrrObservation | None,
        *,
        current_max_cpo_rub: Decimal | None = None,
        allowed_spend_rub: Decimal | None = None,
        spend_rub: Decimal | None = None,
        dry_run_diff_available: bool = False,
    ) -> AdControlDiagnosticsReportV1:
        reason_codes: list[AdControlReasonCode] = []
        blockers: list[str] = []
        provenance_entries: list[ProvenanceEntry] = []

        drr_resolved = AdControlSettingsResolver.resolve_feature(
            context,
            AdControlFeatureId.DRR_POLICY,
        )
        effective_features: list[ResolvedFeaturePolicy] = []
        configured_target: ConfiguredTargetDrr | None = None

        if isinstance(drr_resolved, ResolverBlocked):
            reason_codes.extend(drr_resolved.reason_codes)
            blockers.extend(drr_resolved.blockers)
        else:
            effective_features.append(drr_resolved)
            provenance_entries.append(drr_resolved.provenance)
            if (
                drr_resolved.active
                and isinstance(drr_resolved.payload, DrrPolicyParamsV1)
            ):
                profile = drr_resolved.payload.profile
                configured_target = ConfiguredTargetDrr(
                    target_drr_percent=profile.target_drr_percent,
                    max_drr_percent=profile.max_drr_percent,
                    provenance=drr_resolved.provenance,
                )

        for feature_id in FEATURE_REGISTRY:
            if feature_id == AdControlFeatureId.DRR_POLICY:
                continue
            resolved = AdControlSettingsResolver.resolve_feature(context, feature_id)
            if isinstance(resolved, ResolverBlocked):
                reason_codes.extend(resolved.reason_codes)
                blockers.extend(resolved.blockers)
                continue
            effective_features.append(resolved)
            provenance_entries.append(resolved.provenance)

        dynamic_enabled = False
        from app.modules.ad_control_settings.domain.configured import (
            DynamicDrrControlParamsV1,
        )

        for eff in effective_features:
            if (
                eff.feature_id == AdControlFeatureId.DYNAMIC_DRR_CONTROL
                and eff.active
                and isinstance(eff.payload, DynamicDrrControlParamsV1)
            ):
                dynamic_enabled = eff.payload.enabled

        shop_eff = None
        shop_headroom = None
        campaign_eff = None
        proposed: BoundedCpoProposal | None = None

        if configured_target is not None and actual_drr is not None:
            shop_eff = derive_shop_effective_control_drr(
                configured_target.target_drr_percent,
                dynamic_enabled,
                actual_drr,
            )
            shop_headroom = evaluate_shop_headroom_state(
                configured_target.target_drr_percent,
                actual_drr,
                allowed_spend_rub,
                spend_rub,
            )
            allowed, gate_reason = control_action_allowed(actual_drr)
            if not allowed:
                reason_codes.append(gate_reason)
                reason_codes.append(
                    AdControlReasonCode.NO_CONTROL_ACTION_STALE_OR_UNKNOWN,
                )
            hierarchical_blocked = AdControlSettingsResolver.assert_hierarchical_path(
                context,
            )
            eligibility = campaign_headroom_eligibility(
                context.campaign,
                actual_drr,
                enrollment=context.enrollment,
                control_path=context.control_path,
                hierarchical_resolver_available=hierarchical_blocked is None,
            )
            reason_codes.extend(eligibility.reason_codes)
            blockers.extend(eligibility.blockers)
            if shop_eff.effective_control_drr_percent is not None:
                inherits_shop = (
                    drr_resolved.provenance.source_kind
                    == EffectiveSourceKind.SHOP_POLICY
                    if not isinstance(drr_resolved, ResolverBlocked)
                    else False
                )
                campaign_eff = CampaignEffectiveControlDrr(
                    effective_control_drr_percent=shop_eff.effective_control_drr_percent,
                    inherits_shop_control=inherits_shop,
                    provenance=ProvenanceEntry(
                        feature_id=AdControlFeatureId.DYNAMIC_DRR_CONTROL,
                        source_kind=EffectiveSourceKind.SHOP_POLICY,
                        source_scope=AdControlScope.SHOP,
                        schema_version=1,
                    ),
                )
            proposed = BoundedCpoProposal(
                campaign=context.campaign,
                current_max_cpo_rub=current_max_cpo_rub,
                proposed_max_cpo_rub=None,
                decision="NO_PROPOSAL_PRICE_SEMANTICS_NOT_ACCEPTED",
                reason_codes=(
                    AdControlReasonCode.PRICE_SEMANTICS_NOT_ACCEPTED_CPO_ACTUATION_BLOCKED,
                ),
            )

        decision = "DIAGNOSTIC_READ_ONLY"
        if blockers:
            decision = "BLOCKED"

        configured_shop = project_configured_shop_features(context)
        configured_campaign = project_configured_campaign_features(context)

        return AdControlDiagnosticsReportV1(
            shop_id=context.shop_id,
            campaign=context.campaign,
            configured_shop_features=configured_shop,
            configured_campaign_overrides=configured_campaign,
            effective_features=tuple(effective_features),
            configured_target_drr=configured_target,
            actual_drr=actual_drr,
            shop_effective_control_drr=shop_eff,
            campaign_effective_control_drr=campaign_eff,
            shop_headroom=shop_headroom,
            current_max_cpo_rub=current_max_cpo_rub,
            proposed_cpo=proposed,
            decision=decision,
            reason_codes=tuple(dict.fromkeys(reason_codes)),
            blockers=tuple(blockers),
            dry_run_diff_available=dry_run_diff_available,
            provenance_index=tuple(provenance_entries),
        )
