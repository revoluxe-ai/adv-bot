"""Перечисления keyword performance export (стабильные строковые токены)."""

from enum import StrEnum


class KeywordLegRole(StrEnum):
    """Роль physical adv_id относительно logical resource."""

    AUTO = "AUTO"
    SEARCH = "SEARCH"
    REBOUND_AUTO = "REBOUND_AUTO"
    REBOUND_SEARCH = "REBOUND_SEARCH"
    AMBIGUOUS = "AMBIGUOUS"


class CampaignSlotRole(StrEnum):
    """Active vs historical campaign slot для current state."""

    ACTIVE = "ACTIVE"
    REBOUND_HISTORICAL = "REBOUND_HISTORICAL"
    AMBIGUOUS = "AMBIGUOUS"


class RawQueryStatus(StrEnum):
    """Provenance raw query text."""

    PROVEN = "PROVEN"
    RAW_QUERY_UNAVAILABLE = "RAW_QUERY_UNAVAILABLE"
    AMBIGUOUS = "AMBIGUOUS"


class QuerySpendStatus(StrEnum):
    """Conservative spend semantics per D-003."""

    FACTUAL = "FACTUAL"
    DERIVED_VALID = "DERIVED_VALID"
    ESTIMATE_ONLY = "ESTIMATE_ONLY"
    UNAVAILABLE = "UNAVAILABLE"


class SnapshotStatus(StrEnum):
    """Row-coherent daily snapshot outcome."""

    OK = "OK"
    AMBIGUOUS = "AMBIGUOUS"


class PositionType(StrEnum):
    """Доказанный тип position observation."""

    CLUSTER_AVG_POS = "CLUSTER_AVG_POS"
    WB_KEYWORD_POSITION_API = "WB_KEYWORD_POSITION_API"


class NormQueryProvenance(StrEnum):
    """Provenance norm_query на API-only position stream."""

    PROVEN_EQUAL = "PROVEN_EQUAL"
    NORMALIZATION_UNPROVEN = "NORMALIZATION_UNPROVEN"


class BidEvidenceStatus(StrEnum):
    """Статус current_bid_evidence — cap ≠ applied bid."""

    UNAVAILABLE = "UNAVAILABLE"
    PROVEN = "PROVEN"


class DecisionEventClass(StrEnum):
    """Source-derived класс bid_decision_log (нет native CH event_class column)."""

    DECISION = "DECISION"


class DecisionSourceKind(StrEnum):
    """Provenance bid_decision_log pipeline."""

    RETROSPECTIVE_COMPUTED_CONTEXT = "RETROSPECTIVE_COMPUTED_CONTEXT"


class FinalBidSemantics(StrEnum):
    """Семантика final_bid из fill_bid_decision producer."""

    ANALYTICS_COMPUTED_NOT_VERIFIED_APPLIED = "ANALYTICS_COMPUTED_NOT_VERIFIED_APPLIED"


class WindowSpendStatus(StrEnum):
    """Spend availability across window observed days."""

    FACTUAL = "FACTUAL"
    PARTIAL_UNAVAILABLE = "PARTIAL_UNAVAILABLE"
    UNAVAILABLE = "UNAVAILABLE"


class ComparatorKind(StrEnum):
    """Тип сравнения для window/change rows."""

    NONE = "NONE"
    PREVIOUS_PERIOD = "PREVIOUS_PERIOD"
    PREVIOUS_CALENDAR = "PREVIOUS_CALENDAR"


class FreshnessStatus(StrEnum):
    """Observation freshness vs package_cutoff_instant."""

    FRESH = "FRESH"
    STALE = "STALE"
    UNKNOWN = "UNKNOWN"


class KeywordReasonCode(StrEnum):
    """Reason codes для keyword coverage."""

    NO_DATA = "NO_DATA"
    SNAPSHOT_CONFLICT = "SNAPSHOT_CONFLICT"
    AMBIGUOUS_LEG = "AMBIGUOUS_LEG"
    AMBIGUOUS_OWNERSHIP = "AMBIGUOUS_OWNERSHIP"
    FOREIGN_SHOP_ADV_ID = "FOREIGN_SHOP_ADV_ID"
    AMBIGUOUS_NMID = "AMBIGUOUS_NMID"
    UNASSIGNED_PROVENANCE = "UNASSIGNED_PROVENANCE"
    REBOUND_IDS_UNAVAILABLE = "REBOUND_IDS_UNAVAILABLE"
    RAW_QUERY_UNAVAILABLE = "RAW_QUERY_UNAVAILABLE"
    UNKNOWN_VERSION_TIME_SEMANTICS = "UNKNOWN_VERSION_TIME_SEMANTICS"
    UNSUPPORTED = "UNSUPPORTED"
    SOURCE_ERROR = "SOURCE_ERROR"
    PARTIAL_HISTORY = "PARTIAL_HISTORY"


SCHEMA_VERSION_KEYWORD = "1.0.0"
