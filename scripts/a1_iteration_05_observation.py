"""READ_ONLY: A1 Iteration-05 post-change observation packet (01.09 closed day).

Daily-cap patch EXECUTED/VERIFIED — observation only, no production mutations.
"""

from __future__ import annotations

import argparse
import asyncio
import csv
import json
import os
import re
import statistics
import sys
from collections import defaultdict
from datetime import date, datetime
from pathlib import Path
from typing import Any
from zoneinfo import ZoneInfo

import dotenv

dotenv.load_dotenv()

from scripts import ch_a1_evidence as evidence
from scripts.wb_a1_associated_conversions import _read_float, _read_int
from scripts.wb_api_readonly_ops.collect.ads import _flatten_fullstats
from scripts.wb_api_readonly_ops.collect.api_budget import ApiCallBudget
from scripts.wb_api_readonly_ops.collect.orders_sales import _paginate_supplier_rows

SHOP_ID = "5339e9ad-cbfe-50fc-8d77-b9f337a80417"
MSK = ZoneInfo("Europe/Moscow")
PACKAGE = "A1-ITERATION-05-OBSERVATION-PACKET"
TARGET_DAY = date(2026, 9, 1)
TARGET_STR = TARGET_DAY.isoformat()
NOMINAL_CAP_SUM = 4900

ITER04_EXPECTED: dict[int, tuple[int, int]] = {
    17728892: (200, 150),
    17906286: (0, 450),
    20987867: (500, 200),
    21542370: (300, 50),
    21604339: (0, 350),
    25174753: (200, 300),
    25183231: (250, 200),
    25338885: (150, 450),
    37236815: (100, 400),
    37096258: (200, 100),
    37289966: (250, 100),
}
H1_AUTO = [17906286, 21604339]
H1_SEARCH = [20646357, 21604374]
H1_SEARCH_LIMITS = {20646357: 450, 21604374: 350}
FOCUS_SKUS = (837395782, 195764899)
DEFERRED_ADV = 34210859

BASELINE = {
    "2026-08-27": {"units": 22, "purchase_events": 16, "TOTAL_PRICE_VALUE": 57495, "ad_spend": 4389.24},
    "2026-08-28": {"units": 23, "purchase_events": 18, "TOTAL_PRICE_VALUE": 59716, "ad_spend": 3884.39},
    "2026-08-29": {"units": 31, "purchase_events": 21, "TOTAL_PRICE_VALUE": 85194, "ad_spend": 4147.83},
    "2026-08-30": {"units": 28, "purchase_events": 13, "TOTAL_PRICE_VALUE": 89389, "ad_spend": 3938.47},
    "2026-08-31": {"units": 38, "purchase_events": 25, "TOTAL_PRICE_VALUE": 112375, "ad_spend": 3678.31},
}

PG_FIELDS = [
    "id", "adv_id", "_search_adv_id", "name", "nmids", "active_status", "bot_active",
    "auto_budget_watchdog_enabled", "auto_budget_daily_limit",
    "search_auto_budget_daily_limit", "use_common_budget", "common_budget_daily_limit",
]
NAME_SEARCH = re.compile(r"<!-\[(\d+)\]-!>")


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


def _load_pg(root: Path) -> list[dict[str, str]]:
    staging = root / "staging"
    staging.mkdir(parents=True, exist_ok=True)
    out = staging / "pg.csv"
    cols = ", ".join(f"a.{c}" for c in PG_FIELDS)
    q = (
        f"SELECT {cols} FROM public.advsetting a "
        f"JOIN public.wbcabinet c ON a.wb_cabinet_id = c.id "
        f"WHERE c.shop_id = '{SHOP_ID}'"
    )
    st = evidence.run_pg_query(_pg_db(), q, out, root / "sql" / "pg.sql", csv_output=True)
    if not st["success"]:
        raise RuntimeError(st["stderr"])
    with out.open(encoding="utf-8", newline="") as f:
        return list(csv.DictReader(f))


def _int_lim(v: Any) -> int:
    try:
        return int(float(v or 0))
    except (TypeError, ValueError):
        return 0


def _parse_nmids(raw: str) -> list[int]:
    if not raw:
        return []
    try:
        val = json.loads(raw.replace("'", '"'))
        return [int(x) for x in val if str(x).isdigit()] if isinstance(val, list) else []
    except json.JSONDecodeError:
        return []


def _resolved_search(row: dict[str, str]) -> int | None:
    raw = (row.get("_search_adv_id") or "").strip()
    if raw.isdigit() and int(raw) > 0:
        return int(raw)
    m = NAME_SEARCH.search((row.get("name") or "").replace(" ", ""))
    return int(m.group(1)) if m else None


def _order_day(r: dict[str, Any]) -> str:
    return str(r.get("date") or "")[:10]


def _cancelled(r: dict[str, Any]) -> bool:
    return str(r.get("isCancel")).lower() in ("true", "1", "t")


def _gkey(r: dict[str, Any]) -> str:
    g = str(r.get("gNumber") or "").strip()
    return g or f"srid:{r.get('srid')}"


def _redis_reason(adv_id: int, leg: str) -> dict[str, Any]:
    key = f"campaign-activity-reason:{adv_id}:{leg}"
    raw = ""
    try:
        import redis
        host = os.environ.get("REDIS_HOST") or os.environ.get("REDIS_MASTER_HOST")
        if host:
            c = redis.Redis(
                host=host, port=int(os.environ.get("REDIS_PORT", "6379")),
                password=os.environ.get("REDIS_PASSWORD"),
                db=int(os.environ.get("REDIS_DB", "0")), decode_responses=True,
            )
            raw = c.get(key) or ""
    except Exception:
        pass
    parsed = None
    if raw:
        try:
            parsed = json.loads(raw)
        except json.JSONDecodeError:
            parsed = {"raw": raw}
    return {"key": key, "parsed": parsed}


def _write_csv(path: Path, rows: list[dict[str, Any]], cols: list[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=cols, extrasaction="ignore")
        w.writeheader()
        for r in rows:
            w.writerow({c: r.get(c, "") for c in cols})


def _limits_check(pg_by_adv: dict[int, dict[str, str]]) -> dict[str, Any]:
    rows = []
    ok = True
    for auto_id, (exp_a, exp_s) in sorted(ITER04_EXPECTED.items()):
        row = pg_by_adv.get(auto_id, {})
        act_a = _int_lim(row.get("auto_budget_daily_limit"))
        act_s = _int_lim(row.get("search_auto_budget_daily_limit"))
        match = act_a == exp_a and act_s == exp_s
        ok = ok and match
        rows.append({
            "auto_adv_id": auto_id,
            "advsetting_id": row.get("id", "GAP"),
            "expected_auto_cap": exp_a,
            "expected_search_cap": exp_s,
            "actual_auto_cap": act_a,
            "actual_search_cap": act_s,
            "match": match,
        })
    return {"LIMITS_MATCH": "YES" if ok else "NO", "NOMINAL_CAP": NOMINAL_CAP_SUM, "rows": rows}


def _physical_rows(
    pg_by_adv: dict[int, dict[str, str]],
    stats: dict[tuple[int, str], dict[str, Any]],
    inv: dict[int, dict[str, Any]],
) -> list[dict[str, Any]]:
    search_parent: dict[int, dict[str, str]] = {}
    search_to_auto: dict[int, int] = {}
    for aid, row in pg_by_adv.items():
        sid = _resolved_search(row)
        if sid:
            search_parent[sid] = row
            search_to_auto[sid] = aid

    phys: dict[int, dict[str, Any]] = {}
    for auto_id, row in pg_by_adv.items():
        if str(row.get("bot_active")).lower() not in ("true", "t", "1"):
            continue
        nmid = (_parse_nmids(row.get("nmids") or "") or [None])[0]
        phys[auto_id] = {
            "physical_adv_id": auto_id, "leg_type": "Auto",
            "parent_adv_setting_id": row.get("id"), "nmID": nmid or "",
            "daily_cap": _int_lim(row.get("auto_budget_daily_limit")),
            "active_status": row.get("active_status"),
        }
        sid = _resolved_search(row)
        if sid and sid not in phys:
            pr = search_parent.get(sid, row)
            phys[sid] = {
                "physical_adv_id": sid, "leg_type": "Search",
                "parent_adv_setting_id": pr.get("id"), "nmID": nmid or "",
                "daily_cap": _int_lim(pr.get("search_auto_budget_daily_limit")),
                "active_status": pg_by_adv.get(sid, {}).get("active_status", ""),
            }

    out: list[dict[str, Any]] = []
    for adv_id, meta in phys.items():
        st = stats.get((adv_id, TARGET_STR), {})
        spend = round(float(st.get("spend") or 0), 2)
        views = int(st.get("views") or 0)
        clicks = int(st.get("clicks") or 0)
        lim = int(meta["daily_cap"] or 0)
        cap_pct = round(100 * spend / lim, 2) if lim > 0 else (0 if spend == 0 else "OVERSHOOT_NO_CAP")
        leg = "auto" if meta["leg_type"] == "Auto" else "search"
        rr = _redis_reason(adv_id, leg)
        parsed = rr.get("parsed") or {}
        out.append({
            "parent_adv_setting_id": meta["parent_adv_setting_id"],
            "physical_adv_id": adv_id,
            "leg_type": meta["leg_type"],
            "nmID": meta["nmID"],
            "daily_cap_rub": lim,
            "actual_spend_rub": spend,
            "cap_consumption_pct": cap_pct,
            "views": views,
            "clicks": clicks,
            "ctr_pct": round(100 * clicks / views, 4) if views else 0,
            "cpc_rub": round(spend / clicks, 4) if clicks else "",
            "attributed_orders": int(st.get("orders") or 0),
            "attributed_gmv_rub": round(float(st.get("gmv") or 0), 2),
            "wb_status": inv.get(adv_id, {}).get("wb_status", ""),
            "runtime_active_status": meta["active_status"],
            "pause_reason_code": parsed.get("reason_code", "GAP"),
            "runtime_command": parsed.get("command", "GAP"),
            "reason_updated_at": parsed.get("updated_at", "GAP"),
        })
    out.sort(key=lambda r: -float(r["actual_spend_rub"] or 0))
    return out


def _cap_behaviour(physical: list[dict[str, Any]]) -> dict[str, Any]:
    hit, near, under, major, overshoot = [], [], [], [], []
    for r in physical:
        lim = int(r.get("daily_cap_rub") or 0)
        spend = float(r.get("actual_spend_rub") or 0)
        if lim <= 0:
            continue
        pct = 100 * spend / lim
        entry = {
            "physical_adv_id": r["physical_adv_id"],
            "leg_type": r["leg_type"],
            "cap_rub": lim,
            "spend_rub": spend,
            "cap_pct": round(pct, 2),
            "pause_reason_code": r.get("pause_reason_code"),
            "reason_updated_at": r.get("reason_updated_at"),
        }
        if spend > lim:
            overshoot.append({**entry, "overshoot_rub": round(spend - lim, 2),
                              "overshoot_pct": round(100 * (spend - lim) / lim, 2)})
        elif spend >= lim:
            hit.append(entry)
        elif pct >= 80:
            near.append(entry)
        elif pct < 20:
            major.append(entry)
        elif pct < 50:
            under.append(entry)
    return {
        "CAPS_HIT": hit,
        "CAPS_NEAR_HIT": near,
        "UNDERSPEND": under,
        "MAJOR_UNDERSPEND": major,
        "OVERSHOOT": overshoot,
    }


def _store_day(orders: list[dict[str, Any]]) -> dict[str, Any]:
    rows = [r for r in orders if _order_day(r) == TARGET_STR and not _cancelled(r)]
    groups: dict[str, list] = defaultdict(list)
    for r in rows:
        groups[_gkey(r)].append(r)
    sku_units: dict[int, list] = defaultdict(list)
    for r in rows:
        nmid = _read_int(r, "nmId", "nm_id")
        if nmid:
            sku_units[nmid].append(r)

    stp = round(sum(_read_float(r, "totalPrice") for r in rows), 2)
    spd = round(sum(_read_float(r, "priceWithDisc") for r in rows), 2)
    fp = round(sum(_read_float(r, "finishedPrice") for r in rows), 2)
    units = len(rows)
    events = len(groups)
    bulk_groups = [g for g in groups.values() if len(g) >= 2]
    bulk_units = sum(len(g) for g in bulk_groups)
    sizes = sorted((len(g) for g in groups.values()), reverse=True)
    top1 = sizes[0] if sizes else 0
    top3 = sum(sizes[:3])
    top1_tp = round(sum(_read_float(r, "totalPrice") for r in (sizes and list(groups.values())[0] or [])), 2)
    # fix top1 tp
    ranked = sorted(groups.items(), key=lambda x: -len(x[1]))
    top1_tp = round(sum(_read_float(r, "totalPrice") for r in ranked[0][1]), 2) if ranked else 0
    top3_tp = round(sum(_read_float(r, "totalPrice") for _, m in ranked[:3] for r in m), 2)

    sku_stats = []
    for nmid, rs in sku_units.items():
        gs = defaultdict(list)
        for r in rs:
            gs[_gkey(r)].append(r)
        sku_stats.append({
            "nmID": nmid, "units": len(rs), "purchase_events": len(gs),
            "units_per_event": round(len(rs) / len(gs), 2) if gs else 0,
            "max_bulk_event": max((len(v) for v in gs.values()), default=0),
            "TOTAL_PRICE_VALUE": round(sum(_read_float(r, "totalPrice") for r in rs), 2),
            "FINISHED_PRICE_VALUE": round(sum(_read_float(r, "finishedPrice") for r in rs), 2),
        })

    return {
        "STORE_UNITS": units,
        "STORE_PURCHASE_EVENTS": events,
        "UNITS_PER_EVENT": round(units / events, 2) if events else 0,
        "TOTAL_PRICE_VALUE": stp,
        "PRICE_WITH_DISC_VALUE": spd,
        "FINISHED_PRICE_VALUE": fp,
        "distinct_SKU_with_units": len(sku_units),
        "distinct_SKU_with_purchase_events": len(sku_units),
        "BULK_EVENT_COUNT": len(bulk_groups),
        "BULK_UNIT_SHARE": round(100 * bulk_units / units, 2) if units else 0,
        "MAX_EVENT_SIZE": max(sizes) if sizes else 0,
        "PURCHASE_EVENT_CONCENTRATION": {
            "top1_event_units": top1,
            "top3_events_units": top3,
            "top1_share_units_pct": round(100 * top1 / units, 2) if units else 0,
            "top3_share_units_pct": round(100 * top3 / units, 2) if units else 0,
            "top1_share_TOTAL_PRICE_pct": round(100 * top1_tp / stp, 2) if stp else 0,
            "top3_share_TOTAL_PRICE_pct": round(100 * top3_tp / stp, 2) if stp else 0,
        },
        "sku_stats": sku_stats,
    }


def _adv_nm_map(campaigns: list[dict[str, Any]]) -> dict[int, set[int]]:
    out: dict[int, set[int]] = defaultdict(set)
    for c in campaigns:
        aid = _read_int(c, "id", "advertId")
        for nm in c.get("nm_settings") or c.get("nmSettings") or []:
            if isinstance(nm, dict):
                nid = _read_int(nm, "nm_id", "nmId", "nmID")
                if nid:
                    out[aid].add(nid)
    return out


def _attach_sku_ad(sku_stats: list[dict[str, Any]], fullstats: list[dict[str, Any]],
                   campaigns: list[dict[str, Any]]) -> list[dict[str, Any]]:
    adv_nm = _adv_nm_map(campaigns)
    nm_advs: dict[int, set[int]] = defaultdict(set)
    for aid, nms in adv_nm.items():
        for n in nms:
            nm_advs[n].add(aid)
    for st in sku_stats:
        nmid = st["nmID"]
        spend = clicks = attr = 0.0
        for row in fullstats:
            if str(row.get("date") or "")[:10] != TARGET_STR:
                continue
            aid = _read_int(row, "advertId", "advert_id")
            if aid in nm_advs.get(nmid, set()):
                spend += _read_float(row, "sum", "spend")
                clicks += _read_int(row, "clicks")
                attr += _read_int(row, "orders")
        st["ad_spend_rub"] = round(spend, 2)
        st["ad_clicks"] = int(clicks)
        st["attributed_orders"] = int(attr)
    return sku_stats


def _funnel_store(funnel_rows: list[dict[str, Any]]) -> dict[str, Any]:
    oc = carts = fo = fov = 0.0
    has = False
    for row in funnel_rows:
        day = str(row.get("day") or row.get("date") or "")[:10]
        if day != TARGET_STR:
            continue
        has = True
        oc += _read_float(row, "open_card", "openCard", "openCardCount")
        carts += _read_float(row, "add_to_cart", "addToCart", "cartCount", "addToCartCount")
        fo += _read_float(row, "orders", "orderCount", "ordersCount")
        fov += _read_float(row, "orders_sum", "orderSum", "orderSumRub")
    if not has:
        return {"state": "GAP", "openCard": "GAP", "carts": "GAP", "funnel_orders": "GAP", "funnel_order_value": "GAP"}
    return {
        "state": "AVAILABLE",
        "openCard": oc,
        "carts": carts,
        "funnel_orders": fo,
        "funnel_order_value_rub": round(fov, 2),
    }


async def fetch_all(root: Path) -> tuple[list, list, list, list]:
    import datetime as dt
    from app.configs.app_config import AppConfig
    from app.core.di.wb_manager_hub.wb_manager_hub_factory import WBManagerHubFactory
    from app.core.mp.wb.api.httpx_client_handler import HttpxClientHandler
    from app.core.redis_manager_v2.redis_client import RedisClient
    from app.modules.common_slaves.wildberries.super_cabinet_manager import get_access_for_wb_cabinet
    from redis.asyncio import Redis
    from scripts.wb_api_readonly_ops.collect.funnel import collect_funnel
    from scripts.wb_api_readonly_ops.collect.jsonable import jsonable
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
        budget = ApiCallBudget(max_seconds=1200.0, max_api_calls=1200)
        rm = getattr(dm, "reports_manager", None)

        async def fetch_ord(df: str) -> list[object]:
            if rm:
                return list(await rm.get_supplier_orders(date_from=df, flag=0) or [])
            return list(await dm.get_supplier_orders(date_from=df, flag=0) or [])

        orders_res = await _paginate_supplier_rows(
            fetch=fetch_ord, initial_date_from="2026-08-30", budget=budget, max_pages=800,
        )
        budget.consume()
        adv_ids = list(await pm._client.promotion_count_adapter.get_cabinet_adv_ids() or [])
        budget.consume()
        camps_raw = list(await pm.get_adverts_v2_by_ids(adv_ids) or [])
        campaigns = [jsonable(x) for x in camps_raw if isinstance(jsonable(x), dict)]
        budget.consume()
        stats_raw = await pm.get_full_adv_stat(adv_ids, [TARGET_DAY])
        fullstats = _flatten_fullstats(list(stats_raw or []))

        nmids = list({_read_int(r, "nmId", "nm_id") for r in orders_res.rows if _read_int(r, "nmId", "nm_id")})
        funnel_rows: list[dict[str, Any]] = []
        if nmids:
            store = RawStore(root / "collect_raw")
            try:
                funnel_rows = await collect_funnel(
                    wb_data_manager=dm, store=store, budget=budget,
                    nmids=nmids[:200], date_from=TARGET_DAY, date_to=TARGET_DAY,
                )
            except Exception:
                funnel_rows = []

        return orders_res.rows, campaigns, fullstats, funnel_rows
    finally:
        await httpx.shutdown()
        await redis_raw.aclose()


def build(checked: datetime, pg_rows: list[dict[str, str]],
          orders: list, campaigns: list, fullstats: list, funnel: list) -> dict[str, Any]:
    gaps: list[str] = []
    eligible = checked.date() > TARGET_DAY
    day_state = "CLOSED" if eligible else "OPEN_PARTIAL"

    if not eligible:
        return {
            "OBSERVATION_PACKET": "NOT_ELIGIBLE",
            "reason": f"{TARGET_STR} not fully closed at CHECKED_AT_MSK={checked}",
            "CHECKED_AT_MSK": checked.strftime("%Y-%m-%d %H:%M:%S %Z"),
        }

    pg_by_adv: dict[int, dict[str, str]] = {}
    for row in pg_rows:
        try:
            aid = int(row.get("adv_id") or 0)
        except (TypeError, ValueError):
            continue
        if aid:
            pg_by_adv[aid] = row

    limits = _limits_check(pg_by_adv)
    stats: dict[tuple[int, str], dict[str, Any]] = {}
    for row in fullstats:
        aid = _read_int(row, "advertId", "advert_id")
        day = str(row.get("date") or "")[:10]
        if day != TARGET_STR or not aid:
            continue
        b = stats.setdefault((aid, day), {"spend": 0, "views": 0, "clicks": 0, "orders": 0, "gmv": 0.0})
        b["spend"] += _read_float(row, "sum", "spend")
        b["views"] += _read_int(row, "views")
        b["clicks"] += _read_int(row, "clicks")
        b["orders"] += _read_int(row, "orders")
        b["gmv"] += _read_float(row, "sum_price")

    inv: dict[int, dict[str, Any]] = {}
    for c in campaigns:
        aid = _read_int(c, "id", "advertId")
        if aid:
            inv[aid] = {"wb_status": c.get("status")}

    physical = _physical_rows(pg_by_adv, stats, inv)
    caps = _cap_behaviour(physical)
    store = _store_day(orders)
    sku_stats = _attach_sku_ad(store.pop("sku_stats"), fullstats, campaigns)

    ad_total = {
        "total_ad_spend_rub": round(
            sum(
                _read_float(row, "sum", "spend")
                for row in fullstats
                if str(row.get("date") or "")[:10] == TARGET_STR
            ),
            2,
        ),
        "physical_campaigns_with_spend_gt_0": sum(
            1 for r in physical if float(r["actual_spend_rub"] or 0) > 0
        ),
        "views": sum(int(r["views"] or 0) for r in physical),
        "clicks": sum(int(r["clicks"] or 0) for r in physical),
        "attributed_orders": sum(int(r["attributed_orders"] or 0) for r in physical),
        "attributed_gmv_rub": round(sum(float(r["attributed_gmv_rub"] or 0) for r in physical), 2),
    }
    v = ad_total["views"]
    c = ad_total["clicks"]
    ad_total["ctr_pct"] = round(100 * c / v, 4) if v else 0
    ad_total["cpc_rub"] = round(ad_total["total_ad_spend_rub"] / c, 4) if c else "GAP"

    stp = store["TOTAL_PRICE_VALUE"]
    ad_total["AD_SPEND_SHARE_TOTAL_PRICE_pct"] = round(100 * ad_total["total_ad_spend_rub"] / stp, 2) if stp else "GAP"
    ad_total["spend_over_PRICE_WITH_DISC_pct"] = round(
        100 * ad_total["total_ad_spend_rub"] / store["PRICE_WITH_DISC_VALUE"], 2
    ) if store["PRICE_WITH_DISC_VALUE"] else "GAP"
    ad_total["spend_over_FINISHED_PRICE_pct"] = round(
        100 * ad_total["total_ad_spend_rub"] / store["FINISHED_PRICE_VALUE"], 2
    ) if store["FINISHED_PRICE_VALUE"] else "GAP"

    h1_rows = []
    for aid in H1_AUTO:
        r = next((x for x in physical if x["physical_adv_id"] == aid), {})
        h1_rows.append({"adv_id": aid, "leg": "Auto", "expected_cap": 0, **{
            k: r.get(k, "GAP") for k in ("actual_spend_rub", "views", "clicks", "pause_reason_code", "runtime_command")
        }})
    for aid in H1_SEARCH:
        r = next((x for x in physical if x["physical_adv_id"] == aid), {})
        h1_rows.append({
            "adv_id": aid, "leg": "Search", "expected_limit": H1_SEARCH_LIMITS[aid],
            "actual_spend_rub": r.get("actual_spend_rub", 0),
            "views": r.get("views", 0), "clicks": r.get("clicks", 0),
            "attributed_orders": r.get("attributed_orders", 0),
            "pause_reason_code": r.get("pause_reason_code", "GAP"),
            "runtime_active_status": r.get("runtime_active_status", "GAP"),
        })

    funnel_state = _funnel_store(funnel)
    if funnel_state.get("state") == "GAP":
        gaps.append("funnel_collect_partial_or_failed")

    med_units = statistics.median([b["units"] for b in BASELINE.values()])
    med_events = statistics.median([b["purchase_events"] for b in BASELINE.values()])
    med_stp = statistics.median([b["TOTAL_PRICE_VALUE"] for b in BASELINE.values()])
    med_ad = statistics.median([b["ad_spend"] for b in BASELINE.values()])
    b31 = BASELINE["2026-08-31"]
    baseline_cmp = {
        "vs_median_27_31": {
            "units": store["STORE_UNITS"] - med_units,
            "purchase_events": store["STORE_PURCHASE_EVENTS"] - med_events,
            "TOTAL_PRICE_VALUE": round(store["TOTAL_PRICE_VALUE"] - med_stp, 2),
            "ad_spend": round(ad_total["total_ad_spend_rub"] - med_ad, 2),
        },
        "vs_31_08": {
            "units": store["STORE_UNITS"] - b31["units"],
            "purchase_events": store["STORE_PURCHASE_EVENTS"] - b31["purchase_events"],
            "TOTAL_PRICE_VALUE": round(store["TOTAL_PRICE_VALUE"] - b31["TOTAL_PRICE_VALUE"], 2),
            "ad_spend": round(ad_total["total_ad_spend_rub"] - b31["ad_spend"], 2),
            "bulk_unit_share_note": "compare BULK_UNIT_SHARE separately",
        },
    }

    def top(key: str, n: int = 10) -> list[dict[str, Any]]:
        return sorted(sku_stats, key=lambda x: -float(x.get(key) or 0))[:n]

    focus = {}
    for nmid in FOCUS_SKUS:
        focus[str(nmid)] = next((s for s in sku_stats if s["nmID"] == nmid), {"nmID": nmid, "units": 0})

    gate = "CONTINUES"
    if (limits["LIMITS_MATCH"] == "YES" and day_state == "CLOSED"
            and not caps["OVERSHOOT"] and ad_total["total_ad_spend_rub"] < NOMINAL_CAP_SUM * 0.5):
        gate = "MAY_BE_LIFTED"

    return {
        "OBSERVATION_PACKET": "ELIGIBLE",
        "CHECKED_AT_MSK": checked.strftime("%Y-%m-%d %H:%M:%S %Z"),
        "OBSERVATION_PERIOD": TARGET_STR,
        "DAY_STATE": day_state,
        "last_fully_closed_day": TARGET_STR,
        "01_09_fully_closed_confirmation": "YES — observation date is prior calendar day to CHECKED_AT_MSK",
        "data_freshness_notes": "supplier-orders by order date; fullstats daily; funnel nm-batch; attribution lag possible",
        "LIMITS_MATCH": limits["LIMITS_MATCH"],
        "NOMINAL_CAP": NOMINAL_CAP_SUM,
        "LIMITS_DETAIL": limits["rows"],
        "AD_STORE_TOTAL": ad_total,
        "PHYSICAL_CAMPAIGN_SPEND": physical,
        "CAP_BEHAVIOUR": caps,
        "H1_STATE": "EXECUTED + OBSERVING",
        "H1_DETAIL": h1_rows,
        "STORE_DEMAND": store,
        "KPI_DENOMINATOR": "TOTAL_PRICE_VALUE",
        "FUNNEL": funnel_state,
        "BASELINE_COMPARISON": baseline_cmp,
        "NEW_SKU": "GAP",
        "34210859": "DEFERRED",
        "AGGRESSIVENESS_TEST": "NOT_EXECUTED",
        "TOP_SKU_BY_UNITS": top("units"),
        "TOP_SKU_BY_PURCHASE_EVENTS": top("purchase_events"),
        "TOP_SKU_BY_TOTAL_PRICE": top("TOTAL_PRICE_VALUE"),
        "FOCUS_SKUS": focus,
        "OBSERVATION_GATE": gate,
        "ITERATION_04_CAUSAL_RESULT": "OPEN",
        "OPEN_GAPS": gaps,
        # RETURN SUMMARY fields
        "TOTAL_AD_SPEND": ad_total["total_ad_spend_rub"],
        "AD_SPEND_SHARE_TOTAL_PRICE": ad_total["AD_SPEND_SHARE_TOTAL_PRICE_pct"],
        "MAIN_SKU_DRIVERS": top("units")[:3],
        "ATTRIBUTED_ORDERS": ad_total["attributed_orders"],
        **{k: store[k] for k in (
            "STORE_UNITS", "STORE_PURCHASE_EVENTS", "UNITS_PER_EVENT",
            "TOTAL_PRICE_VALUE", "BULK_EVENT_COUNT", "BULK_UNIT_SHARE", "MAX_EVENT_SIZE",
        )},
        "PURCHASE_EVENT_CONCENTRATION": store["PURCHASE_EVENT_CONCENTRATION"],
        "FUNNEL_STATE": funnel_state.get("state"),
    }


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--output-dir", default=".tmp/a1_iteration_05_observation")
    args = ap.parse_args(argv)
    root = Path(args.output_dir).resolve()
    root.mkdir(parents=True, exist_ok=True)
    _bootstrap()
    pg = _load_pg(root)

    async def _run() -> dict[str, Any]:
        orders, campaigns, fullstats, funnel = await fetch_all(root)
        checked = datetime.now(MSK)
        payload = build(checked, pg, orders, campaigns, fullstats, funnel)
        pkg = root / PACKAGE
        pkg.mkdir(parents=True, exist_ok=True)
        (pkg / f"{PACKAGE}.json").write_text(
            json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8"
        )
        if payload.get("OBSERVATION_PACKET") == "ELIGIBLE":
            phys = payload.get("PHYSICAL_CAMPAIGN_SPEND", [])
            if phys:
                _write_csv(pkg / "PHYSICAL_CAMPAIGN_SPEND.csv", phys, list(phys[0].keys()))
            lim = payload.get("LIMITS_DETAIL", [])
            if lim:
                _write_csv(pkg / "LIMITS_CHECK.csv", lim, list(lim[0].keys()))
        payload["CSV_DIR"] = str(pkg.resolve())
        return payload

    out = asyncio.run(_run())
    print(json.dumps(out, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
