"""READ_ONLY: A1 direct + associated value review for MAX CPO decision inputs.

Собирает fullstats v3 nm-level attribution (direct vs associated carts/orders/GMV),
association matrix, supplier-order factual layer и PG AdvSetting contours.
Не меняет MAX CPO и не пишет в WB/DB.
"""

from __future__ import annotations

import argparse
import asyncio
import csv
import json
import os
import re
import sys
from collections import defaultdict
from datetime import date, datetime, time, timedelta, timezone
from pathlib import Path
from typing import Any
from zoneinfo import ZoneInfo

import dotenv

dotenv.load_dotenv()

from scripts import ch_a1_evidence as evidence
from scripts.a1_cpc_two_sku_safety_preflight import _bootstrap, _fetch_cards, _parse_nmids
from scripts.wb_a1_associated_conversions import (
    _config_rows,
    _derive,
    _jsonable,
    _nm_rows,
    _read_float,
    _read_int,
)
from scripts.wb_api_readonly_ops.collect.api_budget import ApiCallBudget
from scripts.wb_api_readonly_ops.collect.orders_sales import _paginate_supplier_rows

SHOP_ID = evidence.SHOP_ID
MSK = ZoneInfo("Europe/Moscow")

TARGET_NMIDS = (
    85970344,
    770642983,
    14166423,
    837395782,
    7974113,
    14824677,
    4491664,
    7974106,
    7839837,
    4491663,
    13713289,
    4491650,
    147281596,
)

HIGHLIGHT_NMIDS = {14824677, 837395782}

DIRECT_PRICE_CPO_BASELINE: dict[int, int] = {
    85970344: 423,
    770642983: 159,
    14166423: 104,
    837395782: 235,
    7974113: 287,
    14824677: 600,
    4491664: 600,
    7974106: 266,
    7839837: 94,
    4491663: 600,
    13713289: 86,
    4491650: 500,
    147281596: 259,
}

PG_ADV_FIELDS = [
    "id",
    "adv_id",
    "_search_adv_id",
    "name",
    "nmids",
    "aggressiveness",
    "strategy",
    "active_status",
    "bot_active",
    "auto_budget_daily_limit",
    "search_auto_budget_daily_limit",
    "use_common_budget",
    "common_budget_daily_limit",
    "target_price_for_order",
    "max_price_for_order",
    "max_cpc",
    "last_update",
]

WINDOWS = (3, 7, 14, 28)

METRIC_SEMANTICS = {
    "spend": {
        "source": "GET /adv/v3/fullstats",
        "field": "days[].sum",
        "note": "campaign-day spend; AdvSetting sums auto+search legs",
    },
    "views_clicks": {
        "source": "GET /adv/v3/fullstats",
        "field": "days[].views|clicks",
    },
    "carts": {
        "source": "GET /adv/v3/fullstats",
        "field": "days[].apps[].nms[].atbs",
        "direct_split": "ordered_nm_id == advertised_nm_id",
        "associated_split": "ordered_nm_id != advertised_nm_id within same campaign-day nm rows",
        "gap": "no separate WB associated-carts endpoint; split derived from nm rows only",
    },
    "orders_gmv": {
        "source": "GET /adv/v3/fullstats",
        "fields": "orders, sum_price on nm rows",
        "direct_split": "ordered_nm_id == advertised_nm_id",
        "associated_split": "ordered_nm_id != advertised_nm_id",
    },
    "supplier_orders": {
        "source": "GET /api/v1/supplier/orders",
        "fields": "totalPrice, gNumber — factual store layer, not ad-attributed",
    },
}


def _pg_db() -> str:
    return os.environ.get("POSTGRES_DBNAME") or "adv_updater"


def _msk_now() -> datetime:
    return datetime.now(timezone.utc).astimezone(MSK)


def _iso_msk(dt: datetime) -> str:
    return dt.astimezone(MSK).isoformat()


def _closed_end_day(now: datetime | None = None) -> date:
    return (now or _msk_now()).date() - timedelta(days=1)


def _closed_dates(closed_end: date, days: int) -> set[str]:
    start = closed_end - timedelta(days=days - 1)
    out: set[str] = set()
    d = start
    while d <= closed_end:
        out.add(d.isoformat())
        d += timedelta(days=1)
    return out


def _load_pg_adv(root: Path) -> list[dict[str, str]]:
    staging = root / "staging"
    staging.mkdir(parents=True, exist_ok=True)
    out = staging / "pg_adv.csv"
    cols = ", ".join(f"a.{c}" for c in PG_ADV_FIELDS)
    q = (
        f"SELECT {cols} FROM public.advsetting a "
        f"JOIN public.wbcabinet c ON a.wb_cabinet_id = c.id "
        f"WHERE c.shop_id = '{SHOP_ID}'"
    )
    st = evidence.run_pg_query(_pg_db(), q, out, root / "sql" / "pg_adv.sql", csv_output=True)
    if not st["success"]:
        raise RuntimeError(st["stderr"])
    with out.open(encoding="utf-8", newline="") as f:
        return list(csv.DictReader(f))


def _contours_for_targets(pg: list[dict[str, str]]) -> list[dict[str, Any]]:
    """AdvSetting rows: bot_active and intersecting any target nmID."""
    out: list[dict[str, Any]] = []
    targets = set(TARGET_NMIDS)
    for row in pg:
        nmids = _parse_nmids(row.get("nmids") or "")
        hit = [n for n in nmids if n in targets]
        if not hit:
            continue
        bot = str(row.get("bot_active")).lower() in ("true", "t", "1")
        out.append(
            {
                "adv_setting_id": _read_int(row, "id"),
                "auto_adv_id": _read_int(row, "adv_id"),
                "search_adv_id": _read_int(row, "_search_adv_id"),
                "nmids": nmids,
                "target_nmids_in_row": hit,
                "primary_nmid": hit[0] if len(hit) == 1 else None,
                "vendorCode": None,
                "name": row.get("name"),
                "aggressiveness": row.get("aggressiveness"),
                "bot_active": bot,
                "active_status": row.get("active_status"),
                "auto_budget_daily_limit": _read_int(row, "auto_budget_daily_limit"),
                "search_auto_budget_daily_limit": _read_int(
                    row, "search_auto_budget_daily_limit"
                ),
                "current_target_cpo": row.get("target_price_for_order"),
                "current_max_cpo": row.get("max_price_for_order"),
                "max_cpc": row.get("max_cpc"),
                "created_at": row.get("last_update"),
                "pg_row": row,
            }
        )
    return out


def _adv_ids_for_contours(contours: list[dict[str, Any]]) -> list[int]:
    ids: set[int] = set()
    for c in contours:
        if c["auto_adv_id"]:
            ids.add(c["auto_adv_id"])
        if c["search_adv_id"]:
            ids.add(c["search_adv_id"])
    return sorted(ids)


def _is_cancelled(row: dict[str, Any]) -> bool:
    return str(row.get("isCancel")).lower() in ("true", "1", "t")


def _g_key(row: dict[str, Any]) -> str:
    g = str(row.get("gNumber") or "").strip()
    return g if g else f"srid:{row.get('srid')}"


def _msk_dt(row: dict[str, Any]) -> datetime | None:
    raw = str(row.get("date") or row.get("lastChangeDate") or "").strip()
    if not raw or raw.startswith("0001"):
        return None
    try:
        if raw.endswith("Z"):
            dt = datetime.fromisoformat(raw.replace("Z", "+00:00"))
            return dt.astimezone(MSK)
        dt = datetime.fromisoformat(raw)
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=MSK)
        return dt.astimezone(MSK)
    except ValueError:
        return None


def _supplier_metrics(
    orders: list[dict[str, Any]], nmid: int, closed_end: date, days: int
) -> dict[str, Any]:
    dates = _closed_dates(closed_end, days)
    rows = [
        r
        for r in orders
        if _read_int(r, "nmId", "nm_id", "nmid") == nmid
        and not _is_cancelled(r)
        and (_msk_dt(r) or datetime.min.replace(tzinfo=MSK)).date().isoformat() in dates
    ]
    groups: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for r in rows:
        groups[_g_key(r)].append(r)
    return {
        "PURCHASE_EVENTS": len(groups),
        "UNITS": len(rows),
        "TOTAL_PRICE_VALUE": round(sum(_read_float(r, "totalPrice") for r in rows), 2),
        "window_closed_days": days,
    }


def _safe_div(num: float, den: float) -> float | None:
    if den <= 0:
        return None
    return round(num / den, 6)


def _campaign_day_spend(
    day_rows: list[dict[str, Any]], advert_ids: set[int], dates: set[str]
) -> float:
    return round(
        sum(
            r["day_spend"]
            for r in day_rows
            if r["advert_id"] in advert_ids and r["date"] in dates
        ),
        2,
    )


def _split_nm_metrics(
    nm_rows: list[dict[str, Any]],
    day_rows: list[dict[str, Any]],
    advert_ids: set[int],
    advertised_nmid: int,
    dates: set[str],
) -> dict[str, Any]:
    """Direct vs associated from nm rows for one advertised SKU."""
    rows = [r for r in nm_rows if r["advert_id"] in advert_ids and r["date"] in dates]
    spend_campaign_day = _campaign_day_spend(day_rows, advert_ids, dates)
    views = sum(r["views"] for r in rows)
    clicks = sum(r["clicks"] for r in rows)
    direct = [r for r in rows if r["ordered_nm_id"] == advertised_nmid]
    assoc = [r for r in rows if r["ordered_nm_id"] != advertised_nmid]
    d_carts = sum(r["atbs"] for r in direct)
    a_carts = sum(r["atbs"] for r in assoc)
    t_carts = d_carts + a_carts
    d_orders = sum(r["orders"] for r in direct)
    a_orders = sum(r["orders"] for r in assoc)
    t_orders = d_orders + a_orders
    d_gmv = sum(r["sum_price"] for r in direct)
    a_gmv = sum(r["sum_price"] for r in assoc)
    t_gmv = d_gmv + a_gmv
    return {
        "spend": spend_campaign_day,
        "views": views,
        "clicks": clicks,
        "CTR": _safe_div(clicks, views),
        "CPC": _safe_div(spend_campaign_day, clicks),
        "direct_carts": d_carts,
        "associated_carts": a_carts,
        "total_carts": t_carts,
        "direct_orders": d_orders,
        "associated_orders": a_orders,
        "total_orders": t_orders,
        "direct_gmv": round(d_gmv, 2),
        "associated_gmv": round(a_gmv, 2),
        "total_gmv": round(t_gmv, 2),
        "ASSOCIATED_CART_SHARE": _safe_div(a_carts, t_carts),
        "ASSOCIATED_GMV_SHARE": _safe_div(a_gmv, t_gmv) if t_gmv else None,
        "ASSOCIATED_ORDER_SHARE": _safe_div(a_orders, t_orders) if t_orders else None,
        "SPEND_PER_DIRECT_CART": _safe_div(spend_campaign_day, d_carts),
        "SPEND_PER_TOTAL_CART": _safe_div(spend_campaign_day, t_carts),
        "direct_cart_to_order_conv": _safe_div(d_orders, d_carts),
        "associated_cart_to_order_conv": _safe_div(a_orders, a_carts),
        "DIRECT_AD_DRR": _safe_div(spend_campaign_day, d_gmv),
        "TOTAL_ATTRIBUTED_DRR": _safe_div(spend_campaign_day, t_gmv),
        "DIRECT_CPO": _safe_div(spend_campaign_day, d_orders),
        "TOTAL_ATTRIBUTED_CPO": _safe_div(spend_campaign_day, t_orders),
    }


def _edge_rows(
    nm_rows: list[dict[str, Any]],
    advert_ids: set[int],
    advertised_nmid: int,
    dates: set[str],
    card_index: dict[int, dict[str, Any]],
) -> list[dict[str, Any]]:
    grouped: dict[int, dict[str, Any]] = defaultdict(
        lambda: {"associated_carts": 0, "associated_orders": 0, "associated_gmv": 0.0}
    )
    for r in nm_rows:
        if r["advert_id"] not in advert_ids or r["date"] not in dates:
            continue
        purchased = r["ordered_nm_id"]
        if purchased == advertised_nmid:
            edge_type = "SELF"
        else:
            edge_type = "ASSOCIATED"
        g = grouped[purchased]
        g["edge_type"] = edge_type
        g["associated_carts"] += r["atbs"]
        g["associated_orders"] += r["orders"]
        g["associated_gmv"] += r["sum_price"]
    out: list[dict[str, Any]] = []
    for purchased, m in sorted(grouped.items()):
        card = card_index.get(purchased, {})
        out.append(
            {
                "ADVERTISED_NMID": advertised_nmid,
                "PURCHASED_OR_CARTED_NMID": purchased,
                "edge_type": m.get("edge_type"),
                "associated_carts": m["associated_carts"],
                "associated_orders": m["associated_orders"],
                "associated_GMV": round(m["associated_gmv"], 2),
                "vendorCode": card.get("vendorCode"),
                "title": card.get("title") or card.get("name"),
                "subjectID": card.get("subjectID"),
                "subjectName": card.get("subjectName"),
            }
        )
    return out


def _daily_rows(
    nm_rows: list[dict[str, Any]],
    day_rows: list[dict[str, Any]],
    advert_ids: set[int],
    advertised_nmid: int,
    closed_end: date,
    days: int = 7,
) -> list[dict[str, Any]]:
    dates = sorted(_closed_dates(closed_end, days))
    out: list[dict[str, Any]] = []
    day_lookup = {(r["advert_id"], r["date"]): r for r in day_rows}
    for d in dates:
        m = _split_nm_metrics(nm_rows, day_rows, advert_ids, advertised_nmid, {d})
        spend_alt = sum(
            day_lookup.get((aid, d), {}).get("day_spend", 0.0) for aid in advert_ids
        )
        if spend_alt and not m["spend"]:
            m["spend"] = round(spend_alt, 2)
        out.append({"date": d, **m})
    return out


def _decision_inputs(metrics_by_window: dict[int, dict[str, Any]]) -> dict[str, Any]:
    out: dict[str, Any] = {}
    for w in (7, 14, 28):
        m = metrics_by_window.get(w, {})
        out[f"DIRECT_AD_DRR_{w}D"] = m.get("DIRECT_AD_DRR")
        out[f"TOTAL_ATTRIBUTED_DRR_{w}D"] = m.get("TOTAL_ATTRIBUTED_DRR")
        out[f"DIRECT_CARTS_{w}D"] = m.get("direct_carts")
        out[f"ASSOCIATED_CARTS_{w}D"] = m.get("associated_carts")
        out[f"DIRECT_ORDERS_{w}D"] = m.get("direct_orders")
        out[f"ASSOCIATED_ORDERS_{w}D"] = m.get("associated_orders")
        out[f"DIRECT_GMV_{w}D"] = m.get("direct_gmv")
        out[f"ASSOCIATED_GMV_{w}D"] = m.get("associated_gmv")
    return out


async def _collect_wb(
    adv_ids: list[int],
    closed_end: date,
) -> tuple[list[dict[str, Any]], list[dict[str, Any]], dict[int, set[int]], list[str]]:
    from app.core.di.app_container import AppContainer
    from app.core.di.di_manager import DIManager
    from app.core.mp.wb.api.adapter.promotion_client.fullstats.chunked import (
        run_chunked_single_range,
    )

    gaps: list[str] = []
    begin = closed_end - timedelta(days=27)
    raw_items: list[dict[str, Any]] = []
    config_rows: list[dict[str, Any]] = []
    promoted: dict[int, set[int]] = {}

    async with await DIManager.create(AppContainer) as container:  # type: ignore[attr-defined]
        factory = (
            container.module_resources.wb_manager_hub_factory_container.wb_manager_hub_factory()
        )
        hub = factory.get_wb_manager_hub(SHOP_ID)
        client = hub.wb_data_manager.promotion_manager._client
        products = hub.wb_data_manager.products_manager

        all_configs = await client.campaigns_info_v2_adapter.get_all_campaigns()
        config_rows, promoted_all = _config_rows(
            [_jsonable(x.to_dict()) for x in all_configs]
        )
        promoted = {k: v for k, v in promoted_all.items() if k in adv_ids}
        missing = [i for i in adv_ids if i not in promoted]
        if missing:
            gaps.append(f"campaign_config_missing_for_adv_ids={missing[:20]}")

        adapter = client.fullstats_adapter

        async def fetcher(chunk: list[int], b: date, e: date) -> list[Any]:
            return await adapter._request_chunk(chunk, b, e)

        items = await run_chunked_single_range(adv_ids, begin, closed_end, fetcher)
        for item in items:
            raw_items.append(_jsonable(item.to_dict()))

        reports_manager = getattr(hub.wb_data_manager, "reports_manager", None)
        budget = ApiCallBudget(max_seconds=900.0, max_api_calls=1200)
        date_from = (closed_end - timedelta(days=35)).isoformat()

        async def fetch_orders(df: str) -> list[object]:
            if reports_manager is not None:
                return list(
                    await reports_manager.get_supplier_orders(date_from=df, flag=0) or []
                )
            return list(
                await hub.wb_data_manager.get_supplier_orders(date_from=df, flag=0) or []
            )

        orders_result = await _paginate_supplier_rows(
            fetch=fetch_orders,
            initial_date_from=date_from,
            budget=budget,
            max_pages=1200,
        )
        orders = [r for r in orders_result.rows if isinstance(r, dict)]

        cards = await _fetch_cards(products, set(TARGET_NMIDS))
        card_index: dict[int, dict[str, Any]] = {}
        for nmid, c in cards.items():
            card_index[nmid] = c
        for nmid in TARGET_NMIDS:
            if nmid not in card_index:
                extra = await _fetch_cards(products, {nmid})
                card_index.update(extra)

    return raw_items, orders, promoted, gaps, card_index, config_rows


async def run_review(root: Path, pg: list[dict[str, str]]) -> dict[str, Any]:
    checked_at = _msk_now()
    closed_end = _closed_end_day(checked_at)
    gaps: list[str] = []

    contours = _contours_for_targets(pg)
    if not contours:
        gaps.append("no_advsetting_rows_for_target_nmids")

    adv_ids = _adv_ids_for_contours(contours)
    raw_items, orders, promoted, wb_gaps, card_index, _ = await _collect_wb(
        adv_ids, closed_end
    )
    gaps.extend(wb_gaps)

    nm_rows, day_rows = _nm_rows(raw_items)
    _, _, _, reconciliation = _derive(nm_rows, day_rows, promoted)
    if not reconciliation.get("pass"):
        gaps.append(
            f"fullstats_nm_day_reconciliation_failed_days={reconciliation.get('failed_days')}"
        )

    nmid_to_contours: dict[int, list[dict[str, Any]]] = defaultdict(list)
    for c in contours:
        for n in c["target_nmids_in_row"]:
            if n in TARGET_NMIDS:
                nmid_to_contours[n].append(c)

    association_matrix: dict[str, list[dict[str, Any]]] = {}
    summary_rows: list[dict[str, Any]] = []

    for nmid in TARGET_NMIDS:
        related = nmid_to_contours.get(nmid, [])
        advert_ids = set()
        for c in related:
            if c["auto_adv_id"]:
                advert_ids.add(c["auto_adv_id"])
            if c["search_adv_id"]:
                advert_ids.add(c["search_adv_id"])
        if not advert_ids:
            gaps.append(f"no_campaign_ids_for_nmid_{nmid}")

        metrics_by_window = {
            w: _split_nm_metrics(
                nm_rows, day_rows, advert_ids, nmid, _closed_dates(closed_end, w)
            )
            for w in WINDOWS
        }
        daily = _daily_rows(nm_rows, day_rows, advert_ids, nmid, closed_end, 7)

        matrix: dict[str, list[dict[str, Any]]] = {}
        for w in (7, 14, 28):
            matrix[f"{w}d"] = _edge_rows(
                nm_rows,
                advert_ids,
                nmid,
                _closed_dates(closed_end, w),
                card_index,
            )
        association_matrix[str(nmid)] = matrix

        supplier_layers = {
            f"{w}d": _supplier_metrics(orders, nmid, closed_end, w) for w in WINDOWS
        }

        since_launch: dict[str, Any] | None = None
        if nmid == 14824677:
            launch_dates: list[str] = []
            for c in related:
                created = str(c.get("created_at") or "")[:10]
                if created:
                    launch_dates.append(created)
            for aid in advert_ids:
                for cfg in raw_items:
                    if _read_int(cfg, "advertId", "advert_id") != aid:
                        continue
            since_launch = {
                "SINCE_LAUNCH": "from_advsetting_created_at",
                "launch_dates_pg": sorted(set(launch_dates)),
                "metrics": _split_nm_metrics(
                    nm_rows,
                    day_rows,
                    advert_ids,
                    nmid,
                    {
                        d
                        for d in {r["date"] for r in nm_rows if r["advert_id"] in advert_ids}
                        if d >= (min(launch_dates) if launch_dates else "2026-09-01")
                    },
                )
                if launch_dates
                else {"GAP": "launch_date_unknown"},
            }

        primary = related[0] if related else {}
        card = card_index.get(nmid, {})
        summary_rows.append(
            {
                "adv_setting_id": primary.get("adv_setting_id"),
                "auto_adv_id": primary.get("auto_adv_id"),
                "search_adv_id": primary.get("search_adv_id"),
                "nmID": nmid,
                "vendorCode": card.get("vendorCode"),
                "current_target_cpo": primary.get("current_target_cpo"),
                "current_max_cpo": primary.get("current_max_cpo"),
                "auto_budget_daily_limit": primary.get("auto_budget_daily_limit"),
                "search_budget_daily_limit": primary.get(
                    "search_auto_budget_daily_limit"
                ),
                "aggressiveness": primary.get("aggressiveness"),
                "bot_active": primary.get("bot_active"),
                "contour_count": len(related),
                "advert_ids": sorted(advert_ids),
                "DIRECT_PRICE_CPO_BASELINE": DIRECT_PRICE_CPO_BASELINE.get(nmid),
                "periods": metrics_by_window,
                "daily_last_7_closed_days": daily,
                "supplier_orders_factual": supplier_layers,
                "since_launch": since_launch,
                "decision_inputs": {
                    "DIRECT_PRICE_CPO_BASELINE": DIRECT_PRICE_CPO_BASELINE.get(nmid),
                    "CURRENT_MAX_CPO": primary.get("current_max_cpo"),
                    ** _decision_inputs(metrics_by_window),
                },
                "data_notes": {
                    "cart_split": METRIC_SEMANTICS["carts"],
                    "not_computed": "ASSOCIATED != TOTAL-DIRECT unless both from nm-row split",
                },
            }
        )

    m7 = {r["nmID"]: r["periods"][7] for r in summary_rows}
    top_assoc_carts = sorted(
        summary_rows,
        key=lambda r: m7.get(r["nmID"], {}).get("associated_carts", 0),
        reverse=True,
    )[:5]
    top_assoc_gmv = sorted(
        summary_rows,
        key=lambda r: m7.get(r["nmID"], {}).get("associated_gmv", 0.0),
        reverse=True,
    )[:5]
    receivers: dict[int, float] = defaultdict(float)
    for nmid in TARGET_NMIDS:
        for edge in association_matrix.get(str(nmid), {}).get("7d", []):
            if edge.get("edge_type") == "ASSOCIATED":
                receivers[edge["PURCHASED_OR_CARTED_NMID"]] += edge["associated_GMV"]
    top_receivers = sorted(receivers.items(), key=lambda x: x[1], reverse=True)[:10]

    direct_only = [
        r["nmID"]
        for r in summary_rows
        if (m7.get(r["nmID"], {}).get("ASSOCIATED_ORDER_SHARE") or 0) < 0.05
        and (m7.get(r["nmID"], {}).get("associated_orders") or 0) == 0
    ]
    no_cart = [
        r["nmID"]
        for r in summary_rows
        if (m7.get(r["nmID"], {}).get("total_carts") or 0) == 0
    ]

    data_gaps = list(gaps)
    data_gaps.append(
        "auto_plus_search_spend_may_double_count_if_WB_attributes_same_event_to_both_legs"
    )
    data_gaps.append(
        "cart_to_order_conversion_uses_same_fullstats_nm_attribution_model_for_both_numerator_and_denominator"
    )
    if any(len(c["target_nmids_in_row"]) > 1 for c in contours):
        data_gaps.append("multi_nmid_advsetting_shared_campaign_spend_not_allocated")

    integrity = "PASS" if reconciliation.get("pass") else "PARTIAL"
    if gaps:
        integrity = "PARTIAL"

    return {
        "STATUS": "OK" if summary_rows else "GAP",
        "INTEGRITY": integrity,
        "CHECKED_AT_MSK": _iso_msk(checked_at),
        "CLOSED_DAY_END": closed_end.isoformat(),
        "SUMMARY_TABLE": summary_rows,
        "ASSOCIATION_MATRIX": association_matrix,
        "TOP_TRAFFIC_DONORS_BY_ASSOC_CARTS": [
            {"nmID": r["nmID"], "associated_carts_7d": m7[r["nmID"]]["associated_carts"]}
            for r in top_assoc_carts
        ],
        "TOP_TRAFFIC_DONORS_BY_ASSOC_GMV": [
            {"nmID": r["nmID"], "associated_gmv_7d": m7[r["nmID"]]["associated_gmv"]}
            for r in top_assoc_gmv
        ],
        "TOP_RECEIVER_NMIDS": [
            {"nmID": n, "associated_gmv_7d_inbound": round(v, 2)} for n, v in top_receivers
        ],
        "DIRECT_ONLY_OR_NEAR_DIRECT_SKUS": direct_only,
        "NO_CART_SIGNAL_SKUS": no_cart,
        "DATA_SEMANTICS_GAPS": data_gaps,
        "METRIC_SEMANTICS": METRIC_SEMANTICS,
        "fullstats_reconciliation": reconciliation,
        "highlight": {
            str(n): next((r for r in summary_rows if r["nmID"] == n), {})
            for n in HIGHLIGHT_NMIDS
        },
        "MAX_CPO_CHANGES_EXECUTED": "NO",
        "WB_API_WRITES": 0,
        "DB_WRITES": 0,
        "READ_ONLY": "CONFIRMED",
    }


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--output", default="")
    ap.add_argument("--output-dir", default=".tmp/a1_direct_assoc_value_review")
    args = ap.parse_args(argv)
    root = Path(args.output_dir).resolve()
    root.mkdir(parents=True, exist_ok=True)
    (root / "sql").mkdir(exist_ok=True)
    _bootstrap()
    pg = _load_pg_adv(root)

    payload = asyncio.run(run_review(root, pg))

    if args.output:
        Path(args.output).write_text(
            json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8"
        )
    out = root / "a1_direct_associated_value_review.json"
    out.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(payload, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
