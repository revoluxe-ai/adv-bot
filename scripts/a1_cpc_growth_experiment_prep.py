"""READ_ONLY: A1 CPC growth experiment prep — authoritative data packet.

Собирает historical demand, advertising history, growth-candidate universe,
temporal patterns и CPC technical eligibility для проектирования отдельного
CPC growth experiment (2 SKU). Без advertising writes и финального selection.
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
from datetime import date, datetime, timedelta
from pathlib import Path
from typing import Any
from zoneinfo import ZoneInfo

import dotenv

dotenv.load_dotenv()

from scripts import ch_a1_evidence as evidence
from scripts.wb_a1_associated_conversions import _read_float, _read_int
from scripts.wb_api_readonly_ops.collect.ads import _flatten_fullstats
from scripts.wb_api_readonly_ops.collect.api_budget import ApiCallBudget
from scripts.wb_api_readonly_ops.collect.jsonable import jsonable
from scripts.wb_api_readonly_ops.collect.orders_sales import _paginate_supplier_rows

SHOP_ID = "5339e9ad-cbfe-50fc-8d77-b9f337a80417"
MSK = ZoneInfo("Europe/Moscow")
PACKAGE = "A1-CPC-GROWTH-EXPERIMENT-PREP"

PERIOD_FROM = date(2026, 8, 5)
PERIOD_TO = date(2026, 9, 1)
CLOSED_THROUGH = date(2026, 9, 1)

ITER06_NMIDS = {7974106, 770642983, 14166423, 7839837}
H1_PHYSICAL = {17906286, 21604339, 20646357, 21604374}
DEFERRED_ADV = 34210859
BULK_HEAVY_NMIDS = {837395782, 195764899}
ACTIVE_WB = {9, 11}

PG_ADV_FIELDS = [
    "id", "adv_id", "_search_adv_id", "type", "name", "nmids", "active_status", "bot_active",
    "auto_budget_watchdog_enabled", "auto_budget_daily_limit", "search_auto_budget_daily_limit",
    "use_common_budget", "common_budget_daily_limit", "strategy", "automatic_version",
]
NAME_SEARCH = re.compile(r"<!-\[(\d+)\]-!>")

DOW_NAMES = ("Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun")


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


def _write_csv(path: Path, rows: list[dict[str, Any]], cols: list[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=cols, extrasaction="ignore")
        w.writeheader()
        for r in rows:
            w.writerow({c: r.get(c, "") for c in cols})


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
    with out.open(encoding="utf-8", newline="") as f:
        return list(csv.DictReader(f))


def _load_wbcards(root: Path, nmids: set[int]) -> dict[int, dict[str, Any]]:
    if not nmids:
        return {}
    ids_sql = ", ".join(str(n) for n in sorted(nmids))
    path = root / "staging" / "wbcard.csv"
    q = (
        f"SELECT nmid, name, wb_category_id, json FROM public.wbcard w "
        f"JOIN public.wbcabinet c ON w.wb_cabinet_id = c.id "
        f"WHERE c.shop_id = '{SHOP_ID}' AND w.nmid IN ({ids_sql})"
    )
    st = evidence.run_pg_query(_pg_db(), q, path, root / "sql" / "wbcard.sql", csv_output=True)
    out: dict[int, dict[str, Any]] = {}
    if not st["success"]:
        return out
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
            out[nmid] = {
                "name": row.get("name") or raw_json.get("title") or "",
                "wb_category_id": row.get("wb_category_id") or raw_json.get("subjectID"),
                "subject": raw_json.get("subjectName") or row.get("name") or "",
                "category": raw_json.get("parentName") or "",
                "stock": _read_int(raw_json, "quantity", "stocks") or None,
                "price": _read_float(raw_json, "price", "salePrice"),
            }
    return out


def _is_cancelled(row: dict[str, Any]) -> bool:
    return str(row.get("isCancel")).lower() in ("true", "1", "t")


def _g_key(row: dict[str, Any]) -> str:
    g = str(row.get("gNumber") or "").strip()
    return g if g else f"srid:{row.get('srid')}"


def _order_day(row: dict[str, Any]) -> str:
    return str(row.get("date") or row.get("lastChangeDate") or "")[:10]


def _msk_dt(row: dict[str, Any]) -> datetime | None:
    raw = str(row.get("date") or row.get("lastChangeDate") or "").strip()
    if not raw or raw.startswith("0001"):
        return None
    try:
        if raw.endswith("Z"):
            dt = datetime.fromisoformat(raw.replace("Z", "+00:00"))
            return dt.astimezone(MSK)
        if "+" in raw[10:] or raw.endswith("MSK"):
            dt = datetime.fromisoformat(raw.replace("MSK", "").strip())
            if dt.tzinfo is None:
                dt = dt.replace(tzinfo=MSK)
            return dt.astimezone(MSK)
        dt = datetime.fromisoformat(raw)
        return dt.replace(tzinfo=MSK)
    except ValueError:
        return None


def _in_period(day: str) -> bool:
    try:
        d = date.fromisoformat(day)
    except ValueError:
        return False
    return PERIOD_FROM <= d <= PERIOD_TO


def _active_period_orders(orders: list[dict[str, Any]]) -> list[dict[str, Any]]:
    return [
        r for r in orders
        if not _is_cancelled(r) and _in_period(_order_day(r))
    ]


def _event_metrics(groups: dict[str, list[dict[str, Any]]]) -> dict[str, Any]:
    events = len(groups)
    units = sum(len(v) for v in groups.values())
    bulk_events = sum(1 for v in groups.values() if len(v) >= 2)
    bulk_units = sum(len(v) for v in groups.values() if len(v) >= 2)
    total_price = round(sum(_read_float(r, "totalPrice") for rs in groups.values() for r in rs), 2)
    return {
        "PURCHASE_EVENTS": events,
        "UNITS": units,
        "TOTAL_PRICE_VALUE": total_price,
        "units_per_event": round(units / events, 3) if events else 0,
        "bulk_events": bulk_events,
        "bulk_unit_share_pct": round(100 * bulk_units / units, 2) if units else 0,
    }


def _adv_nm_map(campaigns: list[dict[str, Any]]) -> dict[int, set[int]]:
    out: dict[int, set[int]] = defaultdict(set)
    for c in campaigns:
        adv_id = _read_int(c, "id", "advertId")
        if not adv_id:
            continue
        for nm in c.get("nm_settings") or c.get("nmSettings") or []:
            if isinstance(nm, dict):
                nid = _read_int(nm, "nm_id", "nmId", "nmID")
                if nid:
                    out[adv_id].add(nid)
    return out


def _campaign_payment(c: dict[str, Any]) -> str:
    settings = c.get("settings") if isinstance(c.get("settings"), dict) else {}
    return str(settings.get("payment_type") or settings.get("paymentType") or "unknown").lower()


def _aggregate_ad_by_sku(
    fullstats: list[dict[str, Any]], adv_nm: dict[int, set[int]]
) -> dict[int, dict[str, Any]]:
    out: dict[int, dict[str, Any]] = defaultdict(
        lambda: {
            "ad_spend_rub": 0.0, "clicks": 0, "views": 0,
            "attributed_orders": 0, "attributed_value_rub": 0.0,
            "campaign_ids": set(), "payment_models": set(),
            "auto_spend": 0.0, "search_spend": 0.0,
        }
    )
    for row in fullstats:
        day = str(row.get("date") or "")[:10]
        if not _in_period(day):
            continue
        adv_id = _read_int(row, "advertId", "advert_id")
        spend = _read_float(row, "sum", "spend")
        clicks = _read_int(row, "clicks")
        views = _read_int(row, "views")
        attr_o = _read_int(row, "orders")
        attr_v = _read_float(row, "sum_price")
        for nmid in adv_nm.get(adv_id, ()):
            b = out[nmid]
            b["ad_spend_rub"] += spend
            b["clicks"] += clicks
            b["views"] += views
            b["attributed_orders"] += attr_o
            b["attributed_value_rub"] += attr_v
            if spend > 0:
                b["campaign_ids"].add(adv_id)
    for nmid, b in out.items():
        b["ad_spend_rub"] = round(float(b["ad_spend_rub"]), 2)
        b["attributed_value_rub"] = round(float(b["attributed_value_rub"]), 2)
        b["CPC"] = round(b["ad_spend_rub"] / b["clicks"], 2) if b["clicks"] else None
        b["CTR_pct"] = round(100 * b["clicks"] / b["views"], 3) if b["views"] else None
        b["campaign_ids"] = sorted(b["campaign_ids"])
        b["purchase_events_per_rub_spend"] = None
    return dict(out)


def _pg_adv_index(pg: list[dict[str, str]]) -> dict[int, dict[str, Any]]:
    idx: dict[int, dict[str, Any]] = {}
    for row in pg:
        adv = _read_int(row, "adv_id")
        if not adv:
            continue
        nmids = _parse_nmids(row.get("nmids") or "")
        search_id = _read_int(row, "_search_adv_id")
        idx[adv] = {
            "adv_id": adv,
            "search_adv_id": search_id,
            "name": row.get("name") or "",
            "nmids": nmids,
            "active_status": _read_int(row, "active_status"),
            "bot_active": str(row.get("bot_active")).lower() in ("true", "t", "1"),
            "auto_budget_daily_limit": _read_int(row, "auto_budget_daily_limit"),
            "search_auto_budget_daily_limit": _read_int(row, "search_auto_budget_daily_limit"),
            "use_common_budget": str(row.get("use_common_budget")).lower() in ("true", "t", "1"),
            "common_budget_daily_limit": _read_int(row, "common_budget_daily_limit"),
            "strategy": row.get("strategy") or "",
            "automatic_version": row.get("automatic_version") or "",
        }
    return idx


def _h1_nmids(pg_idx: dict[int, dict[str, Any]]) -> set[int]:
    out: set[int] = set()
    for adv in H1_PHYSICAL:
        info = pg_idx.get(adv, {})
        out.update(info.get("nmids") or [])
    return out


def _excluded_nmids(pg_idx: dict[int, dict[str, Any]]) -> set[int]:
    ex = set(ITER06_NMIDS) | _h1_nmids(pg_idx)
    # deferred search leg nmids still counted if authoritative elsewhere — exclude H1 only
    return ex


def _ad_state_for_nmid(nmid: int, pg_idx: dict[int, dict[str, Any]], campaigns: list[dict[str, Any]]) -> dict[str, Any]:
    adv_nm = _adv_nm_map(campaigns)
    nm_to_adv = defaultdict(set)
    for adv, nms in adv_nm.items():
        for n in nms:
            nm_to_adv[n].add(adv)
    advs = sorted(nm_to_adv.get(nmid, ()))
    legs: list[dict[str, Any]] = []
    for adv in advs:
        pg = pg_idx.get(adv, {})
        camp = next((c for c in campaigns if _read_int(c, "id", "advertId") == adv), {})
        legs.append({
            "adv_id": adv,
            "wb_status": camp.get("status"),
            "payment_type": _campaign_payment(camp),
            "bot_active": pg.get("bot_active"),
            "active_status": pg.get("active_status"),
            "auto_daily_limit": pg.get("auto_budget_daily_limit"),
            "search_daily_limit": pg.get("search_auto_budget_daily_limit"),
            "search_leg_adv_id": pg.get("search_adv_id"),
        })
    return {
        "physical_campaigns": advs,
        "legs": legs,
        "has_active_wb_campaign": any(
            _read_int(c, "status") in ACTIVE_WB
            for c in campaigns
            if _read_int(c, "id", "advertId") in advs
        ),
    }


def _temporal_buckets(
    orders: list[dict[str, Any]],
    *,
    nmid: int | None = None,
    subject_key: str | None = None,
) -> dict[str, Any]:
    """Aggregate PURCHASE_EVENTS by DOW×hour at store/category/SKU level."""
    cells: dict[tuple[int, int], dict[str, list[dict[str, Any]]]] = defaultdict(lambda: defaultdict(list))
    for row in orders:
        if nmid is not None and _read_int(row, "nmId", "nm_id", "nmid") != nmid:
            continue
        if subject_key is not None:
            subj = str(row.get("subject") or row.get("category") or "")
            if subj != subject_key:
                continue
        dt = _msk_dt(row)
        if not dt:
            continue
        dow = dt.weekday()
        hour = dt.hour
        cells[(dow, hour)][_g_key(row)].append(row)

    bucket_rows: list[dict[str, Any]] = []
    all_groups: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for (dow, hour), groups in sorted(cells.items()):
        merged = dict(groups)
        for gk, rs in merged.items():
            all_groups[gk].extend(rs)
        m = _event_metrics(merged)
        sku_set = {
            s
            for rs in merged.values()
            for r in rs
            for s in [_read_int(r, "nmId", "nm_id", "nmid")]
            if s
        }
        bucket_rows.append({
            "dow": DOW_NAMES[dow],
            "dow_idx": dow,
            "hour_msk": hour,
            **m,
            "distinct_active_sku": len(sku_set),
        })

    totals = _event_metrics(all_groups)
    by_hour: dict[int, dict[str, Any]] = defaultdict(lambda: {"PURCHASE_EVENTS": 0, "TOTAL_PRICE_VALUE": 0.0, "bulk_events": 0})
    by_dow: dict[int, dict[str, Any]] = defaultdict(lambda: {"PURCHASE_EVENTS": 0, "TOTAL_PRICE_VALUE": 0.0})
    for br in bucket_rows:
        h = int(br["hour_msk"])
        by_hour[h]["PURCHASE_EVENTS"] += int(br["PURCHASE_EVENTS"])
        by_hour[h]["TOTAL_PRICE_VALUE"] += float(br["TOTAL_PRICE_VALUE"])
        by_hour[h]["bulk_events"] += int(br["bulk_events"])
        d = int(br["dow_idx"])
        by_dow[d]["PURCHASE_EVENTS"] += int(br["PURCHASE_EVENTS"])
        by_dow[d]["TOTAL_PRICE_VALUE"] += float(br["TOTAL_PRICE_VALUE"])

    total_pe = totals["PURCHASE_EVENTS"] or 1
    hour_rank_pe = sorted(
        [{"hour_msk": h, **v, "share_pct": round(100 * v["PURCHASE_EVENTS"] / total_pe, 2)} for h, v in by_hour.items()],
        key=lambda x: -x["PURCHASE_EVENTS"],
    )
    hour_rank_val = sorted(
        [{"hour_msk": h, **v} for h, v in by_hour.items()],
        key=lambda x: -x["TOTAL_PRICE_VALUE"],
    )
    weak_hours = [x for x in hour_rank_pe if x["PURCHASE_EVENTS"] <= max(1, total_pe * 0.02)]
    dow_dist = [
        {
            "dow": DOW_NAMES[d],
            "PURCHASE_EVENTS": v["PURCHASE_EVENTS"],
            "TOTAL_PRICE_VALUE": round(v["TOTAL_PRICE_VALUE"], 2),
            "share_pct": round(100 * v["PURCHASE_EVENTS"] / total_pe, 2),
        }
        for d, v in sorted(by_dow.items())
    ]
    return {
        "buckets": bucket_rows,
        "totals": totals,
        "top_hours_by_PURCHASE_EVENTS": hour_rank_pe[:5],
        "top_hours_by_TOTAL_PRICE_VALUE": hour_rank_val[:5],
        "weak_hours": weak_hours[:8],
        "day_of_week_distribution": dow_dist,
        "purchase_event_share_by_hour": [
            {"hour_msk": x["hour_msk"], "share_pct": x["share_pct"]} for x in hour_rank_pe
        ],
        "bulk_adjusted_note": (
            "Hours dominated by single bulk_events (>=2 units) flagged in bucket bulk_events; "
            "not treated as strong temporal signal alone."
        ),
    }


def _temporal_signal_strength(pattern: dict[str, Any]) -> str:
    totals = pattern.get("totals") or {}
    pe = int(totals.get("PURCHASE_EVENTS") or 0)
    bulk_share = float(totals.get("bulk_unit_share_pct") or 0)
    if pe < 8:
        return "INSUFFICIENT_DATA"
    top = pattern.get("top_hours_by_PURCHASE_EVENTS") or []
    if not top:
        return "INSUFFICIENT_DATA"
    top_share = float(top[0].get("share_pct") or 0)
    if bulk_share >= 70 and pe < 20:
        return "WEAK"
    if top_share >= 25 and pe >= 20:
        return "STRONG"
    if top_share >= 15 or pe >= 15:
        return "MODERATE"
    return "WEAK"


def _client_designated_state() -> dict[str, Any]:
    """Authoritative client-designated SKU — project artifacts show GAP."""
    return {
        "CLIENT_DESIGNATED_NMID": "GAP",
        "EVIDENCE_SOURCE": (
            "scripts/a1_current_store_snapshot.py: NEW_SKU=GAP, OPEN_GAPS includes "
            "NEW_SKU_identification; TARGET_SKU=837395782 is deferred Search contour "
            f"(adv {DEFERRED_ADV}) not client handoff mapping"
        ),
        "CURRENT_AD_STATE": "GAP",
        "CURRENT_STOCK": "GAP",
        "SUBJECT_CATEGORY": "GAP",
        "CURRENT_PRICE": "GAP",
        "CURRENT_SPP": "GAP",
        "deferred_contour_note": {
            "nmID": 837395782,
            "adv_id": DEFERRED_ADV,
            "status": "DEFERRED_not_client_designated",
        },
    }


def _build_historical_demand(active: list[dict[str, Any]]) -> dict[str, Any]:
    store_groups: dict[str, list[dict[str, Any]]] = defaultdict(list)
    subject_groups: dict[str, dict[str, list[dict[str, Any]]]] = defaultdict(lambda: defaultdict(list))
    sku_groups: dict[int, dict[str, list[dict[str, Any]]]] = defaultdict(lambda: defaultdict(list))

    for row in active:
        gk = _g_key(row)
        dt = _msk_dt(row)
        if not dt:
            continue
        dow, hour = dt.weekday(), dt.hour
        key = (dow, hour)
        store_groups[gk].append(row)
        subj = str(row.get("subject") or "UNKNOWN")
        subject_groups[subj][gk].append(row)
        nmid = _read_int(row, "nmId", "nm_id", "nmid")
        if nmid:
            sku_groups[nmid][gk].append(row)

    def _store_cells_from_groups(gmap: dict[str, list[dict[str, Any]]]) -> list[dict[str, Any]]:
        cells: dict[tuple[int, int], dict[str, list[dict[str, Any]]]] = defaultdict(
            lambda: defaultdict(list)
        )
        for gk, rs in gmap.items():
            for r in rs:
                dt = _msk_dt(r)
                if not dt:
                    continue
                cells[(dt.weekday(), dt.hour)][gk].append(r)
        rows_out: list[dict[str, Any]] = []
        for (dow, hour), gm in sorted(cells.items()):
            m = _event_metrics(gm)
            skus = {
                s
                for rs in gm.values()
                for r in rs
                for s in [_read_int(r, "nmId", "nm_id", "nmid")]
                if s
            }
            rows_out.append({
                "dow": DOW_NAMES[dow], "hour_msk": hour, **m, "distinct_active_sku": len(skus),
            })
        return rows_out

    store_cells = _store_cells_from_groups(store_groups)
    subj_cells = {
        s: _store_cells_from_groups({gk: rs for gk, rs in subject_groups[s].items()})
        for s in sorted(subject_groups)
    }
    sku_cells = {
        n: _store_cells_from_groups({gk: rs for gk, rs in sku_groups[n].items()})
        for n in sorted(sku_groups)
    }

    coverage_days = sorted({ _order_day(r) for r in active })
    return {
        "model": {
            "UNITS": "non-cancelled raw rows",
            "PURCHASE_EVENTS": "distinct gNumber",
            "TOTAL_PRICE_VALUE": "sum totalPrice",
            "BULK_EVENT": "gNumber with >=2 units",
            "timestamp": "order date MSK",
        },
        "coverage": {
            "first_day": coverage_days[0] if coverage_days else None,
            "last_day": coverage_days[-1] if coverage_days else None,
            "closed_days": len(coverage_days),
        },
        "STORE": store_cells,
        "SUBJECT": subj_cells,
        "SKU": {str(k): v for k, v in sku_cells.items()},
    }


def _build_candidates(
    active: list[dict[str, Any]],
    ad_by_sku: dict[int, dict[str, Any]],
    wbcards: dict[int, dict[str, Any]],
    excluded: set[int],
    pg_idx: dict[int, dict[str, Any]],
    campaigns: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    sku_groups: dict[int, dict[str, list[dict[str, Any]]]] = defaultdict(lambda: defaultdict(list))
    spp_vals: dict[int, list[float]] = defaultdict(list)
    for row in active:
        nmid = _read_int(row, "nmId", "nm_id", "nmid")
        if not nmid:
            continue
        sku_groups[nmid][_g_key(row)].append(row)
        spp = _read_float(row, "spp")
        if spp > 0:
            spp_vals[nmid].append(spp)

    rows: list[dict[str, Any]] = []
    for nmid, gmap in sku_groups.items():
        m = _event_metrics(gmap)
        ad = ad_by_sku.get(nmid, {})
        card = wbcards.get(nmid, {})
        stock = card.get("stock")
        exclusion_reasons: list[str] = []
        if nmid in excluded:
            exclusion_reasons.append("ITER06_or_H1_contour")
        if nmid in BULK_HEAVY_NMIDS:
            exclusion_reasons.append("bulk_heavy_history")
        if stock is not None and stock <= 0:
            exclusion_reasons.append("blocking_stock_zero")
        if m["bulk_unit_share_pct"] >= 85 and m["PURCHASE_EVENTS"] <= 5:
            exclusion_reasons.append("bulk_dominated_volume")

        spend = float(ad.get("ad_spend_rub") or 0)
        pe = int(m["PURCHASE_EVENTS"])
        pe_per_spend = round(pe / spend, 4) if spend > 0 else None
        ad_state = _ad_state_for_nmid(nmid, pg_idx, campaigns)
        eligible = not exclusion_reasons and pe >= 3 and (stock is None or stock > 0)

        rank_score = pe * (1 - m["bulk_unit_share_pct"] / 100)
        if spend > 0:
            rank_score *= min(3.0, max(0.3, pe / max(spend / 100, 1)))
        else:
            rank_score *= 1.5

        rows.append({
            "nmID": nmid,
            "subject": card.get("subject") or next((str(r.get("subject") or "") for rs in gmap.values() for r in rs), ""),
            "category": card.get("category") or next((str(r.get("category") or "") for rs in gmap.values() for r in rs), ""),
            "stock": stock if stock is not None else "GAP",
            "price": card.get("price") or "GAP",
            "PURCHASE_EVENTS": pe,
            "UNITS": m["UNITS"],
            "TOTAL_PRICE_VALUE": m["TOTAL_PRICE_VALUE"],
            "bulk_unit_share_pct": m["bulk_unit_share_pct"],
            "units_per_event": m["units_per_event"],
            "ad_spend_rub": spend,
            "clicks": ad.get("clicks", 0),
            "attributed_orders": ad.get("attributed_orders", 0),
            "purchase_events_per_ad_spend": pe_per_spend,
            "current_ad_state": ad_state,
            "exclusion_reasons": exclusion_reasons,
            "growth_candidate_eligible": eligible,
            "_rank_score": round(rank_score, 3),
        })

    rows.sort(key=lambda x: (-x["_rank_score"], -x["PURCHASE_EVENTS"]))
    for i, r in enumerate(rows, 1):
        r["rank"] = i
    return rows


async def _fetch_cpc_min_bids(
    pm: Any, adv_id: int, nmid: int,
) -> dict[str, Any]:
    """POST /api/advert/v1/bids/min with payment_type=cpc (READ_ONLY)."""
    from app.core.mp.wb.api.adapter.promotion_client.min_bids.raw_response_to_dto import (
        convert as response_to_dto,
    )
    from app.core.mp.wb.api.adapter.raise_errors import with_raise_errors
    from app.core.mp.wb.api.generated.promotion.v2.marketing_and_promotions_client.api.sozdanie_kampanij.post_api_advert_v1_bids_min import (
        asyncio_detailed,
    )
    from app.core.mp.wb.api.generated.promotion.v2.marketing_and_promotions_client.models import (
        PostApiAdvertV1BidsMinBody,
        PostApiAdvertV1BidsMinBodyPaymentType,
        PostApiAdvertV1BidsMinBodyPlacementTypesItem,
        PostApiAdvertV1BidsMinResponse200,
    )
    from app.core.mp.wb.api.generated.promotion.v2.marketing_and_promotions_client.types import (
        Response,
    )

    adapter = pm._client.min_bids_adapter
    results: dict[str, Any] = {"adv_id": adv_id, "nmID": nmid, "endpoint": "POST /api/advert/v1/bids/min"}
    for placement, pt_item in (
        ("search", PostApiAdvertV1BidsMinBodyPlacementTypesItem.SEARCH),
        ("combined", PostApiAdvertV1BidsMinBodyPlacementTypesItem.COMBINED),
    ):
        body = PostApiAdvertV1BidsMinBody(
            advert_id=adv_id,
            nm_ids=[nmid],
            payment_type=PostApiAdvertV1BidsMinBodyPaymentType.CPC,
            placement_types=[pt_item],
        )
        try:
            client = await adapter.auth_client_handler.get_proxy_client(adapter)
            response: Response[PostApiAdvertV1BidsMinResponse200] = await with_raise_errors(
                asyncio_detailed,
                client,
                body=body,
            )
            parsed = response.parsed
            if parsed is None:
                results[f"min_bid_cpc_{placement}"] = None
            else:
                dto = response_to_dto(parsed)
                results[f"min_bid_cpc_{placement}"] = [
                    {"nmid": b.nmid, "placement": b.placement_type.value, "min_cpm": b.min_cpm}
                    for b in dto
                ]
        except Exception as exc:  # noqa: BLE001 — evidence capture
            results[f"min_bid_cpc_{placement}_error"] = str(exc)[:500]
    return results


async def _check_cpc_eligibility(
    pm: Any,
    nmids: list[int],
    campaigns: list[dict[str, Any]],
    pg_idx: dict[int, dict[str, Any]],
) -> dict[str, Any]:
    adv_nm = _adv_nm_map(campaigns)
    nm_to_adv = defaultdict(list)
    for adv, nms in adv_nm.items():
        for n in nms:
            nm_to_adv[n].append(adv)

    cpc_campaigns: list[dict[str, Any]] = []
    for c in campaigns:
        if _campaign_payment(c) == "cpc":
            adv = _read_int(c, "id", "advertId")
            cpc_campaigns.append({
                "adv_id": adv,
                "status": c.get("status"),
                "nmids": sorted(adv_nm.get(adv, ())),
                "placements": (c.get("settings") or {}).get("placements"),
            })

    per_sku: list[dict[str, Any]] = []
    for nmid in nmids:
        advs = nm_to_adv.get(nmid, [])
        search_adv = None
        for adv in advs:
            pg = pg_idx.get(adv, {})
            if pg.get("search_adv_id"):
                search_adv = pg.get("search_adv_id")
                break
        probe_adv = search_adv or (advs[0] if advs else None)
        entry: dict[str, Any] = {
            "nmID": nmid,
            "current_campaigns": advs,
            "cpc_campaigns_involving_nmid": [
                x for x in cpc_campaigns if nmid in x.get("nmids", [])
            ],
            "cpc_subject_category_eligibility": "UNKNOWN_WITHOUT_CREATE_PROBE",
        }
        if probe_adv:
            entry["min_bids_probe"] = await _fetch_cpc_min_bids(pm, probe_adv, nmid)
            entry["probe_adv_id"] = probe_adv
        else:
            entry["min_bids_probe"] = "GAP_no_campaign_for_probe"
        per_sku.append(entry)

    return {
        "CPC_ELIGIBLE_SKUS": per_sku,
        "existing_cpc_campaigns": cpc_campaigns,
        "CPC_API_CONTROL_CAPABILITIES": {
            "create_campaign": {
                "endpoint": "POST /api/advert/v2/seacat/save/ad",
                "writable_via_api": "YES_documented",
                "executed_here": "NO",
            },
            "manage_bids": {
                "endpoints": [
                    "POST /api/advert/v1/bids/min",
                    "PATCH /adv/v0/auction/bids (auction)",
                    "cluster bid managers in shop-runner",
                ],
                "cpc_bid_management": "YES_via_promotion_API",
                "executed_here": "NO",
            },
            "daily_limit": {
                "pg_fields": [
                    "advsetting.auto_budget_daily_limit",
                    "advsetting.search_auto_budget_daily_limit",
                    "advsetting.common_budget_daily_limit",
                ],
                "bot_route": "shop-runner watchdog deposits + PG limits",
                "wb_api_direct_daily_limit": "PARTIAL_campaign_budget_total_via_promotion_API",
                "cabinet_ui_may_be_required": "for_some_CPC_topologies",
            },
            "payment_model_change": "FORBIDDEN_IN_THIS_PACKET",
        },
        "DAILY_LIMIT_CONTROL_ROUTE": (
            "Primary: PG advsetting daily limit fields consumed by shop-runner; "
            "WB campaign budget.total for spend cap; CPC-specific limit surface may "
            "require cabinet UI for fields not exposed in readonly probes"
        ),
        "CURRENT_CAMPAIGN_CONFLICTS": (
            "Simultaneous CPM auto/search legs + deferred 34210859 + Iter06 pairs "
            "may constrain CPC topology; per-SKU campaign list in CPC_ELIGIBLE_SKUS"
        ),
    }


def _cpc_observability() -> dict[str, Any]:
    return {
        "post_launch_metrics": {
            "clicks": {"source": "WB_API", "endpoint": "/adv/v3/fullstats, /adv/v0/normquery/stats", "available": "YES"},
            "spend": {"source": "WB_API", "endpoint": "/adv/v3/fullstats", "available": "YES"},
            "CPC": {"source": "WB_API", "endpoint": "derived spend/clicks", "available": "YES"},
            "carts": {"source": "WB_API", "endpoint": "fullstats atb (if present)", "available": "PARTIAL"},
            "attributed_orders": {"source": "WB_API", "endpoint": "/adv/v3/fullstats orders", "available": "YES"},
            "attributed_value": {"source": "WB_API", "endpoint": "/adv/v3/fullstats sum_price", "available": "YES"},
            "normquery_cluster_stats": {
                "source": "WB_API",
                "endpoint": "POST /adv/v0/normquery/stats",
                "available": "YES_search_leg",
            },
            "hourly_data": {
                "source": "BOT_TELEMETRY",
                "endpoint": "CH bid_decision_log / runtime ticks",
                "available": "PARTIAL_not_full_WB_hourly",
            },
            "views_CTR": {
                "source": "WB_API",
                "endpoint": "/adv/v3/fullstats views",
                "available": "CPM_primary",
                "cpc_limitation": "CPC may not expose views/CTR via same surfaces — API limitation, not collector GAP",
            },
        },
    }


async def fetch_wb(root: Path) -> tuple[list, list, list, Any]:
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
        budget = ApiCallBudget(max_seconds=1800.0, max_api_calls=1500)
        rm = getattr(dm, "reports_manager", None)

        async def fetch_ord(df: str) -> list[object]:
            if rm:
                return list(await rm.get_supplier_orders(date_from=df, flag=0) or [])
            return list(await dm.get_supplier_orders(date_from=df, flag=0) or [])

        orders_res = await _paginate_supplier_rows(
            fetch=fetch_ord,
            initial_date_from=PERIOD_FROM.isoformat(),
            budget=budget,
            max_pages=1200,
        )
        budget.consume()
        adv_ids = list(await pm._client.promotion_count_adapter.get_cabinet_adv_ids() or [])
        budget.consume()
        camps_raw = list(await pm.get_adverts_v2_by_ids(adv_ids) or [])
        campaigns = [jsonable(x) for x in camps_raw if isinstance(jsonable(x), dict)]

        dates = []
        d = PERIOD_FROM
        while d <= PERIOD_TO:
            dates.append(d)
            d += timedelta(days=1)
        budget.consume()
        stats_raw = await pm.get_full_adv_stat(adv_ids, dates)
        fullstats = _flatten_fullstats(list(stats_raw or []))
        return orders_res.rows, campaigns, fullstats, pm
    finally:
        await httpx.shutdown()
        await redis_raw.aclose()


def build(
    checked: datetime,
    orders: list[dict[str, Any]],
    campaigns: list[dict[str, Any]],
    fullstats: list[dict[str, Any]],
    pg: list[dict[str, str]],
    cpc_eligibility: dict[str, Any],
    wbcards: dict[int, dict[str, Any]],
) -> dict[str, Any]:
    gaps: list[str] = []
    pg_idx = _pg_adv_index(pg)
    excluded = _excluded_nmids(pg_idx)
    active = _active_period_orders(orders)
    adv_nm = _adv_nm_map(campaigns)
    ad_by_sku = _aggregate_ad_by_sku(fullstats, adv_nm)

    client = _client_designated_state()
    historical = _build_historical_demand(active)
    if historical["coverage"]["closed_days"] < 28:
        gaps.append(f"orders_coverage_days={historical['coverage']['closed_days']}_lt_28")

    candidates = _build_candidates(active, ad_by_sku, wbcards, excluded, pg_idx, campaigns)
    eligible = [c for c in candidates if c.get("growth_candidate_eligible")]
    top = [c for c in eligible if not c.get("exclusion_reasons")][:8]
    if not top:
        top = [c for c in candidates if not c.get("exclusion_reasons")][:8]

    store_temporal = _temporal_buckets(active)
    store_strength = _temporal_signal_strength(store_temporal)

    sku_temporal: dict[str, Any] = {}
    category_temporal: dict[str, Any] = {}
    for c in top[:5]:
        nmid = int(c["nmID"])
        pat = _temporal_buckets(active, nmid=nmid)
        sku_temporal[str(nmid)] = {**pat, "TEMPORAL_SIGNAL_STRENGTH": _temporal_signal_strength(pat)}
        subj = str(c.get("subject") or "")
        if subj and subj not in category_temporal:
            cp = _temporal_buckets(active, subject_key=subj)
            category_temporal[subj] = {**cp, "TEMPORAL_SIGNAL_STRENGTH": _temporal_signal_strength(cp)}

    ad_history = {
        "source_layers": {
            "WB_API": {
                "endpoints": ["/adv/v3/fullstats", "/api/advert/v2/adverts"],
                "fields": ["spend", "clicks", "views", "orders", "sum_price", "date"],
            },
            "BOT_TELEMETRY": {
                "note": "hourly bid_decision_log not collected in this packet",
                "status": "GAP_optional_followup",
            },
        },
        "period": f"{PERIOD_FROM.isoformat()}..{PERIOD_TO.isoformat()}",
        "sku_ad_totals": {str(k): v for k, v in ad_by_sku.items()},
    }

    if not wbcards:
        gaps.append("wbcard_stock_price_GAP")

    return {
        "CHECKED_AT_MSK": checked.strftime("%Y-%m-%d %H:%M:%S %Z"),
        "HISTORICAL_PERIOD": {
            "from": PERIOD_FROM.isoformat(),
            "to": PERIOD_TO.isoformat(),
            "closed_days_target": 28,
            "actual_coverage": historical["coverage"],
        },
        "CLIENT_DESIGNATED_NMID": client["CLIENT_DESIGNATED_NMID"],
        "CLIENT_DESIGNATED_SKU_STATE": client,
        "HISTORICAL_DEMAND_DATASET": historical,
        "ADVERTISING_HISTORY": ad_history,
        "GROWTH_CANDIDATE_TABLE": candidates,
        "TOP_CANDIDATES": [c["nmID"] for c in top[:5]],
        "STORE_TEMPORAL_PATTERN": {**store_temporal, "level": "STORE"},
        "CATEGORY_TEMPORAL_PATTERN": category_temporal,
        "SKU_TEMPORAL_PATTERN": sku_temporal,
        "TEMPORAL_SIGNAL_STRENGTH": {
            "STORE": store_strength,
            "TOP_SKU": {k: v.get("TEMPORAL_SIGNAL_STRENGTH") for k, v in sku_temporal.items()},
        },
        "CPC_ELIGIBLE_SKUS": cpc_eligibility.get("CPC_ELIGIBLE_SKUS"),
        "CPC_MIN_BIDS": [
            x.get("min_bids_probe") for x in cpc_eligibility.get("CPC_ELIGIBLE_SKUS", [])
        ],
        "CPC_API_CONTROL_CAPABILITIES": cpc_eligibility.get("CPC_API_CONTROL_CAPABILITIES"),
        "DAILY_LIMIT_CONTROL_ROUTE": cpc_eligibility.get("DAILY_LIMIT_CONTROL_ROUTE"),
        "CURRENT_CAMPAIGN_CONFLICTS": cpc_eligibility.get("CURRENT_CAMPAIGN_CONFLICTS"),
        "CPC_OBSERVABILITY": _cpc_observability(),
        "DATA_GAPS": gaps,
        "NO_WRITES": "CONFIRMED",
        "EXCLUSIONS_APPLIED": {
            "ITER06_NMIDS": sorted(ITER06_NMIDS),
            "H1_PHYSICAL_ADV": sorted(H1_PHYSICAL),
            "H1_NMIDS": sorted(_h1_nmids(pg_idx)),
            "DEFERRED_ADV": DEFERRED_ADV,
        },
    }


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--output-dir", default=".tmp/a1_cpc_growth_prep")
    args = ap.parse_args(argv)
    root = Path(args.output_dir).resolve()
    root.mkdir(parents=True, exist_ok=True)
    _bootstrap()
    pg = _load_pg_adv(root)

    async def _run() -> dict[str, Any]:
        orders, campaigns, fullstats, pm = await fetch_wb(root)
        checked = datetime.now(MSK)
        active = _active_period_orders(orders)
        nmids_set = {_read_int(r, "nmId", "nm_id", "nmid") for r in active}
        nmids_set.discard(None)
        wbcards = _load_wbcards(root, nmids_set)

        pg_idx = _pg_adv_index(pg)
        excluded = _excluded_nmids(pg_idx)
        adv_nm = _adv_nm_map(campaigns)
        ad_by_sku = _aggregate_ad_by_sku(fullstats, adv_nm)
        candidates_pre = _build_candidates(active, ad_by_sku, wbcards, excluded, pg_idx, campaigns)
        top_nmids = [int(c["nmID"]) for c in candidates_pre if not c.get("exclusion_reasons")][:6]

        cpc_eligibility = await _check_cpc_eligibility(pm, top_nmids, campaigns, pg_idx)

        payload = build(checked, orders, campaigns, fullstats, pg, cpc_eligibility, wbcards)
        payload["GROWTH_CANDIDATE_TABLE"] = _build_candidates(
            active, ad_by_sku, wbcards, excluded, pg_idx, campaigns,
        )

        pkg = root / PACKAGE
        pkg.mkdir(parents=True, exist_ok=True)
        (pkg / f"{PACKAGE}.json").write_text(
            json.dumps(payload, ensure_ascii=False, indent=2, default=str), encoding="utf-8",
        )
        ct = payload["GROWTH_CANDIDATE_TABLE"]
        if ct:
            cols = [k for k in ct[0] if not k.startswith("_")]
            _write_csv(pkg / "GROWTH_CANDIDATE_TABLE.csv", ct, cols)
        return payload

    out = asyncio.run(_run())
    summary = {k: v for k, v in out.items() if k not in ("GROWTH_CANDIDATE_TABLE", "HISTORICAL_DEMAND_DATASET", "SKU_TEMPORAL_PATTERN")}
    summary["GROWTH_CANDIDATE_COUNT"] = len(out.get("GROWTH_CANDIDATE_TABLE", []))
    print(json.dumps(summary, ensure_ascii=False, indent=2, default=str))
    return 0


if __name__ == "__main__":
    sys.exit(main())
