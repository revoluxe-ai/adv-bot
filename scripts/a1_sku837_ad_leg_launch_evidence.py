"""READ_ONLY: A1 evidence — Unified/Auto vs Search leg для nmID 837395782.

Category-first sample (exact subject / related / store-wide), campaign leg mapping,
fullstats economics, placement breakdown. Без advertising writes.
"""

from __future__ import annotations

import argparse
import asyncio
import json
import os
import re
import sys
from collections import defaultdict
from datetime import date, datetime, timedelta, timezone
from pathlib import Path
from typing import Any
from zoneinfo import ZoneInfo

import dotenv

dotenv.load_dotenv()

from scripts import ch_a1_evidence as evidence
from scripts.wb_a1_associated_conversions import (
    _config_rows,
    _jsonable,
    _nm_rows,
    _read_float,
    _read_int,
)
from scripts.wb_api_readonly_ops.collect.ads import _flatten_fullstats
from scripts.wb_api_readonly_ops.collect.api_budget import ApiCallBudget
from scripts.wb_api_readonly_ops.collect.jsonable import jsonable
from scripts.wb_api_readonly_ops.collect.orders_sales import _paginate_supplier_rows

SHOP_ID = "5339e9ad-cbfe-50fc-8d77-b9f337a80417"
MSK = ZoneInfo("Europe/Moscow")
PACKAGE = "A1-SKU837-AD-LEG-LAUNCH-EVIDENCE"

TARGET_NMID = 837395782
TARGET_SUBJECT_ID = 4069
TARGET_SUBJECT_NAME = "Подушки для растяжки"
NEW_UNIFIED_ADV = 39900256
NEW_SEARCH_ADV = 39900211

CLOSED_THROUGH = date(2026, 9, 1)
PERIOD_DAYS = 28
PERIOD_TO = CLOSED_THROUGH
PERIOD_FROM = PERIOD_TO - timedelta(days=PERIOD_DAYS - 1)

RELATED_KEYWORDS = (
    "йог",
    "болстер",
    "валик",
    "подуш",
    "фитнес",
    "растяж",
    "массаж",
    "gym",
    "stretch",
    "yoga",
    "roller",
    "bolster",
    "pillow",
)

PG_ADV_FIELDS = [
    "id", "adv_id", "_search_adv_id", "type", "name", "nmids", "active_status",
    "wb_bid_type", "wb_placement_search", "wb_placement_recommendations",
]

NAME_SEARCH = re.compile(r"<!-\[(\d+)\]-!>")


def _msk_now() -> datetime:
    return datetime.now(timezone.utc).astimezone(MSK)


def _pg_db() -> str:
    return os.environ.get("POSTGRES_DBNAME") or "adv_updater"


def _bootstrap() -> None:
    u, p = os.environ.get("POSTGRES_USER"), os.environ.get("POSTGRES_PASSWORD")
    if u and p:
        evidence._PG_CREDENTIALS = u, p
    h = os.environ.get("POSTGRES_MASTER_HOST") or os.environ.get("POSTGRES_REPLICA_HOST")
    if h:
        evidence.PG_EXTERNAL_HOST = h
    pt = os.environ.get("POSTGRES_PORT")
    if pt:
        evidence.PG_EXTERNAL_PORT = int(pt)


def _parse_nmids(raw: str) -> list[int]:
    out: list[int] = []
    for part in re.split(r"[,;\s]+", str(raw or "")):
        part = part.strip().strip("[]")
        if part.isdigit():
            out.append(int(part))
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
    import csv

    with out.open(encoding="utf-8", newline="") as f:
        return list(csv.DictReader(f))


def _load_all_wbcards(root: Path) -> dict[int, dict[str, Any]]:
    path = root / "staging" / "wbcard_all.csv"
    q = (
        "SELECT w.nmid, w.name, w.wb_category_id, w.json FROM public.wbcard w "
        f"JOIN public.wbcabinet c ON w.wb_cabinet_id = c.id WHERE c.shop_id = '{SHOP_ID}'"
    )
    st = evidence.run_pg_query(_pg_db(), q, path, root / "sql" / "wbcard_all.sql", csv_output=True)
    out: dict[int, dict[str, Any]] = {}
    if not st["success"]:
        return out
    import csv

    with path.open(encoding="utf-8", newline="") as f:
        for row in csv.DictReader(f):
            nmid = _read_int(row, "nmid")
            if not nmid:
                continue
            raw_json: dict[str, Any] = {}
            try:
                parsed = json.loads(row.get("json") or "{}")
                if isinstance(parsed, dict):
                    raw_json = parsed
            except (TypeError, json.JSONDecodeError):
                pass
            subject_id = _read_int(raw_json, "subjectID", "subjectId") or _read_int(
                row, "wb_category_id",
            )
            subject = str(raw_json.get("subjectName") or row.get("name") or "")
            parent = str(raw_json.get("parentName") or "")
            out[nmid] = {
                "nmID": nmid,
                "vendorCode": raw_json.get("vendorCode"),
                "subjectID": subject_id,
                "subjectName": subject,
                "parentName": parent,
                "title": raw_json.get("title") or row.get("name"),
            }
    return out


def _in_period(day: str) -> bool:
    try:
        d = date.fromisoformat(day[:10])
    except ValueError:
        return False
    return PERIOD_FROM <= d <= PERIOD_TO


def _is_cancelled(row: dict[str, Any]) -> bool:
    return str(row.get("isCancel")).lower() in ("true", "1", "t")


def _g_key(row: dict[str, Any]) -> str:
    g = str(row.get("gNumber") or "").strip()
    return g if g else f"srid:{row.get('srid')}"


def _order_day(row: dict[str, Any]) -> str:
    return str(row.get("date") or row.get("lastChangeDate") or "")[:10]


def _event_metrics(groups: dict[str, list[dict[str, Any]]]) -> dict[str, Any]:
    events = len(groups)
    units = sum(len(v) for v in groups.values())
    bulk_units = sum(len(v) for v in groups.values() if len(v) >= 2)
    total_price = round(sum(_read_float(r, "totalPrice") for rs in groups.values() for r in rs), 2)
    return {
        "PURCHASE_EVENTS": events,
        "UNITS": units,
        "TOTAL_PRICE_VALUE": total_price,
        "bulk_unit_share_pct": round(100 * bulk_units / units, 2) if units else 0,
    }


def _classify_samples(wbcards: dict[int, dict[str, Any]]) -> dict[str, Any]:
    exact: list[int] = []
    related: list[int] = []
    for nmid, card in wbcards.items():
        sid = card.get("subjectID")
        subj = str(card.get("subjectName") or "").lower()
        parent = str(card.get("parentName") or "").lower()
        blob = f"{subj} {parent}"
        if sid == TARGET_SUBJECT_ID:
            exact.append(nmid)
        elif any(k in blob for k in RELATED_KEYWORDS):
            related.append(nmid)
    related_only = sorted(set(related) - set(exact))
    store_wide = sorted(wbcards)
    return {
        "EXACT_SUBJECT": {
            "level": "EXACT_SUBJECT",
            "subjectID": TARGET_SUBJECT_ID,
            "subjectName": TARGET_SUBJECT_NAME,
            "nmids": sorted(exact),
            "nmids_count": len(exact),
        },
        "RELATED_CATEGORY": {
            "level": "RELATED_CATEGORY",
            "rule": "subject keyword match (йога/болстер/валик/подушк/фитнес/растяж/…)",
            "nmids": related_only,
            "nmids_count": len(related_only),
            "includes_exact_subject": False,
        },
        "STORE_WIDE": {
            "level": "STORE_WIDE",
            "nmids": store_wide,
            "nmids_count": len(store_wide),
        },
    }


def _pg_index(pg: list[dict[str, str]]) -> dict[int, dict[str, Any]]:
    idx: dict[int, dict[str, Any]] = {}
    for row in pg:
        adv = _read_int(row, "adv_id")
        if not adv:
            continue
        idx[adv] = {
            "adv_id": adv,
            "search_adv_id": _read_int(row, "_search_adv_id"),
            "name": row.get("name") or "",
            "nmids": _parse_nmids(row.get("nmids") or ""),
            "wb_bid_type": row.get("wb_bid_type"),
            "type": row.get("type"),
        }
    return idx


def _leg_from_campaign(raw: dict[str, Any], pg_row: dict[str, Any] | None) -> str:
    """Unified/Auto vs manual Search по bid_type WB v2 (не по имени)."""
    bid = str(raw.get("bid_type") or (pg_row or {}).get("wb_bid_type") or "").lower()
    if bid == "unified":
        return "UNIFIED_AUTO"
    if bid == "manual":
        return "SEARCH"
    settings = raw.get("settings") if isinstance(raw.get("settings"), dict) else {}
    placements = settings.get("placements") if isinstance(settings.get("placements"), dict) else {}
    if placements.get("search") and not placements.get("recommendations"):
        return "SEARCH"
    if placements.get("recommendations") and not placements.get("search"):
        return "UNIFIED_AUTO"
    return "UNCLASSIFIED"


def _campaign_maps(
    campaigns: list[dict[str, Any]],
    pg_idx: dict[int, dict[str, Any]],
) -> tuple[dict[int, dict[str, Any]], dict[int, set[int]]]:
    inv: dict[int, dict[str, Any]] = {}
    adv_nm: dict[int, set[int]] = defaultdict(set)
    for raw in campaigns:
        adv_id = _read_int(raw, "id", "advertId")
        if not adv_id:
            continue
        pg_row = pg_idx.get(adv_id, {})
        nm_settings = raw.get("nm_settings") or raw.get("nmSettings") or []
        nmids: set[int] = set()
        if isinstance(nm_settings, list):
            for nm in nm_settings:
                if isinstance(nm, dict):
                    nid = _read_int(nm, "nm_id", "nmId", "nmID")
                    if nid:
                        nmids.add(nid)
        if not nmids:
            nmids.update(pg_row.get("nmids") or [])
        adv_nm[adv_id] = nmids
        settings = raw.get("settings") if isinstance(raw.get("settings"), dict) else {}
        inv[adv_id] = {
            "adv_id": adv_id,
            "leg": _leg_from_campaign(raw, pg_row),
            "bid_type": raw.get("bid_type") or pg_row.get("wb_bid_type"),
            "payment_type": settings.get("payment_type") or settings.get("paymentType"),
            "placements": settings.get("placements"),
            "wb_status": raw.get("status"),
            "nmids": sorted(nmids),
            "search_adv_id": pg_row.get("search_adv_id"),
            "name": settings.get("name") or pg_row.get("name"),
        }
    return inv, dict(adv_nm)


def _empty_metrics() -> dict[str, Any]:
    return {
        "spend_rub": 0.0,
        "views": 0,
        "clicks": 0,
        "attributed_orders": 0,
        "attributed_gmv_rub": 0.0,
        "atbs": 0,
        "campaign_ids": set(),
        "sku_ids": set(),
    }


def _finalize_metrics(m: dict[str, Any], total_spend: float) -> dict[str, Any]:
    spend = round(float(m["spend_rub"]), 2)
    clicks = int(m["clicks"])
    views = int(m["views"])
    orders = int(m["attributed_orders"])
    gmv = round(float(m["attributed_gmv_rub"]), 2)
    out = {
        "spend_rub": spend,
        "views": views,
        "clicks": clicks,
        "CTR_pct": round(100 * clicks / views, 3) if views else None,
        "CPC_rub": round(spend / clicks, 2) if clicks else None,
        "attributed_orders": orders,
        "attributed_gmv_rub": gmv,
        "atbs": int(m.get("atbs") or 0),
        "CLICKS_PER_100_RUB": round(100 * clicks / spend, 3) if spend else None,
        "ATTR_ORDERS_PER_1000_RUB": round(1000 * orders / spend, 3) if spend else None,
        "ATTR_GMV_PER_RUB": round(gmv / spend, 3) if spend else None,
        "SPEND_SHARE": round(spend / total_spend, 4) if total_spend else None,
        "campaign_count": len(m["campaign_ids"]),
        "sku_count": len(m["sku_ids"]),
        "campaign_ids": sorted(m["campaign_ids"]),
    }
    return out


def _aggregate_leg_metrics(
    sample_nmids: set[int],
    inventory: dict[int, dict[str, Any]],
    day_rows: list[dict[str, Any]],
    nm_rows: list[dict[str, Any]],
) -> tuple[dict[str, Any], dict[str, Any], float]:
    """Агрегировать метрики по leg для sample SKU."""
    relevant_adv: dict[int, str] = {}
    for adv_id, inv in inventory.items():
        if sample_nmids.intersection(inv.get("nmids") or []):
            leg = inv.get("leg") or "UNCLASSIFIED"
            relevant_adv[adv_id] = leg

    legs = {
        "UNIFIED_AUTO": _empty_metrics(),
        "SEARCH": _empty_metrics(),
        "UNCLASSIFIED": _empty_metrics(),
    }
    placement: dict[str, dict[str, Any]] = defaultdict(_empty_metrics)

    for row in day_rows:
        if not _in_period(row.get("date", "")):
            continue
        adv_id = _read_int(row, "advert_id")
        if adv_id not in relevant_adv:
            continue
        leg = relevant_adv[adv_id]
        bucket = legs.setdefault(leg, _empty_metrics())
        bucket["spend_rub"] += _read_float(row, "day_spend")
        bucket["clicks"] += _read_int(row, "day_clicks")
        bucket["views"] += _read_int(row, "day_views")
        bucket["attributed_orders"] += _read_int(row, "day_orders")
        bucket["attributed_gmv_rub"] += _read_float(row, "day_sum_price")
        bucket["campaign_ids"].add(adv_id)
        bucket["sku_ids"].update(
            sample_nmids.intersection(inventory.get(adv_id, {}).get("nmids") or []),
        )

    for row in nm_rows:
        if not _in_period(row.get("date", "")):
            continue
        adv_id = _read_int(row, "advert_id")
        nmid = _read_int(row, "ordered_nm_id")
        if adv_id not in relevant_adv or nmid not in sample_nmids:
            continue
        atbs = _read_int(row, "atbs")
        leg = relevant_adv[adv_id]
        legs[leg]["atbs"] += atbs
        if relevant_adv[adv_id] == "UNIFIED_AUTO":
            app_type = str(row.get("app_type") or "unknown")
            placement[app_type]["atbs"] += atbs
            placement[app_type]["spend_rub"] += _read_float(row, "spend")
            placement[app_type]["clicks"] += _read_int(row, "clicks")
            placement[app_type]["views"] += _read_int(row, "views")
            placement[app_type]["attributed_orders"] += _read_int(row, "orders")
            placement[app_type]["attributed_gmv_rub"] += _read_float(row, "sum_price")

    total_spend = sum(legs[k]["spend_rub"] for k in legs)
    unified = _finalize_metrics(legs["UNIFIED_AUTO"], total_spend)
    search = _finalize_metrics(legs["SEARCH"], total_spend)
    uncl = _finalize_metrics(legs["UNCLASSIFIED"], total_spend)

    placement_out: dict[str, Any] = {}
    for app_type, pm in placement.items():
        placement_out[app_type] = _finalize_metrics(pm, unified.get("spend_rub") or 0)

    return (
        {"UNIFIED_AUTO": unified, "SEARCH": search, "UNCLASSIFIED": uncl},
        placement_out,
        total_spend,
    )


def _sku_factual_outcomes(
    orders: list[dict[str, Any]],
    sample_nmids: set[int],
) -> dict[int, dict[str, Any]]:
    groups: dict[int, dict[str, list[dict[str, Any]]]] = defaultdict(lambda: defaultdict(list))
    for row in orders:
        if _is_cancelled(row):
            continue
        day = _order_day(row)
        if not _in_period(day):
            continue
        nmid = _read_int(row, "nmId", "nm_id", "nmid")
        if nmid not in sample_nmids:
            continue
        groups[nmid][_g_key(row)].append(row)
    return {nmid: _event_metrics(g) for nmid, g in groups.items()}


def _concentration(metrics: dict[str, Any]) -> dict[str, Any]:
    spend = metrics.get("UNIFIED_AUTO", {}).get("spend_rub", 0) + metrics.get("SEARCH", {}).get("spend_rub", 0)
    u = metrics.get("UNIFIED_AUTO", {}).get("spend_rub") or 0
    s = metrics.get("SEARCH", {}).get("spend_rub") or 0
    if spend <= 0:
        return {"top_leg": None, "unified_spend_share": None, "search_spend_share": None}
    share_u = u / spend
    return {
        "top_leg": "UNIFIED_AUTO" if u >= s else "SEARCH",
        "unified_spend_share": round(share_u, 3),
        "search_spend_share": round(1 - share_u, 3),
        "variance_note": "high_concentration" if max(share_u, 1 - share_u) > 0.85 else "mixed",
    }


def _confidence(level: str, sample: dict[str, Any], metrics: dict[str, Any], total_spend: float) -> str:
    n = sample.get("nmids_count") or 0
    camps = (metrics.get("UNIFIED_AUTO", {}).get("campaign_count") or 0) + (
        metrics.get("SEARCH", {}).get("campaign_count") or 0
    )
    if total_spend < 500 or camps == 0:
        return "LOW"
    if level == "EXACT_SUBJECT" and n >= 3 and total_spend >= 2000:
        return "MEDIUM" if camps < 2 else "HIGH"
    if level == "RELATED_CATEGORY" and n >= 8 and total_spend >= 5000:
        return "MEDIUM"
    if level == "STORE_WIDE":
        return "MEDIUM" if total_spend >= 20000 else "LOW"
    return "LOW"


def _comparison_block(
    level: str,
    sample: dict[str, Any],
    metrics: dict[str, Any],
    placement: dict[str, Any],
    total_spend: float,
    factual: dict[int, dict[str, Any]],
) -> dict[str, Any]:
    return {
        "level": level,
        "sample_size_nmids": sample.get("nmids_count"),
        "sample_nmids": sample.get("nmids"),
        "UNIFIED_AUTO": metrics.get("UNIFIED_AUTO"),
        "SEARCH": metrics.get("SEARCH"),
        "UNCLASSIFIED": metrics.get("UNCLASSIFIED"),
        "total_sample_ad_spend_rub": round(total_spend, 2),
        "placement_breakdown_unified": placement,
        "concentration": _concentration(metrics),
        "confidence": _confidence(level, sample, metrics, total_spend),
        "sku_factual_outcomes": factual,
        "note": "Evidence only — no launch recommendation",
    }


async def _fetch_wb(root: Path) -> tuple[list[dict[str, Any]], list[dict[str, Any]], list[Any], list[dict[str, Any]], list[dict[str, Any]]]:
    from app.configs.app_config import AppConfig
    from app.core.di.wb_manager_hub.wb_manager_hub_factory import WBManagerHubFactory
    from app.core.mp.wb.api.httpx_client_handler import HttpxClientHandler
    from app.core.redis_manager_v2.redis_client import RedisClient
    from app.modules.common_slaves.wildberries.super_cabinet_manager import get_access_for_wb_cabinet
    from redis.asyncio import Redis

    app_config = AppConfig.create()
    rc = app_config.infrastructure.redis
    redis_raw: Redis[str] = Redis(
        host=rc.host, port=rc.port, db=rc.db, password=rc.password, decode_responses=True,
    )
    await redis_raw.ping()
    redis_wrap = RedisClient(redis_client=redis_raw)
    httpx = HttpxClientHandler()
    await httpx.init()
    try:
        await get_access_for_wb_cabinet(SHOP_ID)
        hub = WBManagerHubFactory(httpx_client_handler=httpx, redis_client_wrapper=redis_wrap).get_wb_manager_hub(SHOP_ID)
        dm = hub.wb_data_manager
        pm = dm.promotion_manager
        budget = ApiCallBudget(max_seconds=2400.0, max_api_calls=2000)
        rm = getattr(dm, "reports_manager", None)

        async def fetch_ord(df: str) -> list[object]:
            if rm:
                return list(await rm.get_supplier_orders(date_from=df, flag=0) or [])
            return list(await dm.get_supplier_orders(date_from=df, flag=0) or [])

        orders_res = await _paginate_supplier_rows(
            fetch=fetch_ord,
            initial_date_from=PERIOD_FROM.isoformat(),
            budget=budget,
            max_pages=1500,
        )
        orders = [jsonable(r) if not isinstance(r, dict) else r for r in orders_res.rows]

        budget.consume()
        adv_ids = list(await pm._client.promotion_count_adapter.get_cabinet_adv_ids() or [])
        budget.consume()
        camps_raw = list(await pm.get_adverts_v2_by_ids(adv_ids) or [])
        campaigns = [jsonable(x) for x in camps_raw if isinstance(jsonable(x), dict)]

        dates: list[date] = []
        d = PERIOD_FROM
        while d <= PERIOD_TO:
            dates.append(d)
            d += timedelta(days=1)
        budget.consume()
        stats_raw = list(await pm.get_full_adv_stat(adv_ids, dates) or [])
        raw_items = [jsonable(x) for x in stats_raw if isinstance(jsonable(x), dict)]
        nm_rows, day_rows = _nm_rows(raw_items)
        flat = _flatten_fullstats(stats_raw)
        return orders, campaigns, raw_items, nm_rows, day_rows
    finally:
        await httpx.shutdown()
        await redis_raw.aclose()


async def run_evidence(
    output_dir: Path,
    pg: list[dict[str, str]],
    wbcards: dict[int, dict[str, Any]],
) -> dict[str, Any]:
    checked = _msk_now()
    root = output_dir
    samples = _classify_samples(wbcards)
    pg_idx = _pg_index(pg)

    orders, campaigns, _raw_items, nm_rows, day_rows = await _fetch_wb(root)
    inventory, adv_nm = _campaign_maps(campaigns, pg_idx)

    # Campaign mapping for target + new (context only)
    target_campaigns = [
        inv for inv in inventory.values()
        if TARGET_NMID in (inv.get("nmids") or [])
    ]
    new_campaign_context = {
        "planned_unified_adv_id": NEW_UNIFIED_ADV,
        "planned_search_adv_id": NEW_SEARCH_ADV,
        "in_wb_inventory": {
            str(NEW_UNIFIED_ADV): NEW_UNIFIED_ADV in inventory,
            str(NEW_SEARCH_ADV): NEW_SEARCH_ADV in inventory,
        },
        "note": "New campaign IDs are context only; historical metrics exclude zero-spend future legs",
    }

    comparisons: dict[str, Any] = {}
    placement_global: dict[str, Any] = {}
    for key in ("EXACT_SUBJECT", "RELATED_CATEGORY", "STORE_WIDE"):
        sample = samples[key]
        nmset = set(sample["nmids"])
        metrics, placement, total_spend = _aggregate_leg_metrics(nmset, inventory, day_rows, nm_rows)
        factual = _sku_factual_outcomes(orders, nmset)
        comparisons[key] = _comparison_block(key, sample, metrics, placement, total_spend, factual)
        if key == "EXACT_SUBJECT":
            placement_global = placement

    # Direct vs associative from nm_rows + promoted map
    direct_assoc_status = "PARTIAL"
    direct_note = (
        "fullstats apps/nms available; promoted_nm_id vs ordered_nm_id split computable "
        "but not joined to leg comparison in this packet — use wb_a1_associated_conversions pattern"
    )
    promoted_rows, promoted_map = _config_rows([c for c in campaigns if isinstance(c, dict)])
    direct_orders = assoc_orders = 0
    for row in nm_rows:
        if not _in_period(row.get("date", "")):
            continue
        adv_id = _read_int(row, "advert_id")
        ordered = _read_int(row, "ordered_nm_id")
        promoted = promoted_map.get(adv_id, set())
        o = _read_int(row, "orders")
        if ordered in promoted:
            direct_orders += o
        elif o:
            assoc_orders += o
    direct_assoc = {
        "status": direct_assoc_status,
        "DIRECT_ATTRIBUTION": {
            "direct_attributed_orders": direct_orders,
            "associative_attributed_orders": assoc_orders,
            "scope": "store_all_campaigns_in_period",
        },
        "note": direct_note,
    }

    gaps: list[str] = []
    if samples["EXACT_SUBJECT"]["nmids_count"] < 2:
        gaps.append("EXACT_SUBJECT sample very small")
    if comparisons["EXACT_SUBJECT"]["total_sample_ad_spend_rub"] == 0:
        gaps.append("EXACT_SUBJECT zero ad spend in period")
    if comparisons["EXACT_SUBJECT"]["UNIFIED_AUTO"]["campaign_count"] == 0 and comparisons["EXACT_SUBJECT"]["SEARCH"]["campaign_count"] == 0:
        gaps.append("no classified legs with spend for exact subject")
    if not placement_global:
        gaps.append("UNIFIED placement breakdown empty (no unified spend or apps[])")

    payload = {
        "CHECKED_AT_MSK": checked.strftime("%Y-%m-%d %H:%M:%S %Z"),
        "PERIOD": {
            "from": PERIOD_FROM.isoformat(),
            "to": PERIOD_TO.isoformat(),
            "closed_days": PERIOD_DAYS,
            "timezone": "Europe/Moscow",
        },
        "TARGET": {
            "nmID": TARGET_NMID,
            "subjectID": TARGET_SUBJECT_ID,
            "subjectName": TARGET_SUBJECT_NAME,
            "NEW_CAMPAIGNS": new_campaign_context,
        },
        "EXACT_SUBJECT_SAMPLE": samples["EXACT_SUBJECT"],
        "RELATED_CATEGORY_SAMPLE": samples["RELATED_CATEGORY"],
        "STORE_WIDE_SAMPLE": {"nmids_count": samples["STORE_WIDE"]["nmids_count"]},
        "TARGET_SKU_CAMPAIGN_MAPPING": target_campaigns,
        "CAMPAIGN_INVENTORY_COUNT": len(inventory),
        "UNIFIED_METRICS": comparisons["EXACT_SUBJECT"]["UNIFIED_AUTO"],
        "SEARCH_METRICS": comparisons["EXACT_SUBJECT"]["SEARCH"],
        "PLACEMENT_BREAKDOWN": placement_global,
        "DIRECT_ASSOCIATIVE_STATUS": direct_assoc,
        "COMPARISON_TABLE": {
            "A_EXACT_SUBJECT": comparisons["EXACT_SUBJECT"],
            "B_RELATED_CATEGORY": comparisons["RELATED_CATEGORY"],
            "C_STORE_WIDE": comparisons["STORE_WIDE"],
        },
        "CONFIDENCE_BY_LEVEL": {
            k: comparisons[k]["confidence"] for k in comparisons
        },
        "DATA_GAPS": gaps,
        "NO_WRITES": "CONFIRMED",
    }

    pkg = output_dir / PACKAGE
    pkg.mkdir(parents=True, exist_ok=True)
    (pkg / f"{PACKAGE}.json").write_text(
        json.dumps(payload, ensure_ascii=False, indent=2, default=str), encoding="utf-8",
    )
    return payload


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--output-dir", default=".tmp/a1_sku837_ad_leg_evidence")
    args = ap.parse_args(argv)
    root = Path(args.output_dir).resolve()
    _bootstrap()
    pg = _load_pg_adv(root)
    wbcards = _load_all_wbcards(root)
    payload = asyncio.run(run_evidence(root, pg, wbcards))
    summary = {
        "CHECKED_AT_MSK": payload["CHECKED_AT_MSK"],
        "PERIOD": payload["PERIOD"],
        "EXACT_SUBJECT_SAMPLE": payload["EXACT_SUBJECT_SAMPLE"],
        "RELATED_CATEGORY_SAMPLE": {
            "nmids_count": payload["RELATED_CATEGORY_SAMPLE"]["nmids_count"],
        },
        "STORE_WIDE_SAMPLE": payload["STORE_WIDE_SAMPLE"],
        "UNIFIED_METRICS": payload["UNIFIED_METRICS"],
        "SEARCH_METRICS": payload["SEARCH_METRICS"],
        "PLACEMENT_BREAKDOWN": payload["PLACEMENT_BREAKDOWN"],
        "DIRECT_ASSOCIATIVE_STATUS": payload["DIRECT_ASSOCIATIVE_STATUS"],
        "COMPARISON_TABLE": {
            "A_EXACT_SUBJECT": {
                "confidence": payload["COMPARISON_TABLE"]["A_EXACT_SUBJECT"]["confidence"],
                "total_sample_ad_spend_rub": payload["COMPARISON_TABLE"]["A_EXACT_SUBJECT"]["total_sample_ad_spend_rub"],
                "UNIFIED_AUTO": payload["COMPARISON_TABLE"]["A_EXACT_SUBJECT"]["UNIFIED_AUTO"],
                "SEARCH": payload["COMPARISON_TABLE"]["A_EXACT_SUBJECT"]["SEARCH"],
                "concentration": payload["COMPARISON_TABLE"]["A_EXACT_SUBJECT"]["concentration"],
            },
            "B_RELATED_CATEGORY": {
                "confidence": payload["COMPARISON_TABLE"]["B_RELATED_CATEGORY"]["confidence"],
                "total_sample_ad_spend_rub": payload["COMPARISON_TABLE"]["B_RELATED_CATEGORY"]["total_sample_ad_spend_rub"],
                "UNIFIED_AUTO": payload["COMPARISON_TABLE"]["B_RELATED_CATEGORY"]["UNIFIED_AUTO"],
                "SEARCH": payload["COMPARISON_TABLE"]["B_RELATED_CATEGORY"]["SEARCH"],
            },
            "C_STORE_WIDE": {
                "confidence": payload["COMPARISON_TABLE"]["C_STORE_WIDE"]["confidence"],
                "total_sample_ad_spend_rub": payload["COMPARISON_TABLE"]["C_STORE_WIDE"]["total_sample_ad_spend_rub"],
                "UNIFIED_AUTO": payload["COMPARISON_TABLE"]["C_STORE_WIDE"]["UNIFIED_AUTO"],
                "SEARCH": payload["COMPARISON_TABLE"]["C_STORE_WIDE"]["SEARCH"],
            },
        },
        "DATA_GAPS": payload["DATA_GAPS"],
        "NO_WRITES": payload["NO_WRITES"],
    }
    print(json.dumps(summary, ensure_ascii=False, indent=2, default=str))
    return 0


if __name__ == "__main__":
    sys.exit(main())
