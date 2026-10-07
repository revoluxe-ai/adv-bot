"""Сборка in-memory AttributionIngestBatch из raw fullstats + membership."""

from __future__ import annotations

import hashlib
from collections import defaultdict
from collections.abc import Mapping
from datetime import date, datetime, timezone
from decimal import Decimal
from typing import Any

from app.modules.attribution_facts.domain.classification import classify_ordered_nm
from app.modules.attribution_facts.domain.coverage import evaluate_window_coverage
from app.modules.attribution_facts.domain.enums import (
    AttributionReasonCode,
    SourceFamily,
)
from app.modules.attribution_facts.domain.ingest_models import (
    AttributionIngestBatch,
    coverage_for_ingest_source,
)
from app.modules.attribution_facts.domain.models import (
    AttributionCommerceFact,
    AttributionFactKey,
    AttributionMetrics,
    CampaignDayTotals,
    DateWindow,
    DayReconciliationResult,
    NmDayContribution,
    ObservationProvenance,
)
from app.modules.attribution_facts.domain.reconciliation import reconcile_campaign_day
from app.modules.attribution_facts.ingest.raw_fullstats import (
    fullstats_item_to_raw_rows,
    fullstats_items_to_campaign_day_rows,
)
from app.modules.attribution_facts.membership.resolver import (
    MembershipResolveResult,
    MembershipSnapshotResolver,
)


def _observation_id(
    shop_id: str,
    key: AttributionFactKey,
    orders: int,
    gmv: Decimal,
) -> str:
    blob = f"{shop_id}|{key}|{orders}|{gmv}"
    return hashlib.sha256(blob.encode()).hexdigest()[:32]


async def build_ingest_batch_from_raw_items(
    *,
    shop_id: str,
    raw_items: tuple[Mapping[str, Any], ...],
    resolver: MembershipSnapshotResolver,
    source_revision: int = 1,
) -> AttributionIngestBatch:
    """
    Построить facts + reconciliation + coverage из raw fullstats items.

    Args:
        shop_id: Магазин shop-runner.
        raw_items: Сериализованные FullStatsItem dicts с apps/nms.
        resolver: Membership resolver для physical adv.
        source_revision: Версия источника для provenance.

    Returns:
        AttributionIngestBatch без persistence.
    """
    nm_rows = tuple(
        row for item in raw_items for row in fullstats_item_to_raw_rows(item)
    )
    day_rows = fullstats_items_to_campaign_day_rows(raw_items)
    used_raw = bool(nm_rows)
    ingested_at = datetime.now(tz=timezone.utc)
    facts: list[AttributionCommerceFact] = []
    partial_fallback = False
    reason_acc: list[AttributionReasonCode] = []

    membership_by_date: dict[date, MembershipResolveResult] = {}
    for row in nm_rows:
        if row.event_date not in membership_by_date:
            resolved: MembershipResolveResult = await resolver.resolve(row.event_date)
            membership_by_date[row.event_date] = resolved
            if resolved.partial_fallback:
                partial_fallback = True
            reason_acc.extend(resolved.reason_codes)
        resolved_day: MembershipResolveResult = membership_by_date[row.event_date]
        attr_class = classify_ordered_nm(
            row.ordered_nm_id,
            resolved_day.snapshot,
        )
        key = AttributionFactKey(
            shop_id=shop_id,
            physical_adv_id=row.physical_adv_id,
            event_date=row.event_date,
            app_type=row.app_type,
            ordered_nm_id=row.ordered_nm_id,
            source_family=SourceFamily.WB_PROMOTION_FULLSTATS_NM_DAY,
        )
        snap_id = (
            resolved_day.snapshot.snapshot_id
            if resolved_day.snapshot is not None
            else "missing"
        )
        prov = ObservationProvenance(
            observation_id=_observation_id(
                shop_id, key, row.orders, row.gmv_rub
            ),
            source_revision=source_revision,
            ingested_at=ingested_at,
            membership_snapshot_id=snap_id,
        )
        facts.append(
            AttributionCommerceFact(
                key=key,
                metrics=AttributionMetrics(
                    attributed_orders=row.orders,
                    attributed_gmv_rub=row.gmv_rub,
                    attributed_atc=row.atc,
                    attributed_units_shks=row.units_shks,
                ),
                attribution_class=attr_class,
                provenance=prov,
            )
        )

    recon_by_key: dict[tuple[int, object], list[NmDayContribution]] = defaultdict(
        list
    )
    for row in nm_rows:
        recon_by_key[(row.physical_adv_id, row.event_date)].append(
            NmDayContribution(
                row.app_type,
                row.ordered_nm_id,
                row.orders,
                row.gmv_rub,
            )
        )
    reconciliations: list[DayReconciliationResult] = []
    all_passed = True
    for day in day_rows:
        contributions = tuple(
            recon_by_key.get((day.physical_adv_id, day.event_date), ())
        )
        result = reconcile_campaign_day(
            CampaignDayTotals(
                physical_adv_id=day.physical_adv_id,
                event_date=day.event_date,
                orders=day.orders,
                gmv_rub=day.gmv_rub,
            ),
            contributions,
        )
        reconciliations.append(result)
        if not result.passed:
            all_passed = False

    if not used_raw:
        coverage = coverage_for_ingest_source(
            has_raw_nm_rows=False,
            partial_membership_fallback=partial_fallback,
            all_days_reconciled=False,
        )
    else:
        dates = sorted({row.event_date for row in nm_rows})
        today = datetime.now(tz=timezone.utc).date()
        window = DateWindow(dates[0], dates[-1]) if dates else DateWindow(today, today)
        coverage = evaluate_window_coverage(
            has_any_facts=bool(facts),
            all_days_reconciled=all_passed and bool(reconciliations),
            partial_membership_fallback=partial_fallback,
            source_complete_through=window.end if all_passed else None,
            window=window,
        )

    return AttributionIngestBatch(
        shop_id=shop_id,
        facts=tuple(facts),
        reconciliations=tuple(reconciliations),
        coverage=coverage,
        used_raw_apps_nms=used_raw,
        partial_membership_fallback=partial_fallback,
        reason_codes=tuple(dict.fromkeys(reason_acc)),
    )


def collapsed_mapper_only_coverage_status() -> str:
    """DayStats-only path cannot claim COMPLETE nm attribution."""
    batch = coverage_for_ingest_source(
        has_raw_nm_rows=False,
        partial_membership_fallback=False,
        all_days_reconciled=True,
    )
    return str(batch.status)
