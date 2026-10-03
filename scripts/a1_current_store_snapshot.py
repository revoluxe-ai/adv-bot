"""READ_ONLY: A1 current store snapshot after Iteration-04.

Снимает intraday factual state магазина: orders/funnel/ads, physical campaigns,
cap behaviour, H1, iteration-04 limits. Без production mutations и causal verdicts.
"""

from __future__ import annotations

import argparse
import asyncio
import csv
import hashlib
import json
import os
import re
import sys
import zipfile
from collections import defaultdict
from datetime import date, datetime, time
from pathlib import Path
from typing import Any
from zoneinfo import ZoneInfo

import dotenv

dotenv.load_dotenv()

from scripts import ch_a1_evidence as evidence
from scripts.wb_a1_associated_conversions import _read_float, _read_int
from scripts.wb_api_readonly_ops.collect_layout import (
    COLLECT_V2_CAMPAIGNS_JSONL,
    COLLECT_V2_FULLSTATS_JSONL,
    COLLECT_V2_FUNNEL_JSONL,
    COLLECT_V2_ORDERS_JSONL,
    read_jsonl_from_zip,
)

SHOP_ID = "5339e9ad-cbfe-50fc-8d77-b9f337a80417"
MSK = ZoneInfo("Europe/Moscow")
PACKAGE_NAME = "A1-CURRENT-STORE-SNAPSHOT"
TODAY = date(2026, 9, 1)
TODAY_STR = TODAY.isoformat()
COMPARE_DAYS = ("2026-08-30", "2026-08-31", TODAY_STR)
ACTIVE_WB = {9, 11}
H1_AUTO = [17906286, 21604339]
H1_SEARCH = [20646357, 21604374]
TARGET_SKU = 837395782
DEFERRED_ADV = 34210859
NAME_SEARCH_PATTERN = re.compile(r"<!-\[(\d+)\]-!>")

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

PG_FIELDS = [
    "id",
    "adv_id",
    "_search_adv_id",
    "name",
    "nmids",
    "active_status",
    "bot_active",
    "auto_budget_watchdog_enabled",
    "auto_budget_daily_limit",
    "search_auto_budget_daily_limit",
    "use_common_budget",
    "common_budget_daily_limit",
]


def _pg_database() -> str:
    return os.environ.get("POSTGRES_DBNAME") or "adv_updater"


def _sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def _write_csv(path: Path, rows: list[dict[str, Any]], cols: list[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=cols, extrasaction="ignore")
        w.writeheader()
        for row in rows:
            w.writerow({c: row.get(c, "") for c in cols})


def _int_limit(val: Any) -> int:
    try:
        return int(float(val or 0))
    except (TypeError, ValueError):
        return 0


def _parse_nmids(raw: str) -> list[int]:
    if not raw:
        return []
    try:
        val = json.loads(raw.replace("'", '"'))
        if isinstance(val, list):
            return [int(x) for x in val if str(x).isdigit()]
    except json.JSONDecodeError:
        pass
    return []


def _search_from_name(name: str) -> int | None:
    if not name:
        return None
    m = NAME_SEARCH_PATTERN.search(name.replace(" ", ""))
    return int(m.group(1)) if m else None


def _resolved_search(row: dict[str, str]) -> int | None:
    raw = (row.get("_search_adv_id") or "").strip()
    if raw.isdigit() and int(raw) > 0:
        return int(raw)
    return _search_from_name(row.get("name") or "")


def _bootstrap_cluster_infra() -> None:
    user = os.environ.get("POSTGRES_USER")
    password = os.environ.get("POSTGRES_PASSWORD")
    if user and password:
        evidence._PG_CREDENTIALS = user, password
    pg_host = os.environ.get("POSTGRES_MASTER_HOST") or os.environ.get("POSTGRES_REPLICA_HOST")
    pg_port = os.environ.get("POSTGRES_PORT")
    if pg_host:
        evidence.PG_EXTERNAL_HOST = pg_host
    if pg_port:
        evidence.PG_EXTERNAL_PORT = int(pg_port)


def _load_pg(root: Path, sql_dir: Path) -> list[dict[str, str]]:
    staging = root / "staging"
    staging.mkdir(parents=True, exist_ok=True)
    out = staging / "pg_advsetting.csv"
    cols = ", ".join(f"a.{c}" for c in PG_FIELDS)
    q = (
        f"SELECT {cols} FROM public.advsetting a "
        f"JOIN public.wbcabinet c ON a.wb_cabinet_id = c.id "
        f"WHERE c.shop_id = '{SHOP_ID}'"
    )
    st = evidence.run_pg_query(_pg_database(), q, out, sql_dir / "pg.sql", csv_output=True)
    if not st["success"]:
        raise RuntimeError(st["stderr"])
    with out.open(encoding="utf-8", newline="") as f:
        return list(csv.DictReader(f))


def _redis_reason(adv_id: int, leg: str) -> dict[str, Any]:
    key = f"campaign-activity-reason:{adv_id}:{leg}"
    raw = ""
    try:
        import redis

        host = os.environ.get("REDIS_HOST") or os.environ.get("REDIS_MASTER_HOST")
        if host:
            client = redis.Redis(
                host=host,
                port=int(os.environ.get("REDIS_PORT", "6379")),
                password=os.environ.get("REDIS_PASSWORD"),
                db=int(os.environ.get("REDIS_DB", "0")),
                decode_responses=True,
            )
            raw = client.get(key) or ""
    except Exception:
        pass
    parsed = None
    if raw:
        try:
            parsed = json.loads(raw)
        except json.JSONDecodeError:
            parsed = {"raw": raw}
    return {"key": key, "parsed": parsed}


async def _run_collect(output_dir: Path) -> dict[str, Any]:
    from app.configs.app_config import AppConfig
    from app.core.di.wb_manager_hub.wb_manager_hub_factory import WBManagerHubFactory
    from app.core.mp.wb.api.httpx_client_handler import HttpxClientHandler
    from app.core.redis_manager_v2.redis_client import RedisClient
    from app.modules.common_slaves.wildberries.super_cabinet_manager import (
        get_access_for_wb_cabinet,
    )
    from redis.asyncio import Redis
    from scripts.wb_api_readonly_ops.cli import DEFAULT_COLLECT_MAX_SECONDS
    from scripts.wb_api_readonly_ops.collect.runner import run_full_collect

    app_config = AppConfig.create()
    redis_config = app_config.infrastructure.redis
    redis_raw: Redis[str] = Redis(
        host=redis_config.host,
        port=redis_config.port,
        db=redis_config.db,
        password=redis_config.password,
        decode_responses=True,
    )
    await redis_raw.ping()
    redis_wrap = RedisClient(redis_client=redis_raw)
    httpx = HttpxClientHandler()
    await httpx.init()
    try:
        await get_access_for_wb_cabinet(SHOP_ID)
        hub = WBManagerHubFactory(
            httpx_client_handler=httpx, redis_client_wrapper=redis_wrap
        ).get_wb_manager_hub(SHOP_ID)
        ads_from = date(2026, 8, 30).isoformat()
        ads_to = TODAY.isoformat()
        report = await run_full_collect(
            shop_id=SHOP_ID,
            wb_data_manager=hub.wb_data_manager,
            output_dir=output_dir,
            orders_date_from=ads_from,
            max_seconds=DEFAULT_COLLECT_MAX_SECONDS,
            max_api_calls=10_000,
            ads_date_from=ads_from,
            ads_date_to=ads_to,
        )
        return report.to_dict()
    finally:
        await httpx.shutdown()
        await redis_raw.close()


def _find_zip(collect_dir: Path) -> Path:
    for name in ("wb_readonly_research.zip", "collect.zip"):
        p = collect_dir / name
        if p.exists():
            return p
    zips = sorted(collect_dir.glob("*.zip"), key=lambda x: x.stat().st_mtime, reverse=True)
    if zips:
        return zips[0]
    raise FileNotFoundError(collect_dir)


def _order_ts(row: dict[str, Any]) -> datetime | None:
    raw = row.get("lastChangeDate") or row.get("date") or ""
    try:
        return datetime.fromisoformat(str(raw).replace("Z", "+00:00")).astimezone(MSK)
    except ValueError:
        return None


def _aggregate_fullstats(rows: list[dict[str, Any]]) -> dict[tuple[int, str], dict[str, Any]]:
    agg: dict[tuple[int, str], dict[str, Any]] = {}
    for row in rows:
        adv_id = _read_int(row, "advertId", "advert_id")
        day = str(row.get("date", ""))[:10]
        if not adv_id or not day:
            continue
        b = agg.setdefault(
            (adv_id, day),
            {"adv_id": adv_id, "date": day, "views": 0, "clicks": 0, "spend": 0.0, "orders": 0, "gmv": 0.0},
        )
        b["views"] += _read_int(row, "views")
        b["clicks"] += _read_int(row, "clicks")
        b["spend"] += _read_float(row, "sum", "spend")
        b["orders"] += _read_int(row, "orders")
        b["gmv"] += _read_float(row, "sum_price")
    return agg


def _campaign_inventory(
    campaigns: list[dict[str, Any]], pg_by_adv: dict[int, dict[str, str]]
) -> dict[int, dict[str, Any]]:
    inv: dict[int, dict[str, Any]] = {}
    for row in campaigns:
        adv_id = _read_int(row, "advertId", "id", "advert_id")
        if not adv_id:
            continue
        status = _read_int(row, "status", "wb_status")
        inv[adv_id] = {
            "adv_id": adv_id,
            "wb_status": status,
            "name": row.get("name") or pg_by_adv.get(adv_id, {}).get("name", ""),
        }
    for adv_id, pg in pg_by_adv.items():
        if adv_id not in inv:
            inv[adv_id] = {"adv_id": adv_id, "wb_status": "", "name": pg.get("name", "")}
    return inv


def _build_physical_rows(
    pg_rows: list[dict[str, str]],
    pg_by_adv: dict[int, dict[str, str]],
    stats: dict[tuple[int, str], dict[str, Any]],
    inventory: dict[int, dict[str, Any]],
) -> list[dict[str, Any]]:
    search_to_parent: dict[int, dict[str, str]] = {}
    search_to_parent_adv: dict[int, int] = {}
    for auto_id, row in pg_by_adv.items():
        sid = _resolved_search(row)
        if sid:
            search_to_parent[sid] = row
            search_to_parent_adv[sid] = auto_id

    physical: dict[int, dict[str, Any]] = {}
    for auto_id, row in pg_by_adv.items():
        if str(row.get("bot_active")).lower() not in ("true", "t", "1"):
            continue
        nmids = _parse_nmids(row.get("nmids") or "")
        nmid = nmids[0] if nmids else ""
        physical[auto_id] = {
            "physical_adv_id": auto_id,
            "leg_type": "Auto",
            "parent_adv_setting_id": row.get("id"),
            "parent_auto_adv_id": "",
            "nmID": nmid,
            "daily_limit": _int_limit(row.get("auto_budget_daily_limit")),
            "limit_field": "auto_budget_daily_limit",
            "bot_active": row.get("bot_active"),
            "active_status": row.get("active_status"),
        }
        sid = _resolved_search(row)
        if sid and sid not in physical:
            parent = search_to_parent.get(sid, row)
            physical[sid] = {
                "physical_adv_id": sid,
                "leg_type": "Search",
                "parent_adv_setting_id": parent.get("id"),
                "parent_auto_adv_id": search_to_parent_adv.get(sid, ""),
                "nmID": nmid,
                "daily_limit": _int_limit(parent.get("search_auto_budget_daily_limit")),
                "limit_field": "search_auto_budget_daily_limit",
                "bot_active": parent.get("bot_active"),
                "active_status": pg_by_adv.get(sid, {}).get("active_status", ""),
            }

    for adv_id, row in pg_by_adv.items():
        if adv_id in physical:
            continue
        if str(row.get("bot_active")).lower() not in ("true", "t", "1"):
            continue
        nmids = _parse_nmids(row.get("nmids") or "")
        physical[adv_id] = {
            "physical_adv_id": adv_id,
            "leg_type": "Search_orphan",
            "parent_adv_setting_id": row.get("id"),
            "parent_auto_adv_id": "",
            "nmID": nmids[0] if nmids else "",
            "daily_limit": _int_limit(row.get("search_auto_budget_daily_limit")),
            "limit_field": "search_auto_budget_daily_limit",
            "bot_active": row.get("bot_active"),
            "active_status": row.get("active_status"),
        }

    out: list[dict[str, Any]] = []
    for adv_id, meta in physical.items():
        inv = inventory.get(adv_id, {})
        wb = inv.get("wb_status", "")
        st = stats.get((adv_id, TODAY_STR), {})
        spend = round(float(st.get("spend") or 0), 2)
        views = int(st.get("views") or 0)
        clicks = int(st.get("clicks") or 0)
        lim = int(meta["daily_limit"] or 0)
        pct = round(100.0 * spend / lim, 2) if lim > 0 else (0.0 if spend == 0 else "OVERSHOOT_NO_CAP")
        ctr = round(100.0 * clicks / views, 4) if views else 0.0
        cpc = round(spend / clicks, 4) if clicks else ""
        leg = "auto" if meta["leg_type"] == "Auto" else "search"
        rr = _redis_reason(adv_id, leg)
        parsed = rr.get("parsed") or {}
        out.append(
            {
                "parent_adv_setting_id": meta["parent_adv_setting_id"],
                "physical_adv_id": adv_id,
                "leg_type": meta["leg_type"],
                "nmID": meta["nmID"],
                "wb_status": wb,
                "bot_active": meta["bot_active"],
                "runtime_active_status": meta["active_status"],
                "daily_limit_rub": lim,
                "spend_today_rub": spend,
                "cap_pct_consumed": pct,
                "views_today": views,
                "clicks_today": clicks,
                "ctr_pct": ctr,
                "cpc_rub": cpc,
                "attributed_orders_today": int(st.get("orders") or 0),
                "attributed_gmv_today_rub": round(float(st.get("gmv") or 0), 2),
                "pause_reason_code": parsed.get("reason_code", "GAP"),
                "runtime_command": parsed.get("command", "GAP"),
                "runtime_reason_updated_at": parsed.get("updated_at", "GAP"),
            }
        )
    out.sort(key=lambda r: (-float(r["spend_today_rub"] or 0),))
    return out


async def run_snapshot(root: Path, pg_rows: list[dict[str, str]]) -> dict[str, Any]:
    checked = datetime.now(MSK)
    cutoff = checked.time()
    sql_dir = root / "sql"
    pkg = root / PACKAGE_NAME
    pkg.mkdir(parents=True, exist_ok=True)
    collect_dir = root / "collect"
    collect_dir.mkdir(parents=True, exist_ok=True)

    pg_by_adv: dict[int, dict[str, str]] = {}
    for row in pg_rows:
        try:
            aid = int(row.get("adv_id") or 0)
        except (TypeError, ValueError):
            continue
        if aid:
            pg_by_adv[aid] = row

    collect_report = await _run_collect(collect_dir)
    zip_path = _find_zip(collect_dir)

    with zipfile.ZipFile(zip_path) as zf:
        orders, _ = read_jsonl_from_zip(zf, COLLECT_V2_ORDERS_JSONL)
        funnel, _ = read_jsonl_from_zip(zf, COLLECT_V2_FUNNEL_JSONL)
        campaigns, _ = read_jsonl_from_zip(zf, COLLECT_V2_CAMPAIGNS_JSONL)
        fullstats, _ = read_jsonl_from_zip(zf, COLLECT_V2_FULLSTATS_JSONL)

    stats = _aggregate_fullstats(fullstats)
    inventory = _campaign_inventory(campaigns, pg_by_adv)

    # Store / SKU today
    store_today = {"factual_orders": 0, "factual_order_value_rub": 0.0}
    sku_today: dict[int, dict[str, Any]] = defaultdict(
        lambda: {"factual_orders": 0, "factual_order_value_rub": 0.0, "carts": 0.0}
    )
    same_time_cmp: dict[str, dict[str, Any]] = {}
    for cmp_day in COMPARE_DAYS:
        same_time_cmp[cmp_day] = {"factual_orders": 0, "factual_order_value_rub": 0.0, "note": ""}

    for row in orders:
        day = str(row.get("date") or "")[:10]
        ts = _order_ts(row)
        val = _read_float(row, "totalPrice", "finishedPrice", "priceWithDisc")
        nmid = _read_int(row, "nmId", "nm_id", "nmid")
        if day == TODAY_STR:
            store_today["factual_orders"] += 1
            store_today["factual_order_value_rub"] += val
            if nmid:
                sku_today[nmid]["factual_orders"] += 1
                sku_today[nmid]["factual_order_value_rub"] += val
        if ts and day in same_time_cmp and ts.time() <= cutoff:
            same_time_cmp[day]["factual_orders"] += 1
            same_time_cmp[day]["factual_order_value_rub"] += val

    store_today["factual_order_value_rub"] = round(store_today["factual_order_value_rub"], 2)
    for d, b in same_time_cmp.items():
        b["factual_order_value_rub"] = round(b["factual_order_value_rub"], 2)
        if d == TODAY_STR:
            b["note"] = "OPEN_PARTIAL current slice"
        else:
            b["note"] = f"same-time slice through {cutoff.strftime('%H:%M')} MSK"

    funnel_today = {"carts": 0.0, "funnel_orders": 0.0, "funnel_order_value_rub": 0.0}
    sku_with_carts = 0
    for row in funnel:
        day = str(row.get("day") or row.get("date") or "")[:10]
        nmid = _read_int(row, "nmid", "nmId")
        carts = _read_float(row, "add_to_cart", "addToCart", "cartCount")
        if day == TODAY_STR:
            funnel_today["carts"] += carts
            funnel_today["funnel_orders"] += _read_float(row, "orders", "orderCount")
            funnel_today["funnel_order_value_rub"] += _read_float(
                row, "orders_sum", "orderSum"
            )
            if nmid:
                sku_today[nmid]["carts"] += carts
    for nmid, b in sku_today.items():
        if b["carts"] > 0:
            sku_with_carts += 1
        b["factual_order_value_rub"] = round(b["factual_order_value_rub"], 2)

    total_spend_today = round(
        sum(float(stats.get((aid, TODAY_STR), {}).get("spend") or 0) for aid in inventory), 2
    )
    spend_order_ratio = (
        round(total_spend_today / store_today["factual_order_value_rub"], 4)
        if store_today["factual_order_value_rub"] > 0
        else "GAP"
    )

    sku_rows: list[dict[str, Any]] = []
    total_ord = store_today["factual_orders"] or 1
    total_val = store_today["factual_order_value_rub"] or 1.0
    for nmid, b in sorted(sku_today.items(), key=lambda x: -x[1]["factual_orders"]):
        if b["factual_orders"] <= 0 and b["carts"] <= 0:
            continue
        sku_rows.append(
            {
                "nmID": nmid,
                "factual_orders": b["factual_orders"],
                "factual_order_value_rub": b["factual_order_value_rub"],
                "carts": b["carts"],
                "share_orders_pct": round(100.0 * b["factual_orders"] / total_ord, 2),
                "share_value_pct": round(100.0 * b["factual_order_value_rub"] / total_val, 2),
            }
        )
    top10_orders = sorted(sku_rows, key=lambda r: -r["factual_orders"])[:10]
    top10_value = sorted(sku_rows, key=lambda r: -r["factual_order_value_rub"])[:10]
    target_sku = next((r for r in sku_rows if r["nmID"] == TARGET_SKU), {"nmID": TARGET_SKU, "GAP": True})

    physical_rows = _build_physical_rows(pg_rows, pg_by_adv, stats, inventory)
    caps_hit = [r for r in physical_rows if isinstance(r["cap_pct_consumed"], (int, float)) and r["cap_pct_consumed"] >= 100]
    caps_near = [r for r in physical_rows if isinstance(r["cap_pct_consumed"], (int, float)) and 80 <= r["cap_pct_consumed"] < 100]
    underspend = [
        r
        for r in physical_rows
        if isinstance(r["cap_pct_consumed"], (int, float))
        and r["daily_limit_rub"] > 0
        and r["cap_pct_consumed"] < 20
        and r["spend_today_rub"] > 0
    ]
    overshoot = [r for r in physical_rows if r["cap_pct_consumed"] == "OVERSHOOT_NO_CAP" or (isinstance(r["cap_pct_consumed"], (int, float)) and r["cap_pct_consumed"] > 100)]

    iter04_rows: list[dict[str, Any]] = []
    cap_sum = 0
    for adv_id, (exp_a, exp_s) in ITER04_EXPECTED.items():
        row = pg_by_adv.get(adv_id, {})
        cur_a = _int_limit(row.get("auto_budget_daily_limit"))
        cur_s = _int_limit(row.get("search_auto_budget_daily_limit"))
        cap_sum += cur_a + cur_s
        iter04_rows.append(
            {
                "adv_id": adv_id,
                "adv_setting_id": row.get("id", "GAP"),
                "expected_auto": exp_a,
                "expected_search": exp_s,
                "current_auto": cur_a,
                "current_search": cur_s,
                "match": cur_a == exp_a and cur_s == exp_s,
            }
        )

    h1_rows: list[dict[str, Any]] = []
    for adv_id in H1_AUTO + H1_SEARCH:
        row = pg_by_adv.get(adv_id, {})
        parent = pg_by_adv.get(17906286 if adv_id == 20646357 else 21604339 if adv_id == 21604374 else adv_id, row)
        leg = "auto" if adv_id in H1_AUTO else "search"
        st = stats.get((adv_id, TODAY_STR), {})
        rr = _redis_reason(adv_id, leg)
        parsed = rr.get("parsed") or {}
        search_lim = _int_limit(parent.get("search_auto_budget_daily_limit")) if adv_id in H1_SEARCH else ""
        h1_rows.append(
            {
                "adv_id": adv_id,
                "leg": "Auto" if adv_id in H1_AUTO else "Search",
                "wb_status": inventory.get(adv_id, {}).get("wb_status", ""),
                "auto_daily_limit": _int_limit(row.get("auto_budget_daily_limit")) if adv_id in H1_AUTO else "",
                "search_limit_via_parent": search_lim if adv_id in H1_SEARCH else "",
                "spend_today": round(float(st.get("spend") or 0), 2),
                "views_today": int(st.get("views") or 0),
                "clicks_today": int(st.get("clicks") or 0),
                "runtime_reason": parsed.get("reason_code", "GAP"),
                "runtime_command": parsed.get("command", "GAP"),
                "h1_status": "EXECUTED + OBSERVING",
            }
        )

    deferred_st = stats.get((DEFERRED_ADV, TODAY_STR), {})
    deferred_inv = inventory.get(DEFERRED_ADV, {})
    deferred_block = {
        "campaign_adv_id": DEFERRED_ADV,
        "sku_nmID": TARGET_SKU,
        "continuity_status": "DEFERRED",
        "wb_status": deferred_inv.get("wb_status", "GAP"),
        "spend_today": round(float(deferred_st.get("spend") or 0), 2),
        "views_today": int(deferred_st.get("views") or 0),
        "clicks_today": int(deferred_st.get("clicks") or 0),
        "attributed_orders_today": int(deferred_st.get("orders") or 0),
        "factual_sku_orders_today": target_sku.get("factual_orders", 0) if isinstance(target_sku, dict) else 0,
        "factual_sku_value_today": target_sku.get("factual_order_value_rub", 0) if isinstance(target_sku, dict) else 0,
        "carts_today": target_sku.get("carts", 0) if isinstance(target_sku, dict) else 0,
    }

    main_sales = [f"{r['nmID']}:{r['factual_orders']}ord" for r in top10_orders[:3]]
    main_ad = [f"{r['physical_adv_id']}:{r['spend_today_rub']}rub" for r in physical_rows[:3]]

    payload: dict[str, Any] = {
        "package": PACKAGE_NAME,
        "PACKAGE_STATUS": "AUTHORITATIVE",
        "CHECKED_AT_MSK": checked.strftime("%Y-%m-%d %H:%M:%S %Z"),
        "coverage": {
            "today": TODAY_STR,
            "day_state": "OPEN_PARTIAL",
            "orders_source": "WB /api/v1/supplier/orders (calendar date field)",
            "funnel_source": "sales-funnel/products/history (daily aggregate, open-day)",
            "ads_source": "adv/v3/fullstats (attribution may lag)",
            "pg_source": "CURRENT advsetting read-only",
            "collect_report": collect_report,
        },
        "store_today": {
            **store_today,
            "carts": funnel_today["carts"],
            "funnel_orders": funnel_today["funnel_orders"],
            "funnel_order_value_rub": round(funnel_today["funnel_order_value_rub"], 2),
            "total_ad_spend_rub": total_spend_today,
            "ad_spend_to_order_value_ratio": spend_order_ratio,
            "sku_with_orders": len([r for r in sku_rows if r["factual_orders"] > 0]),
            "sku_with_carts": sku_with_carts,
            "same_time_comparison": same_time_cmp,
        },
        "sku_top10_orders": top10_orders,
        "sku_top10_value": top10_value,
        "sku_837395782": target_sku,
        "physical_campaigns": physical_rows,
        "cap_behaviour": {
            "caps_hit": caps_hit,
            "caps_near_80pct": caps_near,
            "major_underspend": underspend[:10],
            "overshoot": overshoot,
        },
        "h1_current_state": h1_rows,
        "iteration04_limits": {
            "rows": iter04_rows,
            "effective_cap_sum_rub": cap_sum,
            "expected_sum_rub": 4900,
            "all_match": all(r["match"] for r in iter04_rows),
        },
        "deferred_34210859": deferred_block,
        "NEW_SKU": "GAP",
        "diagnosis": {
            "STORE_TODAY": store_today,
            "AD_SPEND_TODAY": total_spend_today,
            "FACTUAL_ORDERS_TODAY": store_today["factual_orders"],
            "FACTUAL_ORDER_VALUE_TODAY": store_today["factual_order_value_rub"],
            "MAIN_SALES_DRIVERS": main_sales,
            "MAIN_AD_SPEND_DRIVERS": main_ad,
            "CAPS_HIT": [r["physical_adv_id"] for r in caps_hit],
            "CAPS_NEAR_HIT": [r["physical_adv_id"] for r in caps_near],
            "MAJOR_UNDERSPEND": [r["physical_adv_id"] for r in underspend[:5]],
            "H1_CURRENT_STATE": "EXECUTED + OBSERVING",
            "837395782_CURRENT_STATE": target_sku,
            "ANOMALIES": [],
            "OPEN_GAPS": [
                "funnel_daily_not_same_time_comparable",
                "fullstats_attribution_lag_possible",
                "NEW_SKU_identification",
            ],
            "CURRENT_INTRADAY_INTERPRETATION": (
                "Descriptive only: open-day partial slice; not equivalent to closed post-change day."
            ),
        },
    }

    _write_csv(pkg / "STORE_TODAY.csv", [payload["store_today"]], list(payload["store_today"].keys()))
    _write_csv(pkg / "SKU_CONTRIBUTION_TODAY.csv", sku_rows, list(sku_rows[0].keys()) if sku_rows else ["nmID"])
    _write_csv(
        pkg / "PHYSICAL_CAMPAIGNS_TODAY.csv",
        physical_rows,
        list(physical_rows[0].keys()) if physical_rows else ["physical_adv_id"],
    )
    _write_csv(pkg / "ITERATION04_LIMITS.csv", iter04_rows, list(iter04_rows[0].keys()))
    _write_csv(pkg / "H1_CURRENT_STATE.csv", h1_rows, list(h1_rows[0].keys()))

    json_path = pkg / f"{PACKAGE_NAME}.json"
    json_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    zip_out = root / f"{PACKAGE_NAME}.zip"
    with zipfile.ZipFile(zip_out, "w", zipfile.ZIP_DEFLATED) as zf:
        for name in json_path.name, "STORE_TODAY.csv", "SKU_CONTRIBUTION_TODAY.csv", "PHYSICAL_CAMPAIGNS_TODAY.csv", "ITERATION04_LIMITS.csv", "H1_CURRENT_STATE.csv":
            zf.write(pkg / name, arcname=name)
    payload["FINAL_ARCHIVE_SHA256"] = _sha256_file(zip_out)
    payload["ABSOLUTE_ARCHIVE_PATH"] = str(zip_out.resolve())
    json_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    return payload


def main() -> int:
    parser = argparse.ArgumentParser(description="A1 current store snapshot READ_ONLY")
    parser.add_argument("--output-dir", default=".tmp/a1_current_store_snapshot")
    args = parser.parse_args()
    root = Path(args.output_dir)
    root.mkdir(parents=True, exist_ok=True)
    _bootstrap_cluster_infra()
    sql_dir = root / "sql"
    pg_rows = _load_pg(root, sql_dir)
    payload = asyncio.run(run_snapshot(root, pg_rows))
    print(json.dumps({k: payload[k] for k in payload if k not in ("physical_campaigns", "sku_top10_orders", "sku_top10_value", "collect_report")}, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
