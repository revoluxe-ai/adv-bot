"""Доменный контракт CampaignSettingsSnapshotV1 для AI Package export."""

from __future__ import annotations

from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, Field

from app.modules.ai_package_v1.domain.settings_enums import (
    AuthorityClass,
    CampaignLegRole,
    SettingsCollectionOutcome,
    SettingsCoverageLevel,
    SettingsFreshnessLevel,
    SettingsReasonCode,
)

SCHEMA_VERSION = "CampaignSettingsSnapshotV1"
_FROZEN = ConfigDict(frozen=True)


class FieldProvenanceV1(BaseModel):
    """Provenance одного экспортированного поля."""

    model_config = _FROZEN

    field_path: str
    authority_class: AuthorityClass
    source_ref: str
    observed_at: datetime | None = None
    reason_codes: tuple[SettingsReasonCode, ...] = Field(default_factory=tuple)


class CompletenessBlockV1(BaseModel):
    """Четыре независимых измерения полноты (coverage-provenance)."""

    model_config = _FROZEN

    collection_outcome: SettingsCollectionOutcome
    coverage: SettingsCoverageLevel
    reason_codes: tuple[SettingsReasonCode, ...] = Field(default_factory=tuple)
    freshness: SettingsFreshnessLevel


class CampaignLegSettingsV1(BaseModel):
    """Настройки одной ноги (Auto или Search) в detailed snapshot."""

    model_config = _FROZEN

    wb_adv_id: int
    leg_role: CampaignLegRole
    wb_bid_type: str | None = None
    wb_placement_search: bool | None = None
    wb_placement_recommendations: bool | None = None
    wb_status: None = None
    wb_payment_type: None = None
    field_provenance: tuple[FieldProvenanceV1, ...] = Field(default_factory=tuple)


class LocalPolicyBlockV1(BaseModel):
    """Локальная политика AdvSetting (не WB authoritative)."""

    model_config = _FROZEN

    bot_active: bool | None = None
    bidder_active: bool | None = None
    parsing_active: bool | None = None
    budget: dict[str, Any] = Field(default_factory=dict)
    sales: dict[str, Any] = Field(default_factory=dict)
    bid_control: dict[str, Any] = Field(default_factory=dict)
    keyword_policy: dict[str, Any] = Field(default_factory=dict)
    field_provenance: tuple[FieldProvenanceV1, ...] = Field(default_factory=tuple)


class InventoryRelationBlockV1(BaseModel):
    """Идентификаторы и связи inventory grain."""

    model_config = _FROZEN

    adv_setting_id: int
    shop_id: str
    adv_id: int | None = None
    search_adv_id: int | None = None
    name: str
    active_status: str
    nmids: tuple[int, ...] = Field(default_factory=tuple)
    a1_resource_id: str | None = None
    field_provenance: tuple[FieldProvenanceV1, ...] = Field(default_factory=tuple)


class CampaignSettingsSnapshotRecordV1(BaseModel):
    """Одна строка detailed settings export по grain (shop_id, adv_setting_id)."""

    model_config = _FROZEN

    inventory: InventoryRelationBlockV1
    auto_leg: CampaignLegSettingsV1 | None = None
    search_leg: CampaignLegSettingsV1 | None = None
    local_policy: LocalPolicyBlockV1
    record_completeness: CompletenessBlockV1


class CampaignSettingsSnapshotV1(BaseModel):
    """Корневой domain payload для manifest card campaign_settings_snapshot."""

    model_config = _FROZEN

    schema_version: str = SCHEMA_VERSION
    shop_id: str
    snapshot_assembled_at: datetime
    records: tuple[CampaignSettingsSnapshotRecordV1, ...] = Field(default_factory=tuple)
    completeness: CompletenessBlockV1

    def has_unknown_authoritative_field(self) -> bool:
        """True если есть UNKNOWN/WB gap, блокирующий mutation eligibility."""
        for record in self.records:
            for leg in (record.auto_leg, record.search_leg):
                if leg is None:
                    continue
                for prov in leg.field_provenance:
                    if prov.authority_class in (
                        AuthorityClass.UNKNOWN,
                        AuthorityClass.UNSUPPORTED,
                    ):
                        return True
        return False

    def is_mutation_eligible(self) -> bool:
        """Fail-closed: UNKNOWN authoritative поля запрещают mutation heuristics."""
        if self.completeness.collection_outcome in (
            SettingsCollectionOutcome.UNKNOWN,
            SettingsCollectionOutcome.NO_DATA,
        ):
            return False
        if self.has_unknown_authoritative_field():
            return False
        return True
