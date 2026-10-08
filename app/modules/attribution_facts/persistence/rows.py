"""Маппинг domain ingest batch → строки ClickHouse (без spend authority)."""

from __future__ import annotations

from collections.abc import Sequence
from datetime import date, datetime
from decimal import Decimal
from typing import cast

from app.modules.attribution_facts.domain.ingest_models import AttributionIngestBatch
from app.modules.attribution_facts.domain.models import AttributionCommerceFact


def observation_rows_from_batch(
    batch: AttributionIngestBatch,
) -> list[tuple[object, ...]]:
    """Сериализовать facts batch в кортежи для INSERT attribution_fact_observations."""
    partial_flag = 1 if batch.partial_membership_fallback else 0
    rows: list[tuple[object, ...]] = []
    for fact in batch.facts:
        key = fact.key
        metrics = fact.metrics
        prov = fact.provenance
        rows.append(
            (
                batch.shop_id,
                key.physical_adv_id,
                key.event_date,
                key.app_type,
                key.ordered_nm_id,
                str(key.source_family),
                prov.observation_id,
                prov.source_revision,
                prov.ingested_at,
                str(fact.attribution_class),
                metrics.attributed_orders,
                metrics.attributed_gmv_rub,
                metrics.attributed_atc,
                metrics.attributed_units_shks,
                prov.membership_snapshot_id,
                partial_flag,
            )
        )
    return rows


def reconciliation_rows_from_batch(
    batch: AttributionIngestBatch,
) -> list[tuple[object, ...]]:
    """Сериализовать reconciliation results для INSERT attribution_day_reconciliation."""
    from datetime import datetime, timezone

    if not batch.reconciliations:
        return []
    if batch.facts:
        ingested_at = batch.facts[0].provenance.ingested_at
        source_revision = batch.facts[0].provenance.source_revision
    else:
        ingested_at = datetime.now(tz=timezone.utc)
        source_revision = 1
    rows: list[tuple[object, ...]] = []
    for recon in batch.reconciliations:
        rows.append(
            (
                batch.shop_id,
                recon.physical_adv_id,
                recon.event_date,
                1 if recon.passed else 0,
                recon.nm_orders_sum,
                recon.day_orders,
                recon.nm_gmv_sum,
                recon.day_gmv_rub,
                recon.unattributed_orders,
                [str(code) for code in recon.reason_codes],
                source_revision,
                ingested_at,
            )
        )
    return rows


def fact_from_ch_row(row: Sequence[object]) -> AttributionCommerceFact:
    """Восстановить AttributionCommerceFact из projected CH row (reader)."""
    from app.modules.attribution_facts.domain.enums import (
        AttributionClass,
        SourceFamily,
    )
    from app.modules.attribution_facts.domain.models import (
        AttributionFactKey,
        AttributionMetrics,
        ObservationProvenance,
    )

    (
        shop_id,
        physical_adv_id,
        event_date,
        app_type,
        ordered_nm_id,
        source_family,
        observation_id,
        source_revision,
        ingested_at,
        attribution_class,
        attributed_orders,
        attributed_gmv_rub,
        attributed_atc,
        attributed_units_shks,
        membership_snapshot_id,
        _partial_flag,
    ) = row
    key = AttributionFactKey(
        shop_id=str(shop_id),
        physical_adv_id=int(cast(int, physical_adv_id)),
        event_date=_row_date(event_date),
        app_type=int(cast(int, app_type)),
        ordered_nm_id=int(cast(int, ordered_nm_id)),
        source_family=SourceFamily(str(source_family)),
    )
    return AttributionCommerceFact(
        key=key,
        metrics=AttributionMetrics(
            attributed_orders=int(cast(int, attributed_orders))
            if attributed_orders is not None
            else None,
            attributed_gmv_rub=Decimal(str(attributed_gmv_rub))
            if attributed_gmv_rub is not None
            else None,
            attributed_atc=int(cast(int, attributed_atc))
            if attributed_atc is not None
            else None,
            attributed_units_shks=int(cast(int, attributed_units_shks))
            if attributed_units_shks is not None
            else None,
        ),
        attribution_class=AttributionClass(str(attribution_class)),
        provenance=ObservationProvenance(
            observation_id=_decode_ch_string(observation_id),
            source_revision=int(cast(int, source_revision)),
            ingested_at=cast(datetime, ingested_at),
            membership_snapshot_id=str(membership_snapshot_id),
        ),
    )


def _decode_ch_string(value: object) -> str:
    if isinstance(value, bytes):
        return value.decode("ascii").rstrip("\x00")
    return str(value).strip()


def _row_date(value: object) -> date:
    if isinstance(value, date):
        return value
    return date.fromisoformat(str(value))
