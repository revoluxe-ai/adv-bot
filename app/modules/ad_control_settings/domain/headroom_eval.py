"""
Pure headroom eligibility и control-action gate (stale/unknown => no action).
"""

from __future__ import annotations

from decimal import Decimal

from app.modules.ad_control_settings.domain.campaign_ref import CampaignRef
from app.modules.ad_control_settings.domain.drr_state import (
    ActualDrrObservation,
    ShopEffectiveControlDrr,
)
from app.modules.ad_control_settings.domain.enums import (
    ControlPathKind,
    DataSufficiency,
    HierarchicalEnrollment,
)
from app.modules.ad_control_settings.domain.headroom import (
    CampaignHeadroomEligibility,
    ShopHeadroomState,
)
from app.modules.ad_control_settings.domain.reason_codes import AdControlReasonCode


def derive_shop_effective_control_drr(
    configured_target_percent: Decimal,
    dynamic_enabled: bool,
    actual: ActualDrrObservation,
) -> ShopEffectiveControlDrr:
    """
    Derived shop effective control DRR (recomputable).

    Foundation slice: без production dynamic formula; при dynamic_enabled и
    sufficient data возвращает configured как baseline placeholder.
    """
    if not dynamic_enabled:
        return ShopEffectiveControlDrr(
            effective_control_drr_percent=None,
            derived_from_configured=False,
        )
    if actual.data_sufficiency != DataSufficiency.SUFFICIENT:
        return ShopEffectiveControlDrr(
            effective_control_drr_percent=None,
            derived_from_configured=False,
        )
    return ShopEffectiveControlDrr(
        effective_control_drr_percent=configured_target_percent,
        derived_from_configured=True,
    )


def evaluate_shop_headroom_state(
    configured_target_percent: Decimal,
    actual: ActualDrrObservation,
    allowed_spend_rub: Decimal | None,
    spend_rub: Decimal | None,
) -> ShopHeadroomState:
    """Signed headroom rub (optional) из configured vs actual DRR."""
    actual_percent = actual.actual_drr_percent
    headroom_rub: Decimal | None = None
    if (
        actual_percent is not None
        and allowed_spend_rub is not None
        and spend_rub is not None
        and actual.data_sufficiency == DataSufficiency.SUFFICIENT
    ):
        headroom_rub = allowed_spend_rub - spend_rub
    pressure: Decimal | None = None
    if (
        actual_percent is not None
        and actual.data_sufficiency == DataSufficiency.SUFFICIENT
    ):
        pressure = configured_target_percent - actual_percent
    return ShopHeadroomState(
        configured_target_drr_percent=configured_target_percent,
        actual_drr_percent=actual_percent,
        headroom_rub=headroom_rub,
        control_pressure=pressure,
    )


def control_action_allowed(actual: ActualDrrObservation) -> tuple[bool, AdControlReasonCode]:
    """Stale/insufficient/unknown => NO NEW CONTROL ACTION."""
    if actual.data_sufficiency == DataSufficiency.STALE:
        return False, AdControlReasonCode.ACTUAL_DRR_STALE
    if actual.data_sufficiency == DataSufficiency.INSUFFICIENT:
        return False, AdControlReasonCode.ACTUAL_DRR_INSUFFICIENT
    if actual.data_sufficiency == DataSufficiency.UNSUPPORTED:
        return False, AdControlReasonCode.ACTUAL_DRR_UNSUPPORTED
    if actual.data_sufficiency == DataSufficiency.UNKNOWN:
        return False, AdControlReasonCode.MEASUREMENT_UNKNOWN
    return True, AdControlReasonCode.OK


def campaign_headroom_eligibility(
    campaign: CampaignRef,
    actual: ActualDrrObservation,
    *,
    enrollment: HierarchicalEnrollment,
    control_path: ControlPathKind,
    hierarchical_resolver_available: bool,
) -> CampaignHeadroomEligibility:
    """Eligibility contract без production ranking."""
    reasons: list[AdControlReasonCode] = []
    blockers: list[str] = []
    if control_path == ControlPathKind.LEGACY_PASSTHROUGH:
        blockers.append("legacy_passthrough")
        reasons.append(AdControlReasonCode.LEGACY_PASSTHROUGH_ACTIVE)
        return CampaignHeadroomEligibility(
            campaign=campaign,
            eligible=False,
            reason_codes=tuple(reasons),
            blockers=tuple(blockers),
        )
    if enrollment == HierarchicalEnrollment.NOT_ENROLLED:
        blockers.append("not_enrolled")
        reasons.append(AdControlReasonCode.NOT_ENROLLED_FAIL_CLOSED)
        return CampaignHeadroomEligibility(
            campaign=campaign,
            eligible=False,
            reason_codes=tuple(reasons),
            blockers=tuple(blockers),
        )
    if not hierarchical_resolver_available:
        blockers.append("hierarchical_resolver_blocked")
        reasons.append(AdControlReasonCode.INVALID_CONFIGURATION)
        return CampaignHeadroomEligibility(
            campaign=campaign,
            eligible=False,
            reason_codes=tuple(reasons),
            blockers=tuple(blockers),
        )
    allowed, reason = control_action_allowed(actual)
    if not allowed:
        reasons.append(reason)
        reasons.append(AdControlReasonCode.NO_CONTROL_ACTION_STALE_OR_UNKNOWN)
        blockers.append("no_control_action")
        return CampaignHeadroomEligibility(
            campaign=campaign,
            eligible=False,
            reason_codes=tuple(reasons),
            blockers=tuple(blockers),
        )
    return CampaignHeadroomEligibility(
        campaign=campaign,
        eligible=True,
        reason_codes=(AdControlReasonCode.OK,),
        blockers=(),
    )
