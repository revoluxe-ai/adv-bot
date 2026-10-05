"""Unit tests: CampaignSettingsSnapshotV1 domain contract."""

from __future__ import annotations

from datetime import UTC, datetime

import pytest

from app.modules.ai_package_v1.domain.campaign_settings_snapshot_v1 import (
    CampaignLegSettingsV1,
    CampaignSettingsSnapshotRecordV1,
    CampaignSettingsSnapshotV1,
    CompletenessBlockV1,
    FieldProvenanceV1,
    InventoryRelationBlockV1,
    LocalPolicyBlockV1,
    SCHEMA_VERSION,
)
from app.modules.ai_package_v1.domain.settings_enums import (
    AuthorityClass,
    CampaignLegRole,
    SettingsCollectionOutcome,
    SettingsCoverageLevel,
    SettingsFreshnessLevel,
    SettingsReasonCode,
)


@pytest.mark.unit
def test_schema_version_constant() -> None:
    assert SCHEMA_VERSION == "CampaignSettingsSnapshotV1"


@pytest.mark.unit
def test_null_serialization_in_model_dump() -> None:
    leg = CampaignLegSettingsV1(
        wb_adv_id=1,
        leg_role=CampaignLegRole.AUTO,
        wb_bid_type=None,
    )
    dumped = leg.model_dump(mode="json")
    assert dumped["wb_bid_type"] is None


@pytest.mark.unit
def test_unknown_wb_field_fail_closed() -> None:
    leg = CampaignLegSettingsV1(
        wb_adv_id=2,
        leg_role=CampaignLegRole.SEARCH,
        field_provenance=(
            FieldProvenanceV1(
                field_path="search_leg.wb_bid_type",
                authority_class=AuthorityClass.UNKNOWN,
                source_ref="pg:missing",
                reason_codes=(SettingsReasonCode.UNKNOWN,),
            ),
        ),
    )
    record = CampaignSettingsSnapshotRecordV1(
        inventory=InventoryRelationBlockV1(
            adv_setting_id=1,
            shop_id="s1",
            name="n",
            active_status="active",
        ),
        search_leg=leg,
        local_policy=LocalPolicyBlockV1(),
        record_completeness=CompletenessBlockV1(
            collection_outcome=SettingsCollectionOutcome.SUCCESS,
            coverage=SettingsCoverageLevel.PARTIAL,
            freshness=SettingsFreshnessLevel.UNKNOWN,
        ),
    )
    snapshot = CampaignSettingsSnapshotV1(
        shop_id="s1",
        snapshot_assembled_at=datetime(2026, 10, 3, tzinfo=UTC),
        records=(record,),
        completeness=CompletenessBlockV1(
            collection_outcome=SettingsCollectionOutcome.SUCCESS,
            coverage=SettingsCoverageLevel.PARTIAL,
            freshness=SettingsFreshnessLevel.UNKNOWN,
        ),
    )
    assert snapshot.has_unknown_authoritative_field() is True
    assert snapshot.is_mutation_eligible() is False
