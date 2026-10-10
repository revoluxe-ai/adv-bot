"""Unit tests payload_codec round-trip."""

from __future__ import annotations

from decimal import Decimal

import pytest

pytestmark = pytest.mark.unit

from app.modules.ad_control_settings.domain.configured import (
    CpoIncreaseOnHeadroomParamsV1,
    DrrPolicyParamsV1,
)
from app.modules.ad_control_settings.domain.enums import AdControlFeatureId
from app.modules.ad_control_settings.domain.min_data_sufficiency import (
    MinObservedDataSufficiencyRequirement,
)
from app.modules.ad_control_settings.persistence.payload_codec import (
    PayloadCodecError,
    decode_payload_json,
    encode_payload_json,
)
from app.modules.product_control.domain.drr_profile import drr_profile_from_percent


def test_drr_policy_round_trip() -> None:
    payload = DrrPolicyParamsV1(
        profile=drr_profile_from_percent(Decimal("15"), Decimal("20")),
    )
    raw = encode_payload_json(AdControlFeatureId.DRR_POLICY, payload)
    restored = decode_payload_json(AdControlFeatureId.DRR_POLICY, raw)
    assert restored == payload


def test_cpo_increase_round_trip() -> None:
    payload = CpoIncreaseOnHeadroomParamsV1(
        minimum_headroom_rub=Decimal("100"),
        maximum_increase_per_iteration_rub=Decimal("5"),
        cooldown_ticks=2,
        min_data_sufficiency=MinObservedDataSufficiencyRequirement.SUFFICIENT,
    )
    raw = encode_payload_json(AdControlFeatureId.CPO_INCREASE_ON_HEADROOM, payload)
    restored = decode_payload_json(AdControlFeatureId.CPO_INCREASE_ON_HEADROOM, raw)
    assert restored == payload


def test_decode_rejects_unknown_kind() -> None:
    with pytest.raises(PayloadCodecError):
        decode_payload_json(
            AdControlFeatureId.DRR_POLICY,
            {"kind": "Unknown", "schema_version": 1},
        )
