"""Перечисления контракта attribution facts (стабильные строковые токены)."""

from enum import StrEnum


class AttributionClass(StrEnum):
    """Класс атрибуции заказанного nm в рамках physical adv_id и даты."""

    DIRECT = "DIRECT"
    LINKED = "LINKED"
    UNKNOWN = "UNKNOWN"
    UNATTRIBUTED = "UNATTRIBUTED"
    UNSUPPORTED = "UNSUPPORTED"


class AttributionCoverageStatus(StrEnum):
    """Покрытие attribution facts для scope/window (независимо от package cutoff)."""

    COMPLETE = "COMPLETE"
    PARTIAL = "PARTIAL"
    NO_DATA = "NO_DATA"
    UNSUPPORTED = "UNSUPPORTED"
    UNKNOWN = "UNKNOWN"


class AttributionReasonCode(StrEnum):
    """Машинно-читаемые причины fail-closed и неполноты."""

    ATTRIBUTION_SOURCE_MISSING = "ATTRIBUTION_SOURCE_MISSING"
    ATTRIBUTION_SOURCE_PARTIAL = "ATTRIBUTION_SOURCE_PARTIAL"
    ATTRIBUTION_RELATION_UNKNOWN = "ATTRIBUTION_RELATION_UNKNOWN"
    ATTRIBUTION_CAMPAIGN_LEG_AMBIGUOUS = "ATTRIBUTION_CAMPAIGN_LEG_AMBIGUOUS"
    ATTRIBUTION_ORDER_IDENTITY_AMBIGUOUS = "ATTRIBUTION_ORDER_IDENTITY_AMBIGUOUS"
    ATTRIBUTION_VERSION_AMBIGUOUS = "ATTRIBUTION_VERSION_AMBIGUOUS"
    ATTRIBUTION_SCOPE_MISMATCH = "ATTRIBUTION_SCOPE_MISMATCH"
    ATTRIBUTION_UNSUPPORTED = "ATTRIBUTION_UNSUPPORTED"
    RECONCILIATION_FAILED = "RECONCILIATION_FAILED"
    DENOMINATOR_ZERO = "DENOMINATOR_ZERO"
    BLOCKED_BY_ATTRIBUTION_FACTS = "BLOCKED_BY_ATTRIBUTION_FACTS"


class SourceFamily(StrEnum):
    """Идентичность семейства источника для fact key."""

    WB_PROMOTION_FULLSTATS_NM_DAY = "WB_PROMOTION_FULLSTATS_NM_DAY"
