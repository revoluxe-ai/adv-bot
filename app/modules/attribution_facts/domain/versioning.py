"""Концепции версионирования наблюдений (без persistence в Slice A)."""

from __future__ import annotations

from dataclasses import replace
from datetime import datetime

from app.modules.attribution_facts.domain.models import (
    AttributionCommerceFact,
    AttributionMetrics,
    ObservationProvenance,
)


def select_latest_fact(
    observations: tuple[AttributionCommerceFact, ...],
) -> AttributionCommerceFact | None:
    """
    Выбрать latest observation по (source_revision, ingested_at).

    Коррекции заменяют prior; суммирование запрещено на уровне домена.
    """
    if not observations:
        return None

    def sort_key(fact: AttributionCommerceFact) -> tuple[int, datetime]:
        prov = fact.provenance
        return (prov.source_revision, prov.ingested_at)

    return max(observations, key=sort_key)


def apply_latest_metrics(
    base: AttributionCommerceFact,
    newer: AttributionCommerceFact,
) -> AttributionCommerceFact:
    """
    Сформировать logical latest fact после restatement (pure helper).

    Raises:
        ValueError: если keys не совпадают.
    """
    if base.key != newer.key:
        raise ValueError("observation keys must match for revision replace")
    latest = select_latest_fact((base, newer))
    if latest is None:
        return base
    return replace(
        latest,
        metrics=AttributionMetrics(
            attributed_orders=newer.metrics.attributed_orders
            if newer.metrics.attributed_orders is not None
            else latest.metrics.attributed_orders,
            attributed_gmv_rub=newer.metrics.attributed_gmv_rub
            if newer.metrics.attributed_gmv_rub is not None
            else latest.metrics.attributed_gmv_rub,
            attributed_atc=newer.metrics.attributed_atc
            if newer.metrics.attributed_atc is not None
            else latest.metrics.attributed_atc,
            attributed_units_shks=newer.metrics.attributed_units_shks
            if newer.metrics.attributed_units_shks is not None
            else latest.metrics.attributed_units_shks,
        ),
        provenance=newer.provenance,
    )
