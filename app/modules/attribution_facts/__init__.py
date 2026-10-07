"""Доменный контракт фактов рекламной атрибуции DIRECT/LINKED (read-side).

Транспорт-независимые модели, классификация, reconciliation и порт
``AttributionFactsReader``. Сбор и ClickHouse — отдельные слайсы B/C.
"""

from app.modules.attribution_facts.domain.enums import (
    AttributionClass,
    AttributionCoverageStatus,
    AttributionReasonCode,
)
from app.modules.attribution_facts.domain.models import (
    AttributionCommerceFact,
    AttributionFactKey,
    AttributionQueryResult,
    AttributionScope,
    DateWindow,
    MembershipSnapshot,
)

__all__ = [
    "AttributionClass",
    "AttributionCommerceFact",
    "AttributionCoverageStatus",
    "AttributionFactKey",
    "AttributionQueryResult",
    "AttributionReasonCode",
    "AttributionScope",
    "DateWindow",
    "MembershipSnapshot",
]
