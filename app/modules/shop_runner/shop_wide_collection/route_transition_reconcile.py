"""Post-switch reconcile read-latest для dual-leg history (design §C, §F.2, task 7.5 / S22).

Spec: ``connected-shop-campaign-ad-data-collection``.
Debt: ``openspec/architectural-debt/TEMPORARY_DUAL_CAMPAIGN_COLLECTION.md``.

Periodic/reconcile entry для уже переключённого маршрута: сравнивает
read-latest grains dual-leg history, фиксирует расхождение в availability
с ``route_transition_reconcile``. Не пишет fact grain при stale epoch или
ownership mismatch. Availability **не** заменяет запрет записи fact grain.
"""

from __future__ import annotations

import logging
from collections.abc import Mapping, Sequence
from dataclasses import dataclass

from app.modules.shop_runner.shop_wide_collection.availability_append import (
    ShopCampaignAvailabilityClickHouse,
    append_shop_campaign_collection_availability,
)
from app.modules.shop_runner.shop_wide_collection.full_adv_read_latest import (
    FullAdvReadLatestClickHouse,
    FullAdvReadLatestRow,
    load_read_latest_full_adv_facts,
)
from app.modules.shop_runner.shop_wide_collection.inventory_route_read import (
    ShopCampaignInventoryRouteReader,
    load_inventory_route_snapshots,
)
from app.modules.shop_runner.shop_wide_collection.route_resolver import (
    CampaignRouteDecision,
)
from app.modules.shop_runner.shop_wide_collection.route_write_gate import (
    COLLECTOR_ROUTE_TRANSITION_RECONCILE,
    REASON_ROUTE_TRANSITION_RECONCILE,
    RouteWriteGateDecision,
    RouteWriteGateInput,
    evaluate_unmanaged_fact_write_gate,
)

logger = logging.getLogger(__name__)


@dataclass(frozen=True, slots=True)
class RouteTransitionReconcileOutcome:
    """Исход reconcile entry для одного ``adv_id`` (S22)."""

    adv_id: int
    dual_leg_detected: bool
    raw_grain_row_counts: tuple[tuple[int, str, int], ...]
    read_latest_grain_count: int
    availability_reason_code: str
    checked_route_version: int
    allow_fact_write: bool
    read_latest_rows: tuple[FullAdvReadLatestRow, ...]


def _normalize_full_adv_date_key(date_raw: object) -> str:
    """Привести date колонку raw full_adv row к ``YYYY-MM-DD`` строке."""
    if isinstance(date_raw, str):
        return date_raw
    if hasattr(date_raw, "strftime"):
        return date_raw.strftime("%Y-%m-%d")  # type: ignore[union-attr,no-any-return]
    raise TypeError("raw full_adv row date must be str or date-like")


def count_raw_full_adv_grains(
    raw_rows: Sequence[Mapping[str, object]],
) -> dict[tuple[int, str], int]:
    """Подсчёт сырых строк ``full_adv_wb_stat`` per ``(adv_id, date)`` grain.

    Dual-leg overlap оставляет несколько version rows на один grain; read-latest
    через ``argMax`` возвращает одну строку на grain.

    Args:
        raw_rows: in-memory или query mirror с ключами ``adv_id``, ``date``.

    Returns:
        Словарь ``(adv_id, date) → count raw rows``.
    """
    counts: dict[tuple[int, str], int] = {}
    for row in raw_rows:
        adv_id_raw = row.get("adv_id")
        date_raw = row.get("date")
        if isinstance(adv_id_raw, bool) or not isinstance(adv_id_raw, int):
            raise TypeError("raw full_adv row adv_id must be int")
        date_key = _normalize_full_adv_date_key(date_raw)
        key = (adv_id_raw, date_key)
        counts[key] = counts.get(key, 0) + 1
    return counts


def _dual_leg_grain_counts(
    raw_counts: Mapping[tuple[int, str], int],
    adv_id: int,
) -> tuple[tuple[int, str, int], ...]:
    return tuple(
        sorted(
            (grain_adv_id, date_key, count)
            for (grain_adv_id, date_key), count in raw_counts.items()
            if grain_adv_id == adv_id
        )
    )


def _evaluate_reconcile_write_gate(
    *,
    shop_id: str,
    adv_id: int,
    observed_route_version: int,
    current_inventory: object | None,
    route_decision: CampaignRouteDecision | None,
) -> RouteWriteGateDecision:
    """Gate reconcile path: stale epoch / ownership mismatch → no fact write."""
    from app.modules.shop_runner.shop_wide_collection.route_write_gate import (
        InventoryRouteSnapshot,
    )

    inventory_snapshot: InventoryRouteSnapshot | None
    if current_inventory is None:
        inventory_snapshot = None
    elif isinstance(current_inventory, InventoryRouteSnapshot):
        inventory_snapshot = current_inventory
    else:
        raise TypeError("current_inventory must be InventoryRouteSnapshot or None")

    _ = shop_id
    return evaluate_unmanaged_fact_write_gate(
        RouteWriteGateInput(
            shop_id=shop_id,
            adv_id=adv_id,
            observed_route_version=observed_route_version,
            current_inventory=inventory_snapshot,
            route_decision=route_decision,
        )
    )


async def reconcile_route_transition_read_latest(
    *,
    shop_id: str,
    adv_ids: Sequence[int],
    route_decisions: Mapping[int, CampaignRouteDecision | None],
    observed_route_versions: Mapping[int, int],
    inventory_reader: ShopCampaignInventoryRouteReader,
    full_adv_reader: FullAdvReadLatestClickHouse,
    availability_client: ShopCampaignAvailabilityClickHouse,
    raw_dual_leg_rows: Sequence[Mapping[str, object]] | None = None,
) -> tuple[RouteTransitionReconcileOutcome, ...]:
    """S22: reconcile entry для уже переключённого маршрута с dual-leg history.

    Сценарий **не** производит connect/disconnect — только сверка read-latest
    grains и diagnostic availability. Fact grain **не** пишется reconcile entry;
    gate фиксирует, что stale/mismatch collector тоже MUST NOT писать.

    Args:
        shop_id: магазин shop-runner.
        adv_ids: кампании с dual-leg history для reconcile.
        route_decisions: resolver decisions на текущий tick (per adv_id).
        observed_route_versions: epoch, наблюдённый на старте reconcile tick.
        inventory_reader: CH read ``shop_campaign_inventory.route_version``.
        full_adv_reader: CH read-latest ``full_adv_wb_stat``.
        availability_client: append-only availability writer.
        raw_dual_leg_rows: optional mirror сырых fact rows для detect dual-leg.

    Returns:
        Per-adv outcomes с reconcile availability и read-latest grain counts.
    """
    if shop_id == "":
        raise ValueError("shop_id must be a non-empty string")
    if not adv_ids:
        return ()

    raw_counts = (
        count_raw_full_adv_grains(raw_dual_leg_rows)
        if raw_dual_leg_rows is not None
        else {}
    )
    inventory_by_adv = await load_inventory_route_snapshots(
        inventory_reader,
        shop_id=shop_id,
        adv_ids=tuple(adv_ids),
    )
    read_latest_all = await load_read_latest_full_adv_facts(
        full_adv_reader,
        adv_ids=tuple(adv_ids),
    )
    read_latest_by_adv: dict[int, tuple[FullAdvReadLatestRow, ...]] = {}
    for row in read_latest_all:
        read_latest_by_adv.setdefault(row.adv_id, ())
        read_latest_by_adv[row.adv_id] = read_latest_by_adv[row.adv_id] + (row,)

    outcomes: list[RouteTransitionReconcileOutcome] = []
    for adv_id in sorted(adv_ids):
        route_decision = route_decisions.get(adv_id)
        observed_epoch = observed_route_versions.get(adv_id, 0)
        current_inventory = inventory_by_adv.get(adv_id)
        gate = _evaluate_reconcile_write_gate(
            shop_id=shop_id,
            adv_id=adv_id,
            observed_route_version=observed_epoch,
            current_inventory=current_inventory,
            route_decision=route_decision,
        )
        grain_counts = _dual_leg_grain_counts(raw_counts, adv_id)
        dual_leg = any(count > 1 for *_rest, count in grain_counts)
        adv_read_latest = read_latest_by_adv.get(adv_id, ())
        checked_version = (
            current_inventory.route_version
            if current_inventory is not None
            else gate.checked_route_version
        )
        availability_reason = (
            REASON_ROUTE_TRANSITION_RECONCILE
            if dual_leg
            else gate.reason_code
        )
        _ = await append_shop_campaign_collection_availability(
            availability_client,
            shop_id=shop_id,
            adv_id=adv_id,
            collector_id=COLLECTOR_ROUTE_TRANSITION_RECONCILE,
            reason_code=availability_reason,
            route_version=checked_version,
        )
        outcomes.append(
            RouteTransitionReconcileOutcome(
                adv_id=adv_id,
                dual_leg_detected=dual_leg,
                raw_grain_row_counts=grain_counts,
                read_latest_grain_count=len(adv_read_latest),
                availability_reason_code=availability_reason,
                checked_route_version=checked_version,
                allow_fact_write=gate.allow_fact_write,
                read_latest_rows=adv_read_latest,
            )
        )
        logger.info(
            "route_transition_reconcile shop_id=%s adv_id=%s dual_leg=%s "
            "read_latest_grains=%s checked_route_version=%s allow_fact_write=%s",
            shop_id,
            adv_id,
            dual_leg,
            len(adv_read_latest),
            checked_version,
            gate.allow_fact_write,
        )
    return tuple(outcomes)


def read_latest_grain_keys(
    rows: Sequence[FullAdvReadLatestRow],
) -> frozenset[tuple[int, str]]:
    """Уникальные ``(adv_id, date)`` keys read-latest — для assert no double-count."""
    return frozenset((row.adv_id, row.date) for row in rows)
