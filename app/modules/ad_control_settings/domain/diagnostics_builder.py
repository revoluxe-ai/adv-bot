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

_ORDER_VALUE_SUPPRESS = frozenset(
    {
        AdControlReasonCode.ACTUAL_DRR_STALE,
        AdControlReasonCode.ACTUAL_DRR_INSUFFICIENT,
        AdControlReasonCode.ACTUAL_DRR_UNSUPPORTED,
        AdControlReasonCode.MEASUREMENT_UNKNOWN,
        AdControlReasonCode.NO_CONTROL_ACTION_STALE_OR_UNKNOWN,
        AdControlReasonCode.NOT_ENROLLED_FAIL_CLOSED,
        AdControlReasonCode.FEATURE_DISABLED_AT_CAMPAIGN,
        AdControlReasonCode.FEATURE_DISABLED_AT_SHOP,
        AdControlReasonCode.FEATURE_DISABLED_AT_PRODUCT,
        AdControlReasonCode.LEGACY_PASSTHROUGH_ACTIVE,
    }
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
        v1_order_value: bool = False,
        order_value_target_cpo_rub: Decimal | None = None,
        order_value_reason_codes: tuple[AdControlReasonCode, ...] = (),
        campaign_observed_drr: ActualDrrObservation | None = None,
        shop_headroom_target_percent: Decimal | None = None,
    ) -> AdControlDiagnosticsReportV1:
        """
        Собрать read-only отчёт.

        ``v1_order_value=False`` сохраняет catalog-price блок
        ``PRICE_SEMANTICS_NOT_ACCEPTED_CPO_ACTUATION_BLOCKED``.
        ``v1_order_value=True`` принимает order-value target и не подменяет его
        catalog-ценой. Allocator не вызывается.
        """
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
            for code in drr_resolved.reason_codes:
                if code != AdControlReasonCode.OK:
                    reason_codes.append(code)
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
            headroom_percent = (
                shop_headroom_target_percent
                if shop_headroom_target_percent is not None
                else configured_target.target_drr_percent
            )
            shop_headroom = evaluate_shop_headroom_state(
                headroom_percent,
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
            proposed = _cpo_proposal(
                context=context,
                current_max_cpo_rub=current_max_cpo_rub,
                reason_codes=reason_codes,
                v1_order_value=v1_order_value,
                order_value_target_cpo_rub=order_value_target_cpo_rub,
                order_value_reason_codes=order_value_reason_codes,
            )
            reason_codes.extend(proposed.reason_codes)

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
            campaign_observed_drr=campaign_observed_drr,
            decision=decision,
            reason_codes=tuple(dict.fromkeys(reason_codes)),
            blockers=tuple(blockers),
            dry_run_diff_available=dry_run_diff_available,
            provenance_index=tuple(provenance_entries),
        )


def _cpo_proposal(
    *,
    context: ResolverContext,
    current_max_cpo_rub: Decimal | None,
    reason_codes: list[AdControlReasonCode],
    v1_order_value: bool,
    order_value_target_cpo_rub: Decimal | None,
    order_value_reason_codes: tuple[AdControlReasonCode, ...],
) -> BoundedCpoProposal:
    """Catalog-price блок или V1 order-value target без allocator."""
    if not v1_order_value:
        return BoundedCpoProposal(
            campaign=context.campaign,
            current_max_cpo_rub=current_max_cpo_rub,
            proposed_max_cpo_rub=None,
            decision="NO_PROPOSAL_PRICE_SEMANTICS_NOT_ACCEPTED",
            reason_codes=(
                AdControlReasonCode.PRICE_SEMANTICS_NOT_ACCEPTED_CPO_ACTUATION_BLOCKED,
            ),
        )
    blocked = [
        code for code in reason_codes if code in _ORDER_VALUE_SUPPRESS
    ]
    blocked.extend(order_value_reason_codes)
    if order_value_target_cpo_rub is None or blocked:
        codes = tuple(dict.fromkeys(blocked)) or (
            AdControlReasonCode.CPO_INPUTS_INCOMPLETE,
        )
        return BoundedCpoProposal(
            campaign=context.campaign,
            current_max_cpo_rub=current_max_cpo_rub,
            proposed_max_cpo_rub=None,
            decision="NO_PROPOSAL_ORDER_VALUE_BLOCKED",
            reason_codes=codes,
        )
    return BoundedCpoProposal(
        campaign=context.campaign,
        current_max_cpo_rub=current_max_cpo_rub,
        proposed_max_cpo_rub=order_value_target_cpo_rub,
        decision="DIAGNOSTIC_ORDER_VALUE_TARGET_CPO",
        reason_codes=(AdControlReasonCode.HEADROOM_ALLOCATOR_NOT_ACCEPTED,),
    )
