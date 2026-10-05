"""Координатор одного тика shop-wide common-sales (L1–L8)."""

from __future__ import annotations

import asyncio
import logging
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

from app.core.di.wb_manager_hub import WBManagerHub
from app.core.mp.wb.api.excs import ApiForbiddenError
from app.core.redis_manager_v2.redis_client import RedisClient
from app.modules.shop_runner.service_manager.services.common_sale_stat_updater.common_sale_stat_updater import (
    CommonSaleStatUpdater,
)
from app.modules.shop_runner.service_manager.wb_shop_data_manager import WBShopDataManager
from app.modules.shop_runner.wb_statistic_manager.redis_common_stat_timestamp_manager import (
    RedisCommonStatTimestampManager,
)

from .collect_types import (
    CollectContext,
    CommonSaleCollectResult,
    CoverageStatus,
    TickCollectSummary,
    TickPartition,
    expected_shop_pairs,
    nmids_with_full_window,
)
from .coverage_evidence import (
    LastAttemptEvidence,
    ShopWideCoverageEvidenceStore,
    derive_attempt_status,
    sorted_nmids_hash,
)
from .legacy_assigned_nmids import resolve_legacy_assigned_nmids
from .shop_assortment_reader import AssortmentPaginationResult, ShopAssortmentReader

logger = logging.getLogger(__name__)
MSK = ZoneInfo("Europe/Moscow")


async def run_shop_wide_common_sale_stat_tick(
    *,
    shop_id: str,
    wb_manager_hub: WBManagerHub,
    wb_shop_data_manager: WBShopDataManager,
    updater: CommonSaleStatUpdater,
    redis_client: RedisClient,
    redis_common_stat_timestamp_manager: RedisCommonStatTimestampManager,
) -> TickCollectSummary:
    """
    Выполнить один тик координатора: A/E/U partition, disjoint collect, evidence.

    Provisional STARTED записывается до Content API / legacy await; обогащается
    тем же attempt_id после partition; funnel STARTED hook — перед первым API.
    """
    today = datetime.now(MSK).date()
    window_start = today - timedelta(days=6)
    window_end = today

    evidence_store = ShopWideCoverageEvidenceStore(redis_client)
    attempt_id = evidence_store.new_attempt_id()

    await evidence_store.write_provisional_started(
        shop_id,
        attempt_id=attempt_id,
        window_start=window_start.isoformat(),
        window_end=window_end.isoformat(),
    )

    products_manager = wb_manager_hub.wb_data_manager.products_manager
    assortment_reader = ShopAssortmentReader(products_manager)

    try:
        assortment = await assortment_reader.paginate_all_nmids()
    except asyncio.CancelledError:
        raise
    except ApiForbiddenError:
        raise
    except Exception as exc:
        logger.warning(
            "Content API escaped assortment reader shop_id=%s: %s",
            shop_id,
            exc,
        )
        assortment = AssortmentPaginationResult(
            nmids=frozenset(),
            pages_completed=0,
            terminal_empty_page=False,
            complete=False,
            partial_reason=f"content_api_error:{type(exc).__name__}",
        )

    legacy = await resolve_legacy_assigned_nmids(
        wb_shop_data_manager,
        only_bot_active=False,
    )

    partition = _compute_partition(assortment.nmids, legacy.nmids, assortment)
    summary = TickCollectSummary()

    if not assortment.complete:
        summary.coverage_status = CoverageStatus.PARTIAL_ASSORTMENT
        summary.partial_reason = assortment.partial_reason

    a_hash = sorted_nmids_hash(partition.assortment_nmids)

    await evidence_store.enrich_started(
        shop_id,
        attempt_id=attempt_id,
        window_start=window_start.isoformat(),
        window_end=window_end.isoformat(),
        a_count=len(partition.assortment_nmids),
        e_count=len(partition.legacy_nmids),
        u_count=len(partition.uncovered_nmids),
        assortment_complete=partition.assortment_complete,
        assortment_pages=partition.assortment_pages,
        assortment_hash=a_hash,
    )

    funnel_started_written = False

    async def _before_first_funnel_api() -> None:
        nonlocal funnel_started_written
        if funnel_started_written:
            return
        funnel_started_written = True
        await evidence_store.write_started(
            shop_id,
            attempt_id=attempt_id,
            window_start=window_start.isoformat(),
            window_end=window_end.isoformat(),
            a_count=len(partition.assortment_nmids),
            e_count=len(partition.legacy_nmids),
            u_count=len(partition.uncovered_nmids),
            assortment_complete=partition.assortment_complete,
            assortment_pages=partition.assortment_pages,
            assortment_hash=a_hash,
        )

    collect_context = CollectContext(
        attempted_nmids=frozenset(),
        window_start=window_start,
        window_end=window_end,
    )

    e_nmids_sorted = sorted(partition.legacy_nmids)
    e_result: CommonSaleCollectResult | None = None
    if legacy.complex_advs:
        e_nmids_from_adv = sorted({adv.main_nmid for adv in legacy.complex_advs})
        e_result = await updater.collect_by_nmids(
            e_nmids_from_adv,
            collect_context=collect_context,
            before_first_api=_before_first_funnel_api,
        )
    elif e_nmids_sorted:
        e_result = await updater.collect_by_nmids(
            e_nmids_sorted,
            collect_context=collect_context,
            before_first_api=_before_first_funnel_api,
        )

    if e_result is not None:
        _merge_route_result(summary, e_result)
        summary.legacy_route_updated_nmids.update(e_result.updated_nmids)

    u_nmids_sorted = sorted(partition.uncovered_nmids)
    if u_nmids_sorted:
        u_result = await updater.collect_by_nmids(
            u_nmids_sorted,
            collect_context=collect_context,
            before_first_api=_before_first_funnel_api,
        )
        _merge_route_result(summary, u_result)

    expected_pairs = expected_shop_pairs(
        partition.assortment_nmids,
        window_start,
        window_end,
    )

    returned_coverage = summary.returned_pairs & expected_pairs
    summary.returned_pairs = set(returned_coverage)

    persisted_coverage = summary.persisted_pairs & expected_pairs
    summary.persisted_pairs = set(persisted_coverage)

    full_window_a = nmids_with_full_window(
        frozenset(persisted_coverage),
        partition.assortment_nmids,
        window_start,
        window_end,
    )
    summary.updated_nmids = set(full_window_a)
    summary.failed_nmids = set(partition.assortment_nmids - full_window_a)

    summary.coverage_status = _finalize_coverage_status(
        summary,
        partition=partition,
        expected_pair_count=len(expected_pairs),
        persisted_pair_count=len(persisted_coverage),
    )

    missing_pairs = max(0, len(expected_pairs) - len(persisted_coverage))

    terminal = LastAttemptEvidence(
        attempt_status=derive_attempt_status(summary.coverage_status),
        window_start=window_start.isoformat(),
        window_end=window_end.isoformat(),
        a_count=len(partition.assortment_nmids),
        e_count=len(partition.legacy_nmids),
        u_count=len(partition.uncovered_nmids),
        assortment_complete=partition.assortment_complete,
        assortment_pages=partition.assortment_pages,
        expected_pair_count=len(expected_pairs),
        returned_pair_count=len(returned_coverage),
        persisted_pair_count=len(persisted_coverage),
        missing_pair_count=missing_pairs,
        rejected_pair_count=summary.rejected_pair_count,
        partial_reason=summary.partial_reason,
        tick_ts=datetime.now(MSK).isoformat(),
        attempt_id=attempt_id,
        assortment_hash=a_hash,
        provisional=False,
    )
    await evidence_store.write_terminal(shop_id, terminal)
    await evidence_store.write_transition_snapshot(
        shop_id,
        attempt_id=attempt_id,
        a_nmids=partition.assortment_nmids,
        e_nmids=partition.legacy_nmids,
        u_nmids=partition.uncovered_nmids,
    )

    if legacy.complex_advs:
        nmid_to_adv_ids: dict[int, set[int]] = {}
        for adv in legacy.complex_advs:
            nmid_to_adv_ids.setdefault(adv.main_nmid, set()).update(adv.all_adv_ids)
        for nmid in summary.legacy_route_updated_nmids:
            for adv_id in nmid_to_adv_ids.get(nmid, set()):
                await redis_common_stat_timestamp_manager.set(adv_id)

    logger.info(
        "shop_wide_common_sale_stat tick shop_id=%s all_shop_nmids_count=%d "
        "existing_covered_count=%d uncovered_count=%d updated_count=%d "
        "failed_count=%d coverage_status=%s",
        shop_id,
        len(partition.assortment_nmids),
        len(partition.legacy_nmids),
        len(partition.uncovered_nmids),
        len(summary.updated_nmids),
        len(summary.failed_nmids),
        summary.coverage_status.value,
    )

    return summary


def _compute_partition(
    assortment_nmids: frozenset[int],
    legacy_nmids: frozenset[int],
    assortment_result: AssortmentPaginationResult,
) -> TickPartition:
    proven_a = assortment_nmids if assortment_result.complete else assortment_nmids
    u = frozenset(n for n in proven_a if n not in legacy_nmids)

    return TickPartition(
        assortment_nmids=frozenset(proven_a),
        legacy_nmids=legacy_nmids,
        uncovered_nmids=u,
        assortment_pages=assortment_result.pages_completed,
        assortment_complete=assortment_result.complete,
        assortment_partial_reason=assortment_result.partial_reason,
        terminal_empty_page=assortment_result.terminal_empty_page,
    )


def _merge_route_result(
    summary: TickCollectSummary,
    route_result: CommonSaleCollectResult,
) -> None:
    summary.returned_pairs.update(route_result.returned_pairs)
    summary.persisted_pairs.update(route_result.persisted_pairs)
    summary.rejected_pair_count += route_result.rejected_pair_count
    if route_result.ch_insert_failed:
        summary.coverage_status = CoverageStatus.PARTIAL_CH


def _finalize_coverage_status(
    summary: TickCollectSummary,
    *,
    partition: TickPartition,
    expected_pair_count: int,
    persisted_pair_count: int,
) -> CoverageStatus:
    if summary.coverage_status == CoverageStatus.PARTIAL_CH:
        summary.partial_reason = summary.partial_reason or "ch_insert_failed"
        return CoverageStatus.PARTIAL_CH

    if not partition.assortment_complete:
        summary.partial_reason = partition.assortment_partial_reason
        return CoverageStatus.PARTIAL_ASSORTMENT

    if summary.rejected_pair_count > 0:
        summary.partial_reason = "rejected_facts"
        return CoverageStatus.PARTIAL_API

    if summary.failed_nmids:
        summary.partial_reason = "api_batch_failures"
        return CoverageStatus.PARTIAL_API

    if persisted_pair_count < expected_pair_count and partition.assortment_nmids:
        summary.partial_reason = "missing_pairs"
        return CoverageStatus.PARTIAL_API

    return CoverageStatus.COMPLETE
