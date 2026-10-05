"""Перечисления доменного контракта CampaignSettingsSnapshotV1."""

from __future__ import annotations

from enum import StrEnum


class AuthorityClass(StrEnum):
    """Класс источника значения поля detailed settings export."""

    WB_AUTHORITATIVE = "WB_AUTHORITATIVE"
    LOCAL_POLICY = "LOCAL_POLICY"
    INVENTORY_RELATION = "INVENTORY_RELATION"
    UNKNOWN = "UNKNOWN"
    UNSUPPORTED = "UNSUPPORTED"


class CampaignLegRole(StrEnum):
    """Роль WB leg в паре Auto/Search."""

    AUTO = "AUTO"
    SEARCH = "SEARCH"


class SettingsCollectionOutcome(StrEnum):
    """Результат попытки чтения detailed settings на export path."""

    SUCCESS = "SUCCESS"
    PARTIAL = "PARTIAL"
    UNKNOWN = "UNKNOWN"
    NO_DATA = "NO_DATA"


class SettingsCoverageLevel(StrEnum):
    """Покрытие settings snapshot в рамках shop scope."""

    FULL = "FULL"
    PARTIAL = "PARTIAL"
    UNKNOWN = "UNKNOWN"


class SettingsFreshnessLevel(StrEnum):
    """Актуальность PG sync для settings snapshot."""

    FRESH = "FRESH"
    STALE = "STALE"
    UNKNOWN = "UNKNOWN"


class SettingsReasonCode(StrEnum):
    """Причины неполноты detailed campaign settings snapshot."""

    NO_DATA = "NO_DATA"
    UNKNOWN = "UNKNOWN"
    PARTIAL_PG_WB_SYNC = "PARTIAL_PG_WB_SYNC"
    UNSUPPORTED_FIELD = "UNSUPPORTED_FIELD"
    A1_REGISTRY_GAP = "A1_REGISTRY_GAP"
