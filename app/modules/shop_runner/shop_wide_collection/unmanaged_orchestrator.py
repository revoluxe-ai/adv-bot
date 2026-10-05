"""Minimal unmanaged campaign advertising collector (design §D.3, tasks 4.1–4.4, 6.1).

Spec: ``connected-shop-campaign-ad-data-collection``.
Debt: ``openspec/architectural-debt/TEMPORARY_DUAL_CAMPAIGN_COLLECTION.md``.
Decision: ``openspec/changes/shop-wide-campaign-data-collection/decisions/shop-runner-shop-wide-collection/decision.md``.

Orchestrator: WB discovery → resolver → inventory upsert → unmanaged-only
``full_adv_wb_stat`` через injectable thin ends. **MUST NOT** вызывать
``get_sales_funnel_products_history``, ``ClickHouseCommonStatManager.insert``,
``ClustersAdvStatUpdater``, ``update_advs_in_db`` или создавать ``AdvSetting``.

Перед fact write — pre-write gate по ``shop_campaign_inventory.route_version``
и collection ownership. Availability append не авторизует запись fact grain.

Production entry: ``CoroutinesManager.collect_shop_wide_campaign_advertising``
→ ``tick_wiring.run_shop_wide_unmanaged_tick`` (задача 8.1).
"""

from __future__ import annotations

import logging
from collections.abc import Iterable, Sequence
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Protocol

from app.modules.full_stat_adv_updater.types.full_adv_stat import FullAdvStat
from app.modules.shop_runner.service_manager.wb_shop_data_manager.dto.complex_adv import (
    ComplexAdv,
)
from app.modules.shop_runner.shop_wide_collection.availability_append import (
    ShopCampaignAvailabilityClickHouse,
    append_shop_campaign_collection_availability,
)
from app.modules.shop_runner.shop_wide_collection.inventory_route_read import (
    ShopCampaignInventoryRouteReader,
    load_inventory_route_snapshots,
)
from app.modules.shop_runner.shop_wide_collection.inventory_upsert import (
    ShopCampaignInventoryClickHouse,
    ShopCampaignInventoryWrite,
    WbAdvertDiscoveryItem,
    discovered_campaign_from_advert,
    upsert_discovered_shop_campaign_inventory,
)
from app.modules.shop_runner.shop_wide_collection.route_resolver import (
    CampaignCollectionGrain,
    CampaignCollectionRouteResolver,
    CampaignRouteDecision,
    CollectionRoute,
    RouteResolverTickInput,
    RouteResolverTickResult,
)
from app.modules.shop_runner.shop_wide_collection.route_write_gate import (
    COLLECTOR_UNMANAGED_FULL_ADV,
    REASON_COLLECTOR_SOURCE_ERROR,
    REASON_FACT_WRITE_ERROR,
    REASON_UNMANAGED_FACT_WRITE_SKIPPED,
    REASON_UNMANAGED_FACT_WRITE_SUCCEEDED,
    REASON_UNMANAGED_NOT_ELIGIBLE,
    RouteWriteGateInput,
    evaluate_unmanaged_fact_write_gate,
)

logger = logging.getLogger(__name__)


class WbCampaignDiscovery(Protocol):
    """Thin end: WB campaign discovery через ``CampaignsInfoV2`` seam."""

    async def get_all_campaigns(self) -> Sequence[WbAdvertDiscoveryItem]: ...


class FullAdvStatFetcher(Protocol):
    """Thin end: ``wb_data_getter.get_full_adv_stat_for_adv_ids``."""

    async def get_full_adv_stat_for_adv_ids(
        self,
        adv_ids: set[int],
        threshold_dates: int,
    ) -> list[FullAdvStat]: ...


class FullAdvStatWriter(Protocol):
    """Thin end: ``full_wb_adv_stat.insert``."""

    async def insert(self, stats: Iterable[FullAdvStat]) -> None: ...


@dataclass(frozen=True, slots=True)
class UnmanagedAdvCollectOutcome:
    """Исход сбора для одного ``adv_id`` на unmanaged path."""

    adv_id: int
    fact_write_attempted: bool
    fact_write_succeeded: bool
    availability_reason_code: str
    checked_route_version: int


@dataclass(frozen=True, slots=True)
class UnmanagedCollectTickResult:
    """Сводка одного unmanaged collect tick."""

    shop_id: str
    wb_discovered_count: int
    unmanaged_eligible_adv_ids: frozenset[int]
    inventory_writes: tuple[ShopCampaignInventoryWrite, ...]
    route_result: RouteResolverTickResult
    outcomes: tuple[UnmanagedAdvCollectOutcome, ...]
    full_adv_stats_written: int


def _route_string_for_decision(decision: CampaignRouteDecision) -> str | None:
    """Строка route для inventory upsert или ``None`` если resolver UNKNOWN."""
    if decision.route is CollectionRoute.UNKNOWN:
        return None
    return decision.route.value


def _build_inventory_routes(
    route_result: RouteResolverTickResult,
) -> dict[int, str]:
    """Route per adv_id только для ``full_adv_wb_stat`` grain."""
    routes: dict[int, str] = {}
    for decision in route_result.decisions:
        if decision.key.grain is not CampaignCollectionGrain.FULL_ADV_WB_STAT:
            continue
        route_value = _route_string_for_decision(decision)
        if route_value is not None:
            routes[decision.key.wb_adv_id] = route_value
    return routes


def select_unmanaged_full_adv_adv_ids(
    route_result: RouteResolverTickResult,
) -> frozenset[int]:
    """WB discovery minus managed ownership; UNKNOWN fail-closed (task 4.1)."""
    eligible: set[int] = set()
    for decision in route_result.decisions:
        if (
            decision.key.grain is CampaignCollectionGrain.FULL_ADV_WB_STAT
            and CampaignCollectionRouteResolver.is_unmanaged_collector_write_eligible(
                decision
            )
        ):
            eligible.add(decision.key.wb_adv_id)
    return frozenset(eligible)


def _observed_epochs_from_inventory(
    inventory_writes: Sequence[ShopCampaignInventoryWrite],
    eligible_adv_ids: frozenset[int],
) -> dict[int, int]:
    """``route_version`` после upsert для adv_ids, идущих в unmanaged collect."""
    epochs: dict[int, int] = {}
    for row in inventory_writes:
        if row.adv_id in eligible_adv_ids:
            epochs[row.adv_id] = row.route_version
    return epochs


async def _fetch_stats_for_adv_id(
    fetcher: FullAdvStatFetcher,
    adv_id: int,
    threshold_dates: int,
) -> list[FullAdvStat]:
    """Per-adv WB fetch; изолирует partial token/source failure (task 6.1)."""
    return await fetcher.get_full_adv_stat_for_adv_ids({adv_id}, threshold_dates)


async def collect_unmanaged_campaign_advertising(
    *,
    shop_id: str,
    loader_complex_advs: Sequence[ComplexAdv],
    campaigns_discovery: WbCampaignDiscovery,
    inventory_client: ShopCampaignInventoryClickHouse,
    availability_client: ShopCampaignAvailabilityClickHouse,
    full_adv_stat_fetcher: FullAdvStatFetcher,
    full_adv_stat_writer: FullAdvStatWriter,
    threshold_dates: int,
    route_resolver: CampaignCollectionRouteResolver | None = None,
    route_reader: ShopCampaignInventoryRouteReader | None = None,
    observed_at: datetime | None = None,
) -> UnmanagedCollectTickResult:
    """Один unmanaged tick: discovery → route → inventory → gated full_adv write.

    Side effects (when not stubbed): CH inventory/availability/full_adv_wb_stat.
    **MUST NOT** PG enrollment, management writes, funnel или clusters paths.

    Args:
        shop_id: магазин shop-runner.
        loader_complex_advs: post-filter ``get_complex_advs(only_bot_active=False)``.
        campaigns_discovery: injectable ``CampaignsInfoV2.get_all_campaigns`` seam.
        inventory_client: CH writer/reader inventory (upsert + gate read).
        availability_client: append-only availability writer.
        full_adv_stat_fetcher: injectable ``get_full_adv_stat_for_adv_ids``.
        full_adv_stat_writer: injectable ``full_wb_adv_stat.insert``.
        threshold_dates: окно дней для WB full stat read.
        route_resolver: optional resolver (default — новый экземпляр).
        route_reader: optional reader для gate (default — ``inventory_client``).
        observed_at: момент discovery/inventory (UTC).

    Returns:
        Сводка tick с per-adv outcomes и числом записанных stat rows.
    """
    if shop_id == "":
        raise ValueError("shop_id must be a non-empty string")

    resolver = route_resolver or CampaignCollectionRouteResolver()
    reader = route_reader or inventory_client

    wb_items = await campaigns_discovery.get_all_campaigns()
    discovered_campaigns = tuple(
        discovered_campaign_from_advert(item) for item in wb_items
    )
    wb_discovered_ids = frozenset(campaign.adv_id for campaign in discovered_campaigns)

    tick_input = RouteResolverTickInput(
        shop_id=shop_id,
        wb_discovered_adv_ids=wb_discovered_ids,
        loader_complex_advs=tuple(loader_complex_advs),
    )
    route_result = resolver.resolve_tick(tick_input)
    inventory_routes = _build_inventory_routes(route_result)

    inventory_writes = await upsert_discovered_shop_campaign_inventory(
        inventory_client,
        shop_id=shop_id,
        campaigns=discovered_campaigns,
        routes=inventory_routes,
        observed_at=observed_at,
    )

    eligible_adv_ids = select_unmanaged_full_adv_adv_ids(route_result)
    observed_epochs = _observed_epochs_from_inventory(
        inventory_writes, eligible_adv_ids
    )

    outcomes: list[UnmanagedAdvCollectOutcome] = []
    written_count = 0

    for adv_id in sorted(eligible_adv_ids):
        route_decision = route_result.decision_for(
            adv_id, CampaignCollectionGrain.FULL_ADV_WB_STAT
        )
        observed_epoch = observed_epochs.get(adv_id, 0)
        current_by_adv = await load_inventory_route_snapshots(
            reader,
            shop_id=shop_id,
            adv_ids=(adv_id,),
        )
        gate = evaluate_unmanaged_fact_write_gate(
            RouteWriteGateInput(
                shop_id=shop_id,
                adv_id=adv_id,
                observed_route_version=observed_epoch,
                current_inventory=current_by_adv.get(adv_id),
                route_decision=route_decision,
            )
        )

        adv_stats: list[FullAdvStat] = []
        fetch_failed = False
        if gate.allow_fact_write:
            try:
                adv_stats = await _fetch_stats_for_adv_id(
                    full_adv_stat_fetcher,
                    adv_id,
                    threshold_dates,
                )
            except Exception:
                logger.exception(
                    "unmanaged collect source error shop_id=%s adv_id=%s",
                    shop_id,
                    adv_id,
                )
                fetch_failed = True

        fact_attempted = gate.allow_fact_write and bool(adv_stats) and not fetch_failed
        fact_succeeded = False
        availability_reason = gate.reason_code
        checked_route_version = gate.checked_route_version

        if fetch_failed:
            availability_reason = REASON_COLLECTOR_SOURCE_ERROR
        elif gate.allow_fact_write and adv_stats:
            try:
                await full_adv_stat_writer.insert(adv_stats)
            except Exception:
                logger.exception(
                    "unmanaged collect fact write error shop_id=%s adv_id=%s",
                    shop_id,
                    adv_id,
                )
                availability_reason = REASON_FACT_WRITE_ERROR
            else:
                fact_succeeded = True
                written_count += len(adv_stats)
                availability_reason = REASON_UNMANAGED_FACT_WRITE_SUCCEEDED
        elif gate.allow_fact_write and not adv_stats and not fetch_failed:
            availability_reason = REASON_UNMANAGED_FACT_WRITE_SKIPPED
        elif not gate.allow_fact_write:
            availability_reason = gate.reason_code

        _ = await append_shop_campaign_collection_availability(
            availability_client,
            shop_id=shop_id,
            adv_id=adv_id,
            collector_id=COLLECTOR_UNMANAGED_FULL_ADV,
            reason_code=availability_reason,
            route_version=checked_route_version,
        )

        outcomes.append(
            UnmanagedAdvCollectOutcome(
                adv_id=adv_id,
                fact_write_attempted=fact_attempted,
                fact_write_succeeded=fact_succeeded,
                availability_reason_code=availability_reason,
                checked_route_version=checked_route_version,
            )
        )

    for decision in route_result.decisions:
        if decision.key.grain is not CampaignCollectionGrain.FULL_ADV_WB_STAT:
            continue
        adv_id = decision.key.wb_adv_id
        if adv_id in eligible_adv_ids:
            continue
        if decision.route is not CollectionRoute.UNKNOWN:
            continue
        observed_epoch = 0
        for row in inventory_writes:
            if row.adv_id == adv_id:
                observed_epoch = row.route_version
                break
        _ = await append_shop_campaign_collection_availability(
            availability_client,
            shop_id=shop_id,
            adv_id=adv_id,
            collector_id=COLLECTOR_UNMANAGED_FULL_ADV,
            reason_code=REASON_UNMANAGED_NOT_ELIGIBLE,
            route_version=observed_epoch,
        )

    logger.info(
        "unmanaged collect tick shop_id=%s discovered=%s eligible=%s written_stats=%s",
        shop_id,
        len(wb_discovered_ids),
        len(eligible_adv_ids),
        written_count,
    )

    return UnmanagedCollectTickResult(
        shop_id=shop_id,
        wb_discovered_count=len(wb_discovered_ids),
        unmanaged_eligible_adv_ids=eligible_adv_ids,
        inventory_writes=inventory_writes,
        route_result=route_result,
        outcomes=tuple(outcomes),
        full_adv_stats_written=written_count,
    )


def utc_now_naive() -> datetime:
    """Naive UTC для inventory ``DateTime`` колонок в тестах."""
    return datetime.now(timezone.utc).replace(tzinfo=None)
