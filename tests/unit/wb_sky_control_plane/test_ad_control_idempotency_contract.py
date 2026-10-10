"""Ad control idempotency binding (formal contract, no durable store)."""

from __future__ import annotations

import pytest

from app.modules.wb_sky_control_plane.ad_control.idempotency_contract import (
    bind_ad_control_idempotency,
    evaluate_ad_control_idempotency_replay,
)
from app.modules.wb_sky_control_plane.apply.enums import IdempotencyDecisionKind
from app.modules.wb_sky_control_plane.apply.idempotency import IdempotencyRecordView
from app.modules.ad_control_settings.domain.enums import AdControlFeatureId
from app.modules.wb_sky_control_plane.models.ad_control_changeset import (
    AdControlChangeSetV1,
    AdControlLogicalScopeV1,
    AdControlRevisionPreconditionV1,
    AdvertCampaignRefV1,
    CampaignFeatureTargetV1,
    ClearCampaignAdControlFeatureOperation,
)

pytestmark = pytest.mark.unit


def test_same_digest_same_fingerprint_replay_fresh() -> None:
    changeset = AdControlChangeSetV1(
        changeset_id="cs-idem-1",
        scope=AdControlLogicalScopeV1(shop_id="shop-1"),
        operations=[
            ClearCampaignAdControlFeatureOperation(
                operation_id="op-1",
                preconditions=AdControlRevisionPreconditionV1(expected_revision=None),
                resource=AdvertCampaignRefV1(shop_id="shop-1", advert_id=1),
                payload=CampaignFeatureTargetV1(feature_id=AdControlFeatureId.DRR_POLICY),
            )
        ],
    )
    binding = bind_ad_control_idempotency(
        changeset,
        apply_contract_version="v1",
        preview_digest="pd1_test",
    )
    decision = evaluate_ad_control_idempotency_replay(
        binding=binding,
        record=None,
        caller_authorized=True,
    )
    assert decision.kind == IdempotencyDecisionKind.FRESH


def test_same_key_different_digest_conflicts() -> None:
    cs_a = AdControlChangeSetV1(
        changeset_id="cs-a",
        scope=AdControlLogicalScopeV1(shop_id="shop-1"),
        operations=[
            ClearCampaignAdControlFeatureOperation(
                operation_id="op-1",
                preconditions=AdControlRevisionPreconditionV1(expected_revision=None),
                resource=AdvertCampaignRefV1(shop_id="shop-1", advert_id=1),
                payload=CampaignFeatureTargetV1(feature_id=AdControlFeatureId.DRR_POLICY),
            )
        ],
    )
    cs_b = AdControlChangeSetV1(
        changeset_id="cs-b",
        scope=AdControlLogicalScopeV1(shop_id="shop-1"),
        operations=[
            ClearCampaignAdControlFeatureOperation(
                operation_id="op-1",
                preconditions=AdControlRevisionPreconditionV1(expected_revision=None),
                resource=AdvertCampaignRefV1(shop_id="shop-1", advert_id=2),
                payload=CampaignFeatureTargetV1(feature_id=AdControlFeatureId.DRR_POLICY),
            )
        ],
    )
    bind_a = bind_ad_control_idempotency(cs_a, apply_contract_version="v1", preview_digest="pd1")
    bind_b = bind_ad_control_idempotency(cs_b, apply_contract_version="v1", preview_digest="pd1")
    assert bind_a.fingerprint != bind_b.fingerprint
    record = IdempotencyRecordView(
        fingerprint=bind_a.fingerprint,
        terminal_status=None,
        in_flight=False,
        evidence=None,
    )
    decision = evaluate_ad_control_idempotency_replay(
        binding=bind_b,
        record=record,
        caller_authorized=True,
    )
    assert decision.kind == IdempotencyDecisionKind.CONFLICT
