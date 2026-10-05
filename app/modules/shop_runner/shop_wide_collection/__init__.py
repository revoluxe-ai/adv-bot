"""Shop-wide RECORD seam внутри shop-runner.

Placement: proposed decision
``openspec/changes/shop-wide-campaign-data-collection/decisions/shop-runner-shop-wide-collection/decision.md``.
Debt: ``openspec/architectural-debt/TEMPORARY_DUAL_CAMPAIGN_COLLECTION.md``.

``WBShop.run`` читает per-shop feature flag (задача 2.3) и при
``DUAL_PATH_ACTIVE`` ставит ``collect_shop_wide_campaign_advertising`` (§8.1).
Unmanaged orchestrator (``collect_unmanaged_campaign_advertising``) вызывается
из ``tick_wiring.run_shop_wide_unmanaged_tick``. Маршрут классифицирует
``CampaignCollectionRouteResolver`` (задача 3.1).
"""

from app.modules.shop_runner.shop_wide_collection.feature_flag import (
    ROUTE_EPOCH_SOURCE,
    ShopWideCollectionDecision,
    ShopWideCollectionMode,
    ShopWideUnmanagedSliceNotReady,
    apply_shop_wide_collection_gate,
    enforce_shop_wide_collection_fail_closed,
    evaluate_shop_wide_collection,
)
from app.modules.shop_runner.shop_wide_collection.route_resolver import (
    REASON_MANAGED_LOADER_OWNERSHIP,
    REASON_UNKNOWN_CLUSTERS_OUTSIDE_MANAGED,
    REASON_UNKNOWN_NOT_CLASSIFIED,
    REASON_UNMANAGED_WB_DISCOVERY,
    REASON_UNSUPPORTED_GRAIN,
    CampaignCollectionGrain,
    CampaignCollectionRouteResolver,
    CampaignRouteDecision,
    CampaignRouteKey,
    CollectionRoute,
    RouteResolverTickInput,
    RouteResolverTickResult,
    build_managed_ownership_adv_ids,
)
from app.modules.shop_runner.shop_wide_collection.availability_append import (
    ShopCampaignAvailabilityClickHouse,
    ShopCampaignAvailabilityWrite,
    append_shop_campaign_collection_availability,
)
from app.modules.shop_runner.shop_wide_collection.inventory_route_read import (
    ShopCampaignInventoryRouteReader,
    load_inventory_route_snapshots,
)
from app.modules.shop_runner.shop_wide_collection.inventory_upsert import (
    ROUTE_NOT_ASSIGNED,
    DiscoveredWbCampaign,
    ShopCampaignInventoryClickHouse,
    ShopCampaignInventoryWrite,
    WbAdvertDiscoveryItem,
    discovered_campaign_from_advert,
    map_wb_lifecycle,
    upsert_discovered_shop_campaign_inventory,
)
from app.modules.shop_runner.shop_wide_collection.full_adv_read_latest import (
    FullAdvReadLatestClickHouse,
    FullAdvReadLatestRow,
    load_read_latest_full_adv_facts,
)
from app.modules.shop_runner.shop_wide_collection.route_handoff import (
    ConnectHandoffTickResult,
    DoneDisconnectHandoffResult,
    RefusedOwnershipStabilityResult,
    connect_handoff_newly_managed_adv_ids,
    done_handoff_transitioned_to_unmanaged,
    evaluate_refused_disconnect_like_handoff,
    resolve_connect_handoff_next_tick,
    resolve_done_disconnect_handoff,
    unmanaged_blocked_adv_ids_after_connect,
)
from app.modules.shop_runner.shop_wide_collection.route_transition_reconcile import (
    RouteTransitionReconcileOutcome,
    count_raw_full_adv_grains,
    read_latest_grain_keys,
    reconcile_route_transition_read_latest,
)
from app.modules.shop_runner.shop_wide_collection.route_write_gate import (
    COLLECTOR_ROUTE_TRANSITION_RECONCILE,
    COLLECTOR_UNMANAGED_FULL_ADV,
    REASON_COLLECTOR_SOURCE_ERROR,
    REASON_FACT_WRITE_ERROR,
    REASON_OWNERSHIP_MISMATCH,
    REASON_ROUTE_EPOCH_STALE,
    REASON_ROUTE_TRANSITION_RECONCILE,
    REASON_UNMANAGED_FACT_WRITE_SKIPPED,
    REASON_UNMANAGED_FACT_WRITE_SUCCEEDED,
    REASON_UNMANAGED_NOT_ELIGIBLE,
    InventoryRouteSnapshot,
    RouteWriteGateDecision,
    RouteWriteGateInput,
    evaluate_unmanaged_fact_write_gate,
)
from app.modules.shop_runner.shop_wide_collection.unmanaged_orchestrator import (
    FullAdvStatFetcher,
    FullAdvStatWriter,
    UnmanagedAdvCollectOutcome,
    UnmanagedCollectTickResult,
    WbCampaignDiscovery,
    collect_unmanaged_campaign_advertising,
    select_unmanaged_full_adv_adv_ids,
    utc_now_naive,
)

# Static write-gate helpers re-exported for orchestrator wiring (tasks 3.7–3.8).
is_managed_collector_write_eligible = (
    CampaignCollectionRouteResolver.is_managed_collector_write_eligible
)
is_unmanaged_collector_write_eligible = (
    CampaignCollectionRouteResolver.is_unmanaged_collector_write_eligible
)
is_management_relationship_proven = (
    CampaignCollectionRouteResolver.is_management_relationship_proven
)

__all__ = [
    "COLLECTOR_ROUTE_TRANSITION_RECONCILE",
    "COLLECTOR_UNMANAGED_FULL_ADV",
    "ConnectHandoffTickResult",
    "DoneDisconnectHandoffResult",
    "FullAdvReadLatestClickHouse",
    "FullAdvReadLatestRow",
    "REASON_COLLECTOR_SOURCE_ERROR",
    "REASON_FACT_WRITE_ERROR",
    "REASON_MANAGED_LOADER_OWNERSHIP",
    "REASON_OWNERSHIP_MISMATCH",
    "REASON_ROUTE_EPOCH_STALE",
    "REASON_ROUTE_TRANSITION_RECONCILE",
    "REASON_UNKNOWN_CLUSTERS_OUTSIDE_MANAGED",
    "REASON_UNKNOWN_NOT_CLASSIFIED",
    "REASON_UNMANAGED_FACT_WRITE_SKIPPED",
    "REASON_UNMANAGED_FACT_WRITE_SUCCEEDED",
    "REASON_UNMANAGED_NOT_ELIGIBLE",
    "REASON_UNMANAGED_WB_DISCOVERY",
    "REASON_UNSUPPORTED_GRAIN",
    "RefusedOwnershipStabilityResult",
    "RouteTransitionReconcileOutcome",
    "CampaignCollectionGrain",
    "CampaignCollectionRouteResolver",
    "CampaignRouteDecision",
    "CampaignRouteKey",
    "CollectionRoute",
    "RouteResolverTickInput",
    "RouteResolverTickResult",
    "RouteWriteGateDecision",
    "RouteWriteGateInput",
    "ROUTE_EPOCH_SOURCE",
    "ROUTE_NOT_ASSIGNED",
    "DiscoveredWbCampaign",
    "FullAdvStatFetcher",
    "FullAdvStatWriter",
    "InventoryRouteSnapshot",
    "ShopCampaignAvailabilityClickHouse",
    "ShopCampaignAvailabilityWrite",
    "ShopCampaignInventoryClickHouse",
    "ShopCampaignInventoryRouteReader",
    "ShopCampaignInventoryWrite",
    "ShopWideCollectionDecision",
    "ShopWideCollectionMode",
    "ShopWideUnmanagedSliceNotReady",
    "UnmanagedAdvCollectOutcome",
    "UnmanagedCollectTickResult",
    "WbAdvertDiscoveryItem",
    "WbCampaignDiscovery",
    "append_shop_campaign_collection_availability",
    "apply_shop_wide_collection_gate",
    "build_managed_ownership_adv_ids",
    "collect_unmanaged_campaign_advertising",
    "connect_handoff_newly_managed_adv_ids",
    "count_raw_full_adv_grains",
    "discovered_campaign_from_advert",
    "done_handoff_transitioned_to_unmanaged",
    "evaluate_refused_disconnect_like_handoff",
    "evaluate_unmanaged_fact_write_gate",
    "evaluate_shop_wide_collection",
    "enforce_shop_wide_collection_fail_closed",
    "is_managed_collector_write_eligible",
    "is_management_relationship_proven",
    "is_unmanaged_collector_write_eligible",
    "load_inventory_route_snapshots",
    "load_read_latest_full_adv_facts",
    "map_wb_lifecycle",
    "read_latest_grain_keys",
    "reconcile_route_transition_read_latest",
    "resolve_connect_handoff_next_tick",
    "resolve_done_disconnect_handoff",
    "select_unmanaged_full_adv_adv_ids",
    "unmanaged_blocked_adv_ids_after_connect",
    "upsert_discovered_shop_campaign_inventory",
    "utc_now_naive",
]
