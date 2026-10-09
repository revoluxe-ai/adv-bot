"""Bounded backfill: explicit shop/adv window, replay-safe observation append."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Callable, Coroutine

from app.modules.attribution_facts.domain.ingest_models import AttributionIngestBatch
from app.modules.attribution_facts.domain.models import DateWindow
from app.modules.attribution_facts.ingest.pipeline import build_ingest_batch_from_raw_items
from app.modules.attribution_facts.membership.resolver import MembershipSnapshotResolver
from app.modules.attribution_facts.ports.observation_writer import (
    AttributionObservationWriter,
)

RawItemsFetcher = Callable[
    [str, int, DateWindow],
    Coroutine[Any, Any, tuple[dict[str, object], ...]],
]
ResolverFactory = Callable[
    [str, int, int],
    MembershipSnapshotResolver,
]


@dataclass(frozen=True, slots=True)
class BoundedBackfillRequest:
    """Explicit scope for one bounded backfill run (no unbounded sweep)."""

    shop_id: str
    physical_adv_id: int
    adv_setting_id: int
    window: DateWindow
    max_raw_items: int = 50


@dataclass(frozen=True, slots=True)
class BoundedBackfillResult:
    """Summary of a bounded backfill attempt."""

    batches_written: int
    facts_persisted: int
    truncated: bool


async def run_bounded_backfill(
    request: BoundedBackfillRequest,
    *,
    fetch_raw_items: RawItemsFetcher,
    resolver_factory: ResolverFactory,
    writer: AttributionObservationWriter,
) -> BoundedBackfillResult:
    """
    Fetch raw fullstats-shaped items for window and persist ingest batches.

    Uses the same pipeline semantics as live ingest; does not call WB directly.
    """
    raw_items = await fetch_raw_items(
        request.shop_id,
        request.physical_adv_id,
        request.window,
    )
    truncated = len(raw_items) > request.max_raw_items
    items = tuple(raw_items[: request.max_raw_items])
    if not items:
        return BoundedBackfillResult(
            batches_written=0,
            facts_persisted=0,
            truncated=truncated,
        )
    resolver = resolver_factory(
        request.shop_id,
        request.adv_setting_id,
        request.physical_adv_id,
    )
    batch: AttributionIngestBatch = await build_ingest_batch_from_raw_items(
        shop_id=request.shop_id,
        raw_items=items,
        resolver=resolver,
    )
    await writer.append_batch(batch)
    return BoundedBackfillResult(
        batches_written=1,
        facts_persisted=len(batch.facts),
        truncated=truncated,
    )
