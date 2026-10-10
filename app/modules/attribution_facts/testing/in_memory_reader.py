"""In-memory fake ``AttributionFactsReader`` для unit-тестов Slice A."""

from __future__ import annotations

from datetime import date

from app.modules.attribution_facts.domain.coverage import evaluate_window_coverage
from app.modules.attribution_facts.domain.models import (
    AttributionCommerceFact,
    AttributionQueryResult,
    AttributionScope,
    DateWindow,
    DayReconciliationResult,
)


class InMemoryAttributionFactsReader:
    """
    Фикстурный reader: фильтрует предзагруженные facts/reconciliations по scope.

    Не выполняет IO; не дублирует spend authority.
    """

    def __init__(
        self,
        *,
        facts: tuple[AttributionCommerceFact, ...] = (),
        reconciliations: tuple[DayReconciliationResult, ...] = (),
        partial_membership_fallback: bool = False,
        source_complete_through: date | None = None,
        package_cutoff_date: date | None = None,
    ) -> None:
        self._facts = facts
        self._reconciliations = reconciliations
        self._partial_membership_fallback = partial_membership_fallback
        self._source_complete_through = source_complete_through
        self._package_cutoff_date = package_cutoff_date

    async def query(
        self,
        scope: AttributionScope,
        window: DateWindow,
    ) -> AttributionQueryResult:
        """Отфильтровать загруженные facts по shop, adv ids и датам окна."""
        filtered = tuple(
            fact
            for fact in self._facts
            if fact.key.shop_id == scope.shop_id
            and (
                not scope.physical_adv_ids
                or fact.key.physical_adv_id in scope.physical_adv_ids
            )
            and window.start <= fact.key.event_date <= window.end
        )
        filtered_recon = tuple(
            item
            for item in self._reconciliations
            if (
                not scope.physical_adv_ids
                or item.physical_adv_id in scope.physical_adv_ids
            )
            and window.start <= item.event_date <= window.end
        )
        all_passed = bool(filtered_recon) and all(r.passed for r in filtered_recon)
        coverage = evaluate_window_coverage(
            has_any_facts=bool(filtered),
            all_days_reconciled=all_passed,
            partial_membership_fallback=self._partial_membership_fallback,
            source_complete_through=self._source_complete_through,
            window=window,
            package_cutoff_date=self._package_cutoff_date,
        )
        return AttributionQueryResult(
            facts=filtered,
            coverage=coverage,
            reconciliations=filtered_recon,
        )
