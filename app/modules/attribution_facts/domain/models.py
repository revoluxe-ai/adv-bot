"""Модели зерна, снимков membership и результатов запроса attribution facts."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date, datetime
from decimal import Decimal
from typing import Literal

from app.modules.attribution_facts.domain.enums import (
    AttributionClass,
    AttributionCoverageStatus,
    AttributionReasonCode,
    SourceFamily,
)


@dataclass(frozen=True, slots=True)
class AttributionFactKey:
    """
    Канонический ключ факта атрибуции.

    ``advertised_nm_id`` намеренно отсутствует: классификация идёт через
    membership snapshot и ``ordered_nm_id``.
    """

    shop_id: str
    physical_adv_id: int
    event_date: date
    app_type: int
    ordered_nm_id: int
    source_family: SourceFamily = SourceFamily.WB_PROMOTION_FULLSTATS_NM_DAY


@dataclass(frozen=True, slots=True)
class MembershipSnapshot:
    """As-of снимок promoted nm ids для physical adv и календарного дня."""

    snapshot_id: str
    shop_id: str
    physical_adv_id: int
    event_date: date
    promoted_nm_ids: frozenset[int]
    authoritative: bool = True
    partial_fallback: bool = False


@dataclass(frozen=True, slots=True)
class AttributionMetrics:
    """Сырые метрики на зерне fact key (без spend authority)."""

    attributed_orders: int | None = None
    attributed_gmv_rub: Decimal | None = None
    attributed_atc: int | None = None
    attributed_units_shks: int | None = None


@dataclass(frozen=True, slots=True)
class ObservationProvenance:
    """Метаданные наблюдения для будущих слайсов persistence."""

    observation_id: str
    source_revision: int
    ingested_at: datetime
    membership_snapshot_id: str


@dataclass(frozen=True, slots=True)
class AttributionCommerceFact:
    """Один latest logical fact на canonical key."""

    key: AttributionFactKey
    metrics: AttributionMetrics
    attribution_class: AttributionClass
    provenance: ObservationProvenance
    reconciliation_pass: bool | None = None


@dataclass(frozen=True, slots=True)
class CampaignDayTotals:
    """Авторитетные campaign-day totals из того же источника fullstats (не CH read в Slice A)."""

    physical_adv_id: int
    event_date: date
    orders: int
    gmv_rub: Decimal


@dataclass(frozen=True, slots=True)
class NmDayContribution:
    """Вклад одного nm/app в дневную reconciliation."""

    app_type: int
    ordered_nm_id: int
    orders: int
    gmv_rub: Decimal


@dataclass(frozen=True, slots=True)
class DayReconciliationResult:
    """Результат сверки nm breakdown с campaign-day totals."""

    physical_adv_id: int
    event_date: date
    passed: bool
    nm_orders_sum: int
    day_orders: int
    nm_gmv_sum: Decimal
    day_gmv_rub: Decimal
    unattributed_orders: int
    reason_codes: tuple[AttributionReasonCode, ...] = ()


@dataclass(frozen=True, slots=True)
class AttributionCoverage:
    """Покрытие запроса attribution facts."""

    status: AttributionCoverageStatus
    reason_codes: tuple[AttributionReasonCode, ...] = ()
    source_complete_through: date | None = None
    effective_covered_range_start: date | None = None
    effective_covered_range_end: date | None = None
    package_cutoff_date: date | None = None


@dataclass(frozen=True, slots=True)
class DateWindow:
    """Календарное окно запроса (включительные границы)."""

    start: date
    end: date


@dataclass(frozen=True, slots=True)
class AttributionScope:
    """Фильтр read-side запроса (physical legs, не synthetic merge)."""

    shop_id: str
    physical_adv_ids: frozenset[int] = field(default_factory=frozenset)
    allow_pair_aggregate: Literal[False] = False


@dataclass(frozen=True, slots=True)
class AttributionQueryResult:
    """Ответ порта ``AttributionFactsReader``."""

    facts: tuple[AttributionCommerceFact, ...]
    coverage: AttributionCoverage
    reconciliations: tuple[DayReconciliationResult, ...] = ()


@dataclass(frozen=True, slots=True)
class DerivedFactEconomics:
    """Производная метрика CPO/DRR с явным отсутствием значения."""

    metric_name: str
    value: Decimal | None
    reason_codes: tuple[AttributionReasonCode, ...] = ()


@dataclass(frozen=True, slots=True)
class CampaignDaySpendReference:
    """
    Типизированная ссылка на внешний spend (Slice A: только контракт).

    Authority остаётся у ``full_adv_wb_stat``; здесь нет дублирования SoT.
    """

    physical_adv_id: int
    event_date: date
    spend_rub: Decimal
