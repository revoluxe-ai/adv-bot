"""READ_ONLY patch: EXACT_SUBJECT join для A1 ad-leg evidence.

Content API subject mapping + targeted fullstats только для кампаний,
промотирующих subjectID=4069. Не full-cabinet collect.
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
from datetime import date, datetime, timedelta, timezone
from pathlib import Path
from typing import Any
from zoneinfo import ZoneInfo

import dotenv

dotenv.load_dotenv()

from scripts.wb_a1_associated_conversions import _nm_rows, _read_float, _read_int
from scripts.wb_api_readonly_ops.collect.api_budget import ApiCallBudget
from scripts.wb_api_readonly_ops.collect.cards import collect_cards
from scripts.wb_api_readonly_ops.collect.jsonable import jsonable

SHOP_ID = "5339e9ad-cbfe-50fc-8d77-b9f337a80417"
MSK = ZoneInfo("Europe/Moscow")
PACKAGE = "A1-SKU837-EXACT-SUBJECT-PATCH"

TARGET_NMID = 837395782
TARGET_SUBJECT_ID = 4069
TARGET_SUBJECT_NAME = "Подушки для растяжки"

PERIOD_FROM = date(2026, 8, 5)
PERIOD_TO = date(2026, 9, 1)
PRIOR_JOB = "ops-script-a1-sku837-ad-leg-20260902-180000"


def _msk_now() -> datetime:
    return datetime.now(timezone.utc).astimezone(MSK)


def _pg_db() -> str:
    return os.environ.get("POSTGRES_DBNAME") or "adv_updater"


def _bootstrap() -> None:
    u, p = os.environ.get("POSTGRES_USER"), os.environ.get("POSTGRES_PASSWORD")
    if u and p:
        from scripts import ch_a1_evidence as evidence

        evidence._PG_CREDENTIALS = u, p
    h = os.environ.get("POSTGRES_MASTER_HOST") or os.environ.get("POSTGRES_REPLICA_HOST")
    if h:
        from scripts import ch_a1_evidence as evidence

        evidence.PG_EXTERNAL_HOST = h
    pt = os.environ.get("POSTGRES_PORT")
    if pt:
        from scripts import ch_a1_evidence as evidence

        evidence.PG_EXTERNAL_PORT = int(pt)


def _parse_nmids(raw: str) -> list[int]:
    out: list[int] = []
    for part in re.split(r"[,;\s]+", str(raw or "")):
        part = part.strip().strip("[]")
        if part.isdigit():
            out.append(int(part))
    return out


def _load_pg_adv(root: Path) -> list[dict[str, str]]:
    from scripts import ch_a1_evidence as evidence

    staging = root / "staging"
    staging.mkdir(parents=True, exist_ok=True)
    out = staging / "pg_adv.csv"
    cols = "a.adv_id, a._search_adv_id, a.type, a.name, a.nmids, a.wb_bid_type"
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


def _cards_subject_map(cards: list[dict[str, Any]]) -> dict[int, dict[str, Any]]:
    out: dict[int, dict[str, Any]] = {}
    for card in cards:
        nmid = _read_int(card, "nmID", "nmId", "nmid")
        if not nmid:
            continue
        sid = _read_int(card, "subjectID", "subjectId")
        out[nmid] = {
            "nmID": nmid,
            "subjectID": sid,
            "subjectName": card.get("subjectName"),
            "vendorCode": card.get("vendorCode"),
            "title": card.get("title"),
        }
    return out


def _in_period(day: str) -> bool:
    try:
        d = date.fromisoformat(day[:10])
    except ValueError:
        return False
    return PERIOD_FROM <= d <= PERIOD_TO


def _leg_from_campaign(raw: dict[str, Any], pg_row: dict[str, Any] | None) -> str:
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


def _empty_metrics() -> dict[str, Any]:
    return {
        "spend_rub": 0.0,
        "views": 0,
        "clicks": 0,
        "attributed_orders": 0,
        "attributed_gmv_rub": 0.0,
        "atbs": 0,
        "campaign_ids": set(),
    }


def _finalize_metrics(m: dict[str, Any], total_spend: float) -> dict[str, Any]:
    spend = round(float(m["spend_rub"]), 2)
    clicks = int(m["clicks"])
    views = int(m["views"])
    orders = int(m["attributed_orders"])
    gmv = round(float(m["attributed_gmv_rub"]), 2)
    return {
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
        "campaign_ids": sorted(m["campaign_ids"]),
    }


def _aggregate_exact(
    exact_nmids: set[int],
    inventory: dict[int, dict[str, Any]],
    day_rows: list[dict[str, Any]],
    nm_rows: list[dict[str, Any]],
) -> tuple[dict[str, Any], dict[str, Any], dict[str, Any], float]:
    relevant: dict[int, str] = {}
    for adv_id, inv in inventory.items():
        if exact_nmids.intersection(inv.get("nmids") or []):
            relevant[adv_id] = inv.get("leg") or "UNCLASSIFIED"

    legs = {k: _empty_metrics() for k in ("UNIFIED_AUTO", "SEARCH", "UNCLASSIFIED")}
    placement: dict[str, dict[str, Any]] = defaultdict(_empty_metrics)

    for row in day_rows:
        if not _in_period(row.get("date", "")):
            continue
        adv_id = _read_int(row, "advert_id")
        if adv_id not in relevant:
            continue
        leg = relevant[adv_id]
        b = legs[leg]
        b["spend_rub"] += _read_float(row, "day_spend")
        b["clicks"] += _read_int(row, "day_clicks")
        b["views"] += _read_int(row, "day_views")
        b["attributed_orders"] += _read_int(row, "day_orders")
        b["attributed_gmv_rub"] += _read_float(row, "day_sum_price")
        b["campaign_ids"].add(adv_id)

    for row in nm_rows:
        if not _in_period(row.get("date", "")):
            continue
        adv_id = _read_int(row, "advert_id")
        nmid = _read_int(row, "ordered_nm_id")
        if adv_id not in relevant or nmid not in exact_nmids:
            continue
        leg = relevant[adv_id]
        legs[leg]["atbs"] += _read_int(row, "atbs")
        if leg == "UNIFIED_AUTO":
            app_type = str(row.get("app_type") or "unknown")
            placement[app_type]["atbs"] += _read_int(row, "atbs")
            placement[app_type]["spend_rub"] += _read_float(row, "spend")
            placement[app_type]["clicks"] += _read_int(row, "clicks")
            placement[app_type]["views"] += _read_int(row, "views")
            placement[app_type]["attributed_orders"] += _read_int(row, "orders")
            placement[app_type]["attributed_gmv_rub"] += _read_float(row, "sum_price")

    total = sum(legs[k]["spend_rub"] for k in legs)
    unified = _finalize_metrics(legs["UNIFIED_AUTO"], total)
    search = _finalize_metrics(legs["SEARCH"], total)
    placement_out = {
        k: _finalize_metrics(v, unified.get("spend_rub") or 0) for k, v in placement.items()
    }
    return unified, search, placement_out, total


def _adv_candidates_for_nmids(
    pg_rows: list[dict[str, str]],
    exact_nmids: set[int],
) -> tuple[dict[int, dict[str, Any]], set[int]]:
    pg_idx: dict[int, dict[str, Any]] = {}
    adv_candidates: set[int] = set()
    for row in pg_rows:
        adv = _read_int(row, "adv_id")
        if not adv:
            continue
        nmids = _parse_nmids(row.get("nmids") or "")
        pg_idx[adv] = {"wb_bid_type": row.get("wb_bid_type"), "nmids": nmids}
        if exact_nmids.intersection(nmids):
            adv_candidates.add(adv)
        search_adv = _read_int(row, "_search_adv_id")
        if search_adv and exact_nmids.intersection(nmids):
            adv_candidates.add(search_adv)
    return pg_idx, adv_candidates


async def _fetch_exact_subject_data(
    root: Path,
    pg_rows: list[dict[str, str]],
) -> tuple[
    dict[int, dict[str, Any]],
    list[int],
    bool,
    dict[int, dict[str, Any]],
    list[dict[str, Any]],
    list[dict[str, Any]],
    set[int],
]:
    """Content API cards + targeted fullstats для кампаний subject 4069."""
    from app.configs.app_config import AppConfig
    from app.core.di.wb_manager_hub.wb_manager_hub_factory import WBManagerHubFactory
    from app.core.mp.wb.api.httpx_client_handler import HttpxClientHandler
    from app.core.redis_manager_v2.redis_client import RedisClient
    from app.modules.common_slaves.wildberries.super_cabinet_manager import get_access_for_wb_cabinet
    from redis.asyncio import Redis
    from scripts.wb_api_readonly_ops.collect.raw_store import RawStore

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
        budget = ApiCallBudget(max_seconds=900.0, max_api_calls=500)

        store = RawStore(root / "_raw_cards")
        _, cards = await collect_cards(dm, store=store, budget=budget, page_limit=100)
        card_map = _cards_subject_map(cards)
        exact_nmids = sorted(n for n, c in card_map.items() if c.get("subjectID") == TARGET_SUBJECT_ID)
        exact_set = set(exact_nmids)
        target_in_exact = TARGET_NMID in exact_set

        pg_idx, adv_candidates = _adv_candidates_for_nmids(pg_rows, exact_set)
        inventory: dict[int, dict[str, Any]] = {}
        nm_rows: list[dict[str, Any]] = []
        day_rows: list[dict[str, Any]] = []

        if adv_candidates:
            budget.consume()
            camps_raw = list(await pm.get_adverts_v2_by_ids(sorted(adv_candidates)) or [])
            for raw in camps_raw:
                d = jsonable(raw)
                if not isinstance(d, dict):
                    continue
                adv_id = _read_int(d, "id", "advertId")
                if not adv_id:
                    continue
                nm_settings = d.get("nm_settings") or d.get("nmSettings") or []
                nmids: set[int] = set()
                if isinstance(nm_settings, list):
                    for nm in nm_settings:
                        if isinstance(nm, dict):
                            nid = _read_int(nm, "nm_id", "nmId", "nmID")
                            if nid:
                                nmids.add(nid)
                if not nmids:
                    nmids.update(pg_idx.get(adv_id, {}).get("nmids") or [])
                settings = d.get("settings") if isinstance(d.get("settings"), dict) else {}
                inventory[adv_id] = {
                    "adv_id": adv_id,
                    "leg": _leg_from_campaign(d, pg_idx.get(adv_id)),
                    "nmids": sorted(nmids),
                    "bid_type": d.get("bid_type"),
                    "payment_type": settings.get("payment_type"),
                }

            dates: list[date] = []
            d = PERIOD_FROM
            while d <= PERIOD_TO:
                dates.append(d)
                d += timedelta(days=1)
            budget.consume()
            stats_raw = list(await pm.get_full_adv_stat(sorted(adv_candidates), dates) or [])
            raw_items = [jsonable(x) for x in stats_raw if isinstance(jsonable(x), dict)]
            nm_rows, day_rows = _nm_rows(raw_items)

        cache = {
            "adv_candidates": sorted(adv_candidates),
            "exact_nmids": exact_nmids,
            "inventory": {str(k): v for k, v in inventory.items()},
            "nm_rows_count": len(nm_rows),
            "day_rows_count": len(day_rows),
        }
        staging = root / "staging"
        staging.mkdir(parents=True, exist_ok=True)
        (staging / "exact_subject_join_cache.json").write_text(
            json.dumps(cache, ensure_ascii=False, indent=2, default=str), encoding="utf-8",
        )
        return card_map, exact_nmids, target_in_exact, inventory, nm_rows, day_rows, adv_candidates
    finally:
        await httpx.shutdown()
        await redis_raw.aclose()


async def run_patch(output_dir: Path, pg: list[dict[str, str]]) -> dict[str, Any]:
    checked = _msk_now()
    gaps: list[str] = []

    (
        card_map,
        exact_nmids,
        target_in_exact,
        inventory,
        nm_rows,
        day_rows,
        adv_candidates,
    ) = await _fetch_exact_subject_data(output_dir, pg)
    exact_set = set(exact_nmids)

    if not exact_nmids:
        gaps.append("Content API returned zero nmIDs for subjectID=4069")
    if not adv_candidates:
        gaps.append("No PG campaigns promote any subjectID=4069 nmID")
    if not target_in_exact:
        gaps.append(f"TARGET_NMID {TARGET_NMID} not in Content API subjectID=4069 set")

    unified, search, placement, total_spend = _aggregate_exact(
        exact_set, inventory, day_rows, nm_rows,
    )

    promoted_map: dict[int, set[int]] = {
        adv_id: set(inv.get("nmids") or []) for adv_id, inv in inventory.items()
    }
    direct_orders = assoc_orders = 0
    for row in nm_rows:
        if not _in_period(row.get("date", "")):
            continue
        adv_id = _read_int(row, "advert_id")
        if adv_id not in promoted_map:
            continue
        ordered = _read_int(row, "ordered_nm_id")
        if ordered not in exact_set:
            continue
        o = _read_int(row, "orders")
        if ordered in promoted_map.get(adv_id, set()):
            direct_orders += o
        elif o:
            assoc_orders += o

    confidence = "LOW"
    if total_spend >= 500 and (unified["campaign_count"] + search["campaign_count"]) > 0:
        confidence = "MEDIUM" if len(exact_nmids) < 3 or total_spend < 3000 else "HIGH"
    if total_spend == 0:
        gaps.append("EXACT_SUBJECT zero ad spend in period for subject 4069 campaigns")

    payload = {
        "CHECKED_AT_MSK": checked.strftime("%Y-%m-%d %H:%M:%S %Z"),
        "PRIOR_JOB": PRIOR_JOB,
        "PERIOD": {"from": PERIOD_FROM.isoformat(), "to": PERIOD_TO.isoformat()},
        "EXACT_SUBJECT_NMIDS": exact_nmids,
        "EXACT_SUBJECT_SAMPLE_SIZE": len(exact_nmids),
        "TARGET_NMID_837395782_IN_SUBJECT_4069": target_in_exact,
        "TARGET_NMID_SUBJECT_PROOF": card_map.get(TARGET_NMID),
        "EXACT_SUBJECT_SAMPLE": {
            "level": "EXACT_SUBJECT",
            "subjectID": TARGET_SUBJECT_ID,
            "subjectName": TARGET_SUBJECT_NAME,
            "source": "Content API /content/v2/get/cards/list",
            "nmids": exact_nmids,
            "nmids_count": len(exact_nmids),
            "cards_total": len(card_map),
            "adv_candidates_count": len(adv_candidates),
        },
        "UNIFIED_METRICS_EXACT": unified,
        "SEARCH_METRICS_EXACT": search,
        "PLACEMENT_BREAKDOWN_EXACT": placement,
        "DIRECT_ASSOCIATIVE_STATUS_EXACT": {
            "status": "COMPUTED_EXACT_SUBSET",
            "scope": "campaigns promoting subjectID=4069 only",
            "direct_attributed_orders": direct_orders,
            "associative_attributed_orders": assoc_orders,
            "DIRECT_ATTRIBUTION": "AVAILABLE_EXACT_SUBSET",
        },
        "UNIFIED_vs_SEARCH_TABLE": {
            "UNIFIED_AUTO": unified,
            "SEARCH": search,
            "total_ad_spend_rub": round(total_spend, 2),
            "top_leg_by_spend": "UNIFIED_AUTO" if unified["spend_rub"] >= search["spend_rub"] else "SEARCH",
        },
        "confidence": confidence,
        "remaining_gaps": gaps + [
            "Prior job did not persist nm_rows/day_rows; targeted fullstats for subject-4069 campaigns only (not full-cabinet)",
            "PG adv nmids may be stale vs Content API / WB v2 nm_settings",
        ],
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
    ap.add_argument("--output-dir", default="/tmp/a1_sku837_exact_subject_patch")
    args = ap.parse_args(argv)
    root = Path(args.output_dir).resolve()
    _bootstrap()
    pg = _load_pg_adv(root)
    payload = asyncio.run(run_patch(root, pg))
    summary = {
        "CHECKED_AT_MSK": payload["CHECKED_AT_MSK"],
        "EXACT_SUBJECT_NMIDS": payload["EXACT_SUBJECT_NMIDS"],
        "EXACT_SUBJECT_SAMPLE_SIZE": payload["EXACT_SUBJECT_SAMPLE_SIZE"],
        "TARGET_NMID_837395782_IN_SUBJECT_4069": payload["TARGET_NMID_837395782_IN_SUBJECT_4069"],
        "TARGET_NMID_SUBJECT_PROOF": payload["TARGET_NMID_SUBJECT_PROOF"],
        "UNIFIED_vs_SEARCH_TABLE": payload["UNIFIED_vs_SEARCH_TABLE"],
        "PLACEMENT_BREAKDOWN_EXACT": payload["PLACEMENT_BREAKDOWN_EXACT"],
        "DIRECT_ASSOCIATIVE_STATUS_EXACT": payload["DIRECT_ASSOCIATIVE_STATUS_EXACT"],
        "confidence": payload["confidence"],
        "remaining_gaps": payload["remaining_gaps"],
        "NO_WRITES": payload["NO_WRITES"],
    }
    print(json.dumps(summary, ensure_ascii=False, indent=2, default=str))
    return 0


if __name__ == "__main__":
    sys.exit(main())
