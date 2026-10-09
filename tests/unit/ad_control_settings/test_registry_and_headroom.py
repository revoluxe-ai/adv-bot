"""Registry validation, headroom gates, diagnostics contract."""

from __future__ import annotations

from decimal import Decimal

import pytest

from app.modules.ad_control_settings.domain.campaign_ref import CampaignRef
from app.modules.ad_control_settings.domain.configured import (
    CpoDecreaseOnOverspendParamsV1,
    CpoIncreaseOnHeadroomParamsV1,
    DrrPolicyParamsV1,
)
from app.modules.ad_control_settings.domain.diagnostics_builder import (
    AdControlDiagnosticsBuilder,
)
from app.modules.ad_control_settings.domain.drr_state import ActualDrrObservation
from app.modules.ad_control_settings.domain.enums import (
    AdControlFeatureId,
    AdControlFeatureMode,
    AdControlScope,
    ControlPathKind,
    DataSufficiency,
    HierarchicalEnrollment,
    ShopFeatureActivation,
)
from app.modules.ad_control_settings.domain.headroom_eval import control_action_allowed
from app.modules.ad_control_settings.domain.min_data_sufficiency import (
    MinObservedDataSufficiencyRequirement,
)
from app.modules.ad_control_settings.domain.reason_codes import AdControlReasonCode
from app.modules.ad_control_settings.domain.registry import (
    FeatureValidationError,
    assert_scope_supported,
    configuration_identity,
    validate_feature_payload,
)
from app.modules.ad_control_settings.domain.resolver_models import (
    CampaignFeatureSlot,
    ResolverContext,
    ShopFeatureSlot,
)
from app.modules.product_control.domain.drr_profile import drr_profile_from_percent


@pytest.mark.unit
def test_cpo_increase_and_decrease_are_independent_payload_types() -> None:
    inc = CpoIncreaseOnHeadroomParamsV1(
        minimum_headroom_rub=Decimal(100),
        maximum_increase_per_iteration_rub=Decimal(5),
        cooldown_ticks=2,
        min_data_sufficiency=MinObservedDataSufficiencyRequirement.SUFFICIENT,
    )
    dec = CpoDecreaseOnOverspendParamsV1(
        maximum_decrease_per_iteration_rub=Decimal(3),
        cooldown_ticks=1,
        min_data_sufficiency=MinObservedDataSufficiencyRequirement.SUFFICIENT,
    )
    validate_feature_payload(AdControlFeatureId.CPO_INCREASE_ON_HEADROOM, inc)
    validate_feature_payload(AdControlFeatureId.CPO_DECREASE_ON_OVERSPEND, dec)
    with pytest.raises(FeatureValidationError):
        validate_feature_payload(AdControlFeatureId.CPO_INCREASE_ON_HEADROOM, dec)


@pytest.mark.unit
def test_cpo_min_data_sufficiency_rejects_freeform_string() -> None:
    bad = CpoIncreaseOnHeadroomParamsV1(
        minimum_headroom_rub=Decimal(1),
        maximum_increase_per_iteration_rub=Decimal(1),
        cooldown_ticks=0,
        min_data_sufficiency="SUFFICIENT",  # type: ignore[arg-type]
    )
    with pytest.raises(FeatureValidationError):
        validate_feature_payload(AdControlFeatureId.CPO_INCREASE_ON_HEADROOM, bad)


@pytest.mark.unit
def test_unsupported_scope_fail_closed() -> None:
    reason = assert_scope_supported(
        AdControlFeatureId.DYNAMIC_DRR_CONTROL,
        AdControlScope.PRODUCT,
    )
    assert reason == AdControlReasonCode.UNSUPPORTED_SCOPE_FOR_FEATURE


@pytest.mark.unit
def test_configuration_identity_tuple() -> None:
    assert configuration_identity(
        AdControlScope.SHOP,
        AdControlFeatureId.DRR_POLICY,
        1,
    ) == (AdControlScope.SHOP, AdControlFeatureId.DRR_POLICY, 1)


@pytest.mark.unit
def test_stale_actual_drr_blocks_control_action() -> None:
    obs = ActualDrrObservation(
        actual_drr_percent=Decimal(10),
        measurement_window_id="7d",
        data_sufficiency=DataSufficiency.STALE,
        attribution_lag_days=2,
    )
    allowed, reason = control_action_allowed(obs)
    assert allowed is False
    assert reason == AdControlReasonCode.ACTUAL_DRR_STALE


@pytest.mark.unit
def test_diagnostics_no_cpo_proposal_without_price_semantics() -> None:
    drr = DrrPolicyParamsV1(
        profile=drr_profile_from_percent(Decimal(15), Decimal(20)),
    )
    ctx = ResolverContext(
        enrollment=HierarchicalEnrollment.ENROLLED,
        control_path=ControlPathKind.HIERARCHICAL,
        shop_id="s",
        shop_features={
            AdControlFeatureId.DRR_POLICY: ShopFeatureSlot(
                activation=ShopFeatureActivation.ENABLED,
                payload=drr,
            ),
        },
        campaign=CampaignRef(shop_id="s", advert_id=99),
        campaign_features={
            AdControlFeatureId.DRR_POLICY: CampaignFeatureSlot(
                mode=AdControlFeatureMode.INHERIT,
                payload=None,
            ),
        },
    )
    actual = ActualDrrObservation(
        actual_drr_percent=Decimal(10),
        measurement_window_id="7d",
        data_sufficiency=DataSufficiency.SUFFICIENT,
        attribution_lag_days=1,
    )
    report = AdControlDiagnosticsBuilder.build(
        ctx,
        actual,
        current_max_cpo_rub=Decimal(500),
    )
    assert report.proposed_cpo is not None
    assert report.proposed_cpo.proposed_max_cpo_rub is None
    assert (
        AdControlReasonCode.PRICE_SEMANTICS_NOT_ACCEPTED_CPO_ACTUATION_BLOCKED
        in report.proposed_cpo.reason_codes
    )
