"""READ_ONLY: SKU 195764899 growth forensic package (A1).

Механический сбор factual/funnel/ad mapping/performance для target SKU
2026-08-27 → 2026-09-01 (01.09 = OPEN_PARTIAL). Без causal verdicts и mutations.
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
from datetime import date, datetime
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
PACKAGE_NAME = "A1-SKU-195764899-GROWTH-FORENSIC"
TARGET_SKU = 195764899
COMPARE_SKU = 837395782
CLOSED_DAYS = (
    "2026-08-27",
    "2026-08-28",
    "2026-08-29",
    "2026-08-30",
    "2026-08-31",
)
OPEN_DAY = "2026-09-01"
ALL_DAYS = CLOSED_DAYS + (OPEN_DAY,)
ACTIVE_WB = {9, 11}
ORDERS_DAY_FIELD = "date"
NAME_SEARCH_PATTERN = re.compile(r"<!-\[(\d+)\]-!>")

PG_FIELDS = [
    "id",
    "adv_id",
    "_search_adv_id",
    "type",
    "name",
    "nmids",
    "active_status",
    "bot_active",
    "auto_budget_watchdog_enabled",
    "auto_budget_daily_limit",
    "search_auto_budget_daily_limit",
    "use_common_budget",
    "common_budget_daily_limit",
    "aggressiveness",
    "strategy",
    "automatic_version",
    "auto_adv_target_status",
    "auction_adv_target_status",
]

# Prior forensic A1-SKU-837395782-GROWTH-FORENSIC (reference only, not re-collected).
REF_837395782 = {
    "factual_orders_29": 11,
    "factual_value_29": 25839.0,
    "ad_spend_29": 0.0,
    "ad_clicks_29": 0,
    "funnel_carts_28": 9,
    "funnel_carts_29": 8,
    "funnel_carts_30": 9,
    "active_adv_note": "orphan Search 34210859 minimal spend",
}


def _pg_database() -> str:
    return os.environ.get("POSTGRES_DBNAME") or "adv_updater"


def _bootstrap_cluster_infra() -> None:
    user = os.environ.get("POSTGRES_USER")
    password = os.environ.get("POSTGRES_PASSWORD")
    if user and password:
        evidence._PG_CREDENTIALS = user, password
    pg_host = os.environ.get("POSTGRES_MASTER_HOST") or os.environ.get(
        "POSTGRES_REPLICA_HOST"
    )
    pg_port = os.environ.get("POSTGRES_PORT")
    if pg_host:
        evidence.PG_EXTERNAL_HOST = pg_host
    if pg_port:
        evidence.PG_EXTERNAL_PORT = int(pg_port)


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


def _int_limit(val: Any) -> int:
    try:
        return int(float(val or 0))
    except (TypeError, ValueError):
        return 0


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


def _order_day(row: dict[str, Any]) -> str:
    return str(row.get(ORDERS_DAY_FIELD) or row.get("lastChangeDate") or "")[:10]


def _store_orders_daily(rows: list[dict[str, Any]]) -> dict[str, dict[str, Any]]:
    out: dict[str, dict[str, Any]] = {}
    for row in rows:
        day = _order_day(row)
        if day not in ALL_DAYS:
            continue
        b = out.setdefault(day, {"store_orders": 0, "store_value_rub": 0.0})
        b["store_orders"] += 1
        b["store_value_rub"] += _read_float(
            row, "totalPrice", "finishedPrice", "priceWithDisc"
        )
    for b in out.values():
        b["store_value_rub"] = round(b["store_value_rub"], 2)
    return out


def _agg_orders(rows: list[dict[str, Any]], nmid: int) -> dict[str, dict[str, Any]]:
    out: dict[str, dict[str, Any]] = {}
    for row in rows:
        if _read_int(row, "nmId", "nm_id", "nmid") != nmid:
            continue
        day = _order_day(row)
        if day not in ALL_DAYS:
            continue
        b = out.setdefault(
            day,
            {
                "factual_orders": 0,
                "factual_units": 0,
                "factual_order_value_rub": 0.0,
                "price_with_disc": [],
                "total_price": [],
                "finished_price": [],
            },
        )
        qty = _read_int(row, "quantity", "qty") or 1
        b["factual_orders"] += 1
        b["factual_units"] += qty
        b["factual_order_value_rub"] += _read_float(
            row, "totalPrice", "finishedPrice", "priceWithDisc"
        )
        pwd = _read_float(row, "priceWithDisc")
        if pwd > 0:
            b["price_with_disc"].append(pwd)
        tp = _read_float(row, "totalPrice")
        if tp > 0:
            b["total_price"].append(tp)
        fp = _read_float(row, "finishedPrice")
        if fp > 0:
            b["finished_price"].append(fp)
    for day, b in out.items():
        pwds = b.pop("price_with_disc")
        tps = b.pop("total_price")
        fps = b.pop("finished_price")
        b["avg_factual_order_value_rub"] = (
            round(b["factual_order_value_rub"] / b["factual_orders"], 2)
            if b["factual_orders"]
            else 0
        )
        b["avg_priceWithDisc"] = round(sum(pwds) / len(pwds), 2) if pwds else 0
        b["avg_totalPrice"] = round(sum(tps) / len(tps), 2) if tps else "GAP"
        b["avg_finishedPrice"] = round(sum(fps) / len(fps), 2) if fps else "GAP"
        b["factual_order_value_rub"] = round(b["factual_order_value_rub"], 2)
        b["day_state"] = "OPEN_PARTIAL" if day == OPEN_DAY else "CLOSED"
    return out


def _funnel_by_day(rows: list[dict[str, Any]], nmid: int) -> dict[str, dict[str, Any]]:
    out: dict[str, dict[str, Any]] = {}
    for row in rows:
        if _read_int(row, "nmid", "nmId", "nm_id") != nmid:
            continue
        day = str(row.get("day") or row.get("date") or "")[:10]
        if day not in ALL_DAYS:
            continue
        views = _read_float(row, "open_card", "openCard", "openCardCount")
        carts = _read_float(row, "add_to_cart", "addToCart", "cartCount", "addToCartCount")
        funnel_orders = _read_float(row, "orders", "orderCount", "ordersCount")
        funnel_value = _read_float(row, "orders_sum", "orderSum")
        conv_vc = round(100 * carts / views, 4) if views else "GAP"
        conv_co = round(100 * funnel_orders / carts, 4) if carts else "GAP"
        out[day] = {
            "openCardCount": views,
            "addToCartCount": carts,
            "funnel_ordersCount": funnel_orders,
            "funnel_orderValue_rub": funnel_value,
            "conversion_view_to_cart_pct": conv_vc,
            "conversion_cart_to_order_pct": conv_co,
            "day_state": "OPEN_PARTIAL" if day == OPEN_DAY else "CLOSED",
        }
    return out


def _adv_ids_for_nmid(campaigns: list[dict[str, Any]], nmid: int) -> list[int]:
    ids: list[int] = []
    for c in campaigns:
        adv_id = _read_int(c, "id", "advertId")
        nm_settings = c.get("nm_settings") or c.get("nmSettings") or []
        nm_ids: list[int] = []
        if isinstance(nm_settings, list):
            for nm in nm_settings:
                if isinstance(nm, dict):
                    nid = _read_int(nm, "nm_id", "nmId", "nmID")
                    if nid:
                        nm_ids.append(nid)
        if nmid in nm_ids and adv_id:
            ids.append(adv_id)
    return ids


def _pg_rows_for_sku(pg_rows: list[dict[str, str]], nmid: int) -> list[dict[str, str]]:
    out: list[dict[str, str]] = []
    for row in pg_rows:
        if nmid in _parse_nmids(row.get("nmids") or ""):
            out.append(row)
    return out


def _campaign_meta(campaigns: list[dict[str, Any]], adv_id: int) -> dict[str, Any]:
    for c in campaigns:
        if _read_int(c, "id", "advertId") == adv_id:
            settings = c.get("settings") if isinstance(c.get("settings"), dict) else {}
            return {
                "wb_status": c.get("status"),
                "bid_type": c.get("bid_type"),
                "payment_type": settings.get("payment_type"),
                "name": settings.get("name"),
            }
    return {}


def _fullstats_by_adv_day(
    rows: list[dict[str, Any]], adv_ids: list[int]
) -> dict[tuple[int, str], dict[str, Any]]:
    out: dict[tuple[int, str], dict[str, Any]] = {}
    for row in rows:
        adv_id = _read_int(row, "advertId", "advert_id")
        if adv_id not in adv_ids:
            continue
        day = str(row.get("date") or "")[:10]
        if day not in ALL_DAYS:
            continue
        views = _read_int(row, "views")
        clicks = _read_int(row, "clicks")
        spend = _read_float(row, "sum", "spend")
        ctr = round(100 * clicks / views, 4) if views else _read_float(row, "ctr")
        cpc = round(spend / clicks, 4) if clicks else _read_float(row, "cpc")
        out[(adv_id, day)] = {
            "ad_spend_rub": round(spend, 2),
            "views": views,
            "clicks": clicks,
            "ctr": ctr,
            "cpc": cpc,
            "attributed_orders": _read_int(row, "orders"),
            "attributed_gmv_rub": round(_read_float(row, "sum_price"), 2),
        }
    return out


def _physical_campaigns_for_sku(
    pg_sku_rows: list[dict[str, str]],
    wb_adv_ids: list[int],
    campaigns: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    """Собрать physical Auto/Search legs для SKU из PG + WB collect."""
    seen: set[int] = set()
    out: list[dict[str, Any]] = []

    def _append_physical(
        adv_id: int,
        leg: str,
        pg_row: dict[str, str],
        parent_auto: int | None,
    ) -> None:
        if not adv_id or adv_id in seen:
            return
        seen.add(adv_id)
        meta = _campaign_meta(campaigns, adv_id)
        use_common = str(pg_row.get("use_common_budget")).lower() in ("true", "t", "1")
        if leg == "Auto":
            limit_field = (
                "common_budget_daily_limit"
                if use_common and _int_limit(pg_row.get("common_budget_daily_limit")) > 0
                else "auto_budget_daily_limit"
            )
            limit = _int_limit(pg_row.get(limit_field))
        else:
            limit_field = (
                "common_budget_daily_limit"
                if use_common and _int_limit(pg_row.get("common_budget_daily_limit")) > 0
                else "search_auto_budget_daily_limit"
            )
            limit = _int_limit(pg_row.get(limit_field))
        leg_redis = "auto" if leg == "Auto" else "search"
        rr = _redis_reason(adv_id, leg_redis)
        parsed = rr.get("parsed") or {}
        out.append(
            {
                "adv_setting_id": pg_row.get("id"),
                "auto_adv_id": parent_auto or (adv_id if leg == "Auto" else ""),
                "search_adv_id": adv_id if leg == "Search" else _resolved_search(pg_row) or "",
                "physical_adv_id": adv_id,
                "campaign_type": pg_row.get("type") or leg,
                "leg_type": leg,
                "current_wb_status": meta.get("wb_status", "GAP"),
                "current_bot_active": pg_row.get("bot_active"),
                "current_runtime_active_status": pg_row.get("active_status"),
                "daily_limit_rub": limit,
                "daily_limit_field": limit_field,
                "aggressiveness": pg_row.get("aggressiveness"),
                "automatic_version": pg_row.get("automatic_version"),
                "strategy_mode": pg_row.get("strategy"),
                "use_common_budget": use_common,
                "pause_reason_code": parsed.get("reason_code", "GAP"),
                "runtime_command": parsed.get("command", "GAP"),
            }
        )

    for pg_row in pg_sku_rows:
        auto_id = _read_int({"v": pg_row.get("adv_id")}, "v")
        if auto_id:
            _append_physical(auto_id, "Auto", pg_row, None)
        sid = _resolved_search(pg_row)
        if sid:
            _append_physical(sid, "Search", pg_row, auto_id)

    for adv_id in wb_adv_ids:
        if adv_id in seen:
            continue
        pg_match = next(
            (r for r in pg_sku_rows if str(r.get("adv_id")) == str(adv_id)), {}
        )
        _append_physical(adv_id, "WB_only", pg_match or {}, None)

    return out


def _classify_spike(
    factual_0109: int,
    attr_orders_0109: int,
    clicks_0109: int,
    spend_0109: float,
    carts_prior: list[float],
    views_0109: int,
    views_prior: list[float],
) -> str:
    """DO_CURRENT_ADS_MECHANICALLY_EXPLAIN_01_09_SPIKE? — без causal claim."""
    if factual_0109 <= 0:
        return "INCONCLUSIVE"
    ad_negligible = clicks_0109 == 0 and attr_orders_0109 == 0 and spend_0109 < 100
    if factual_0109 >= 3 and ad_negligible:
        return "NOT_SUPPORTED"
    if attr_orders_0109 >= factual_0109 * 0.5 and clicks_0109 > 0:
        return "SUPPORTED"
    prior_carts = [c for c in carts_prior if c != "GAP" and float(c or 0) > 0]
    prior_views = [v for v in views_prior if v != "GAP" and float(v or 0) > 0]
    funnel_led = False
    if prior_carts and factual_0109 > 0:
        funnel_led = max(prior_carts) >= 3
    if funnel_led and ad_negligible:
        return "NOT_SUPPORTED"
    if clicks_0109 > 5 and attr_orders_0109 > 0:
        return "SUPPORTED"
    if views_0109 > 0 and clicks_0109 == 0 and factual_0109 >= 5:
        return "NOT_SUPPORTED"
    return "INCONCLUSIVE"


def _compare_pattern(
    target_factual: dict[str, dict[str, Any]],
    target_ad: dict[str, Any],
    target_funnel: dict[str, dict[str, Any]],
) -> tuple[str, list[str]]:
    """SAME_PATTERN / DIFFERENT_PATTERN / INCONCLUSIVE vs 837395782 reference."""
    reasons: list[str] = []
    spike_day = max(
        CLOSED_DAYS,
        key=lambda d: target_factual.get(d, {}).get("factual_orders", 0),
    )
    spike_orders = target_factual.get(spike_day, {}).get("factual_orders", 0)
    spike_spend = float(target_ad.get("ad_spend_rub") or 0)
    spike_clicks = int(target_ad.get("clicks") or 0)

    ref_orders = REF_837395782["factual_orders_29"]
    ref_spend = REF_837395782["ad_spend_29"]
    ref_clicks = REF_837395782["ad_clicks_29"]

    if spike_orders >= 5 and spike_spend < 100 and spike_clicks == 0:
        reasons.append(
            f"195764899 peak day {spike_day}: {spike_orders} factual orders with "
            f"spend={spike_spend}₽ clicks={spike_clicks}"
        )
        reasons.append(
            f"837395782 ref 29.08: {ref_orders} orders with spend={ref_spend}₽ clicks={ref_clicks}"
        )
        carts = [
            target_funnel.get(d, {}).get("addToCartCount", 0) for d in CLOSED_DAYS
        ]
        if any(c != "GAP" and float(c or 0) >= 3 for c in carts):
            reasons.append(f"195764899 sustained funnel carts {carts} before/during spike")
        return "SAME_PATTERN", reasons

    if spike_spend > 500 or spike_clicks > 20:
        reasons.append(
            f"195764899 has material ad traffic on peak (spend={spike_spend}, clicks={spike_clicks})"
        )
        reasons.append("837395782 ref spike had near-zero ad clicks/spend")
        return "DIFFERENT_PATTERN", reasons

    reasons.append("Insufficient contrast between SKU ad signals and 837395782 reference")
    return "INCONCLUSIVE", reasons


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
    rc = app_config.infrastructure.redis
    redis_raw: Redis[str] = Redis(
        host=rc.host, port=rc.port, db=rc.db, password=rc.password, decode_responses=True
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
        report = await run_full_collect(
            shop_id=SHOP_ID,
            wb_data_manager=hub.wb_data_manager,
            output_dir=output_dir,
            orders_date_from=date(2026, 8, 27).isoformat(),
            max_seconds=DEFAULT_COLLECT_MAX_SECONDS,
            max_api_calls=15_000,
            ads_date_from=date(2026, 8, 27).isoformat(),
            ads_date_to=date(2026, 9, 1).isoformat(),
        )
        return report.to_dict()
    finally:
        await httpx.shutdown()
        await redis_raw.aclose()


def _find_zip(collect_dir: Path) -> Path:
    for name in ("wb_readonly_research.zip",):
        p = collect_dir / name
        if p.exists():
            return p
    zips = sorted(collect_dir.glob("*.zip"), key=lambda p: p.stat().st_mtime, reverse=True)
    if zips:
        return zips[0]
    raise FileNotFoundError(str(collect_dir))


def build_package(
    root: Path,
    zip_path: Path,
    pg_rows: list[dict[str, str]],
    *,
    collect_report: dict[str, Any] | None = None,
) -> dict[str, Any]:
    checked = datetime.now(MSK)
    pkg = root / PACKAGE_NAME
    pkg.mkdir(parents=True, exist_ok=True)
    gaps: list[str] = []

    with zipfile.ZipFile(zip_path) as zf:
        orders, om = read_jsonl_from_zip(zf, COLLECT_V2_ORDERS_JSONL)
        funnel, fm = read_jsonl_from_zip(zf, COLLECT_V2_FUNNEL_JSONL)
        fullstats, _ = read_jsonl_from_zip(zf, COLLECT_V2_FULLSTATS_JSONL)
        campaigns, _ = read_jsonl_from_zip(zf, COLLECT_V2_CAMPAIGNS_JSONL)
        try:
            cards = [
                json.loads(l)
                for l in zf.read("raw/cards/cards.jsonl").decode().splitlines()
                if l.strip()
            ]
        except KeyError:
            cards = []
            gaps.append("cards.jsonl missing")

    store_daily = _store_orders_daily(orders)
    factual_t = _agg_orders(orders, TARGET_SKU)
    funnel_t = _funnel_by_day(funnel, TARGET_SKU)
    pg_sku = _pg_rows_for_sku(pg_rows, TARGET_SKU)
    wb_adv_ids = _adv_ids_for_nmid(campaigns, TARGET_SKU)
    physical = _physical_campaigns_for_sku(pg_sku, wb_adv_ids, campaigns)
    physical_adv_ids = [int(p["physical_adv_id"]) for p in physical if p.get("physical_adv_id")]
    fs_map = _fullstats_by_adv_day(fullstats, physical_adv_ids or wb_adv_ids)

    # Table 1: daily SKU funnel/sales
    daily_sku_rows: list[dict[str, Any]] = []
    for day in ALL_DAYS:
        fd = factual_t.get(day, {})
        fn = funnel_t.get(day, {})
        store = store_daily.get(day, {"store_orders": 0, "store_value_rub": 0})
        fo = fd.get("factual_orders", 0)
        fv = fd.get("factual_order_value_rub", 0)
        so = store["store_orders"]
        sv = store["store_value_rub"]
        daily_sku_rows.append(
            {
                "date": day,
                "day_state": "OPEN_PARTIAL" if day == OPEN_DAY else "CLOSED",
                "nmID": TARGET_SKU,
                "factual_orders": fo,
                "factual_order_value_rub": fv,
                "avg_factual_order_value_rub": fd.get("avg_factual_order_value_rub", 0),
                "sku_share_of_store_orders_pct": round(100 * fo / so, 2) if so else 0,
                "sku_share_of_store_value_pct": round(100 * fv / sv, 2) if sv else 0,
                "store_orders": so,
                "store_value_rub": sv,
                "openCardCount": fn.get("openCardCount", "GAP"),
                "addToCartCount": fn.get("addToCartCount", "GAP"),
                "funnel_ordersCount": fn.get("funnel_ordersCount", "GAP"),
                "funnel_orderValue_rub": fn.get("funnel_orderValue_rub", "GAP"),
                "conversion_view_to_cart_pct": fn.get("conversion_view_to_cart_pct", "GAP"),
                "conversion_cart_to_order_pct": fn.get("conversion_cart_to_order_pct", "GAP"),
            }
        )

    # Table 2: daily physical advertising performance
    ad_perf_rows: list[dict[str, Any]] = []
    sku_ad_daily: dict[str, dict[str, Any]] = {}
    for day in ALL_DAYS:
        sku_bucket = sku_ad_daily.setdefault(
            day,
            {
                "ad_spend_rub": 0.0,
                "views": 0,
                "clicks": 0,
                "attributed_orders": 0,
                "attributed_gmv_rub": 0.0,
            },
        )
        for phys in physical:
            adv_id = int(phys["physical_adv_id"])
            fs = fs_map.get((adv_id, day), {})
            spend = float(fs.get("ad_spend_rub") or 0)
            views = int(fs.get("views") or 0)
            clicks = int(fs.get("clicks") or 0)
            attr_o = int(fs.get("attributed_orders") or 0)
            attr_g = float(fs.get("attributed_gmv_rub") or 0)
            lim = int(phys.get("daily_limit_rub") or 0)
            cap_pct = round(100 * spend / lim, 2) if lim > 0 else (0 if spend == 0 else "OVERSHOOT")
            sku_bucket["ad_spend_rub"] += spend
            sku_bucket["views"] += views
            sku_bucket["clicks"] += clicks
            sku_bucket["attributed_orders"] += attr_o
            sku_bucket["attributed_gmv_rub"] += attr_g
            ad_perf_rows.append(
                {
                    "date": day,
                    "day_state": "OPEN_PARTIAL" if day == OPEN_DAY else "CLOSED",
                    "nmID": TARGET_SKU,
                    "adv_setting_id": phys.get("adv_setting_id"),
                    "physical_adv_id": adv_id,
                    "leg_type": phys.get("leg_type"),
                    "auto_adv_id": phys.get("auto_adv_id"),
                    "search_adv_id": phys.get("search_adv_id"),
                    "campaign_type": phys.get("campaign_type"),
                    "current_wb_status": phys.get("current_wb_status"),
                    "current_bot_active": phys.get("current_bot_active"),
                    "current_runtime_active_status": phys.get("current_runtime_active_status"),
                    "daily_limit_rub": lim,
                    "cap_consumption_pct": cap_pct,
                    "ad_spend_rub": spend,
                    "views": views,
                    "clicks": clicks,
                    "ctr_pct": fs.get("ctr", 0),
                    "cpc_rub": fs.get("cpc", 0),
                    "attributed_orders": attr_o,
                    "attributed_gmv_rub": attr_g,
                    "aggressiveness": phys.get("aggressiveness"),
                    "automatic_version": phys.get("automatic_version"),
                    "strategy_mode": phys.get("strategy_mode"),
                    "pause_reason_code": phys.get("pause_reason_code"),
                    "runtime_command": phys.get("runtime_command"),
                }
            )

    ad_campaign_status = "NONE" if not physical and not wb_adv_ids else "MAPPED"

    # 01.09 spike decomposition
    d0109 = factual_t.get(OPEN_DAY, {})
    ad0109 = sku_ad_daily.get(OPEN_DAY, {})
    fn0109 = funnel_t.get(OPEN_DAY, {})
    carts_prior = [
        funnel_t.get(d, {}).get("addToCartCount", 0)
        for d in CLOSED_DAYS
    ]
    views_prior = [
        funnel_t.get(d, {}).get("openCardCount", 0)
        for d in CLOSED_DAYS
    ]
    spike_class = _classify_spike(
        factual_0109=int(d0109.get("factual_orders") or 0),
        attr_orders_0109=int(ad0109.get("attributed_orders") or 0),
        clicks_0109=int(ad0109.get("clicks") or 0),
        spend_0109=float(ad0109.get("ad_spend_rub") or 0),
        carts_prior=carts_prior,
        views_0109=int(fn0109.get("openCardCount") or 0)
        if fn0109.get("openCardCount") != "GAP"
        else 0,
        views_prior=views_prior,
    )

    peak_day = max(ALL_DAYS, key=lambda d: factual_t.get(d, {}).get("factual_orders", 0))
    peak_ad = sku_ad_daily.get(peak_day, {})
    compare_verdict, compare_reasons = _compare_pattern(
        factual_t, peak_ad, funnel_t
    )

    direct_assoc = {
        "status": "GAP",
        "note": "collect_v2 fullstats flattened without apps/nms[] — DIRECT_ASSOC_SPLIT unavailable",
    }
    gaps.append("direct_assoc_nm_level_not_in_collect_flatten")

    price_stock = {
        "seller_price": "HISTORICAL_GAP",
        "wb_price": "HISTORICAL_GAP",
        "discount_pct": "HISTORICAL_GAP",
        "spp_wallet_discount": "HISTORICAL_GAP",
        "promotion": "HISTORICAL_GAP",
        "stock_available_qty": "HISTORICAL_GAP",
        "observed_priceWithDisc_from_orders": {
            day: factual_t.get(day, {}).get("avg_priceWithDisc", "GAP") for day in ALL_DAYS
        },
    }
    gaps.extend(
        [
            "historical_seller_wb_price",
            "historical_spp_promo",
            "historical_stock",
        ]
    )

    spike_decomp = {
        "date": OPEN_DAY,
        "day_state": "OPEN_PARTIAL",
        "factual_orders_snapshot": d0109.get("factual_orders", 0),
        "attributed_orders_current_ads": ad0109.get("attributed_orders", 0),
        "ad_spend_accumulated_rub": ad0109.get("ad_spend_rub", 0),
        "ad_clicks_today": ad0109.get("clicks", 0),
        "carts_prior_days": dict(zip(CLOSED_DAYS, carts_prior)),
        "openCard_prior_days": dict(zip(CLOSED_DAYS, views_prior)),
        "openCard_today_partial": fn0109.get("openCardCount", "GAP"),
        "DO_CURRENT_ADS_MECHANICALLY_EXPLAIN_01_09_SPIKE": spike_class,
    }

    _write_csv(
        pkg / "DAILY_SKU_FUNNEL_SALES.csv",
        daily_sku_rows,
        list(daily_sku_rows[0].keys()) if daily_sku_rows else ["date"],
    )
    _write_csv(
        pkg / "DAILY_PHYSICAL_AD_PERFORMANCE.csv",
        ad_perf_rows,
        list(ad_perf_rows[0].keys()) if ad_perf_rows else ["date"],
    )
    _write_csv(pkg / "AD_CAMPAIGNS_MAPPING.csv", physical, list(physical[0].keys()) if physical else ["physical_adv_id"])

    provenance = [
        "# SOURCE_PROVENANCE",
        "",
        f"- package: `{PACKAGE_NAME}`",
        f"- target_sku: `{TARGET_SKU}`",
        f"- shop_id: `{SHOP_ID}`",
        f"- period: `2026-08-27` → `2026-09-01` (01.09 OPEN_PARTIAL)",
        f"- checked_at_msk: {checked.strftime('%Y-%m-%d %H:%M:%S %Z')}",
        f"- collect_zip: `{zip_path.resolve()}`",
        f"- orders_member: `{om}`",
        f"- funnel_member: `{fm}`",
        f"- AD_CAMPAIGN: `{ad_campaign_status}`",
        f"- physical_adv_ids: `{physical_adv_ids}`",
        f"- pg_sku_rows: `{len(pg_sku)}`",
        "- causal_verdict: FORBIDDEN",
        "",
        f"- GAPS: {gaps}",
        "",
    ]
    (pkg / "SOURCE_PROVENANCE.md").write_text("\n".join(provenance), encoding="utf-8")

    return_block = {
        "SKU": TARGET_SKU,
        "PERIOD": "2026-08-27 → 2026-09-01 (2026-09-01 OPEN_PARTIAL)",
        "FACTUAL_ORDER_SERIES": {d: factual_t.get(d, {}).get("factual_orders", 0) for d in ALL_DAYS},
        "FACTUAL_VALUE_SERIES": {
            d: factual_t.get(d, {}).get("factual_order_value_rub", 0) for d in ALL_DAYS
        },
        "CART_SERIES": {d: funnel_t.get(d, {}).get("addToCartCount", "GAP") for d in ALL_DAYS},
        "AD_CAMPAIGNS": physical if physical else "NONE",
        "AD_SPEND_SERIES": {d: round(sku_ad_daily.get(d, {}).get("ad_spend_rub", 0), 2) for d in ALL_DAYS},
        "AD_CLICK_SERIES": {d: sku_ad_daily.get(d, {}).get("clicks", 0) for d in ALL_DAYS},
        "ATTRIBUTED_ORDER_SERIES": {
            d: sku_ad_daily.get(d, {}).get("attributed_orders", 0) for d in ALL_DAYS
        },
        "DIRECT_ASSOC_SPLIT": direct_assoc,
        "PRICE_STOCK_PROMO_STATE": price_stock,
        "01_09_SPIKE_CLASSIFICATION": spike_decomp,
        "COMPARISON_TO_837395782": {
            "verdict": compare_verdict,
            "reasons": compare_reasons,
            "reference_package": "A1-SKU-837395782-GROWTH-FORENSIC",
        },
        "OPEN_GAPS": gaps,
        "CHECKED_AT_MSK": checked.strftime("%Y-%m-%d %H:%M:%S %Z"),
    }

    payload: dict[str, Any] = {
        "package": PACKAGE_NAME,
        "PACKAGE_STATUS": "AUTHORITATIVE",
        "RETURN": return_block,
        "collect_report": collect_report,
        "GAPS": gaps,
    }
    jp = pkg / f"{PACKAGE_NAME}.json"
    jp.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")

    names = [
        "DAILY_SKU_FUNNEL_SALES.csv",
        "DAILY_PHYSICAL_AD_PERFORMANCE.csv",
        "AD_CAMPAIGNS_MAPPING.csv",
        "SOURCE_PROVENANCE.md",
        f"{PACKAGE_NAME}.json",
    ]
    hashes = {n: _sha256_file(pkg / n) for n in names}
    (pkg / "PACKAGE_MANIFEST.json").write_text(
        json.dumps({"package": PACKAGE_NAME, "file_sha256": hashes}, indent=2),
        encoding="utf-8",
    )
    zout = root / f"{PACKAGE_NAME}.zip"
    with zipfile.ZipFile(zout, "w", zipfile.ZIP_DEFLATED) as zf:
        for n in names + ["PACKAGE_MANIFEST.json"]:
            zf.write(pkg / n, arcname=n)
    sha = _sha256_file(zout)
    payload["FINAL_ARCHIVE_SHA256"] = sha
    payload["ABSOLUTE_ARCHIVE_PATH"] = str(zout.resolve())
    jp.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")

    flat = {**return_block, "PACKAGE_STATUS": "AUTHORITATIVE", "FINAL_ARCHIVE_SHA256": sha}
    flat["ABSOLUTE_ARCHIVE_PATH"] = str(zout.resolve())
    return flat


async def run(
    root: Path,
    pg_rows: list[dict[str, str]],
    *,
    collect_zip: Path | None,
    skip_collect: bool,
) -> dict[str, Any]:
    cd = root / "collect"
    cd.mkdir(parents=True, exist_ok=True)
    cr = None
    if skip_collect and collect_zip and collect_zip.exists():
        zp = collect_zip
    else:
        cr = await _run_collect(cd)
        zp = _find_zip(cd)
    return build_package(root, zp, pg_rows, collect_report=cr)


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--output-dir", default=".tmp/a1_sku_195764899_forensic")
    ap.add_argument("--collect-zip", default="")
    ap.add_argument("--skip-collect", action="store_true")
    args = ap.parse_args(argv)
    root = Path(args.output_dir).resolve()
    root.mkdir(parents=True, exist_ok=True)
    sql_dir = root / "sql"
    _bootstrap_cluster_infra()
    pg_rows = _load_pg(root, sql_dir)
    cz = Path(args.collect_zip).resolve() if args.collect_zip else None
    out = asyncio.run(
        run(root, pg_rows, collect_zip=cz, skip_collect=args.skip_collect or bool(args.collect_zip))
    )
    print(json.dumps(out, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
