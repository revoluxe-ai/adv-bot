"""READ_ONLY: daily spend control + 29.08 sales/ad spend reconciliation (A1).

Собирает store orders/funnel, campaign fullstats, PG spend-control matrix,
CH spend (bot truth), portfolio-cap simulation и H1 gate check.
Никаких writes в WB/PG.
"""

from __future__ import annotations

import argparse
import asyncio
import csv
import hashlib
import json
import os
import sys
import zipfile
from collections import defaultdict
from datetime import date, datetime, timezone
from pathlib import Path
from typing import Any
from zoneinfo import ZoneInfo

import dotenv

dotenv.load_dotenv()

from scripts import ch_a1_evidence as evidence
from scripts.wb_a1_associated_conversions import _jsonable, _read_float, _read_int

SHOP_ID = "5339e9ad-cbfe-50fc-8d77-b9f337a80417"
MSK = ZoneInfo("Europe/Moscow")
PACKAGE_NAME = "A1-DAILY-SPEND-CONTROL-AND-20260829-RECONCILIATION"

ADS_FROM = date(2026, 8, 27)
ADS_TO = date(2026, 8, 30)
CLOSED_THROUGH = date(2026, 8, 29)
OPEN_DAY = date(2026, 8, 30)
TARGET_DAYS = ("2026-08-27", "2026-08-28", "2026-08-29", "2026-08-30")
ACTIVE_STATUSES = {9}

H1_AUTO = [17906286, 21604339]
H1_SEARCH = [20646357, 21604374]

SETTING_FIELDS = [
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
    "max_balance_adding_for_day",
    "aggressiveness",
    "strategy",
    "wb_bid_type",
    "wb_placement_search",
    "wb_placement_recommendations",
]

PORTFOLIO_TARGETS = (3500, 4000, 4500)


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
    ch_host = os.environ.get("CLICK_HOUSE_HOST")
    ch_port = os.environ.get("CLICKHOUSE_PORT", "8123")
    if ch_host:
        evidence.CH_HTTP_URL = f"http://{ch_host}:{ch_port}/"


def _day_state(day_str: str) -> str:
    try:
        d = date.fromisoformat(day_str[:10])
    except ValueError:
        return "UNKNOWN"
    if d == OPEN_DAY:
        return "OPEN_PARTIAL"
    if d <= CLOSED_THROUGH and d >= ADS_FROM:
        return "CLOSED"
    return "OUT_OF_SCOPE"


def _write_csv(path: Path, rows: list[dict[str, Any]], columns: list[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=columns, extrasaction="ignore")
        writer.writeheader()
        for row in rows:
            writer.writerow({c: row.get(c, "") for c in columns})


def _load_pg_advsettings(root: Path, sql_dir: Path) -> list[dict[str, str]]:
    staging = root / "staging"
    staging.mkdir(parents=True, exist_ok=True)
    path = staging / "advsetting_all.csv"
    cols = ", ".join(f"a.{c}" for c in SETTING_FIELDS)
    st = evidence.run_pg_query(
        _pg_database(),
        (
            f"SELECT {cols} FROM public.advsetting a "
            f"JOIN public.wbcabinet c ON a.wb_cabinet_id = c.id "
            f"WHERE c.shop_id = '{SHOP_ID}'"
        ),
        path,
        sql_dir / "pg_advsetting_shop.sql",
        csv_output=True,
    )
    if not st["success"]:
        raise RuntimeError(f"advsetting query failed: {st['stderr']}")
    with path.open(encoding="utf-8", newline="") as handle:
        return list(csv.DictReader(handle))


def _pg_by_adv_id(rows: list[dict[str, str]]) -> dict[int, dict[str, str]]:
    out: dict[int, dict[str, str]] = {}
    for row in rows:
        try:
            adv_id = int(row.get("adv_id") or 0)
        except (TypeError, ValueError):
            continue
        if adv_id:
            out[adv_id] = row
    return out


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
    redis_client_raw: Redis[str] = Redis(
        host=redis_config.host,
        port=redis_config.port,
        db=redis_config.db,
        password=redis_config.password,
        decode_responses=True,
    )
    await redis_client_raw.ping()
    redis_client_wrapper = RedisClient(redis_client=redis_client_raw)
    httpx_client_handler = HttpxClientHandler()
    await httpx_client_handler.init()
    try:
        await get_access_for_wb_cabinet(SHOP_ID)
        hub = WBManagerHubFactory(
            httpx_client_handler=httpx_client_handler,
            redis_client_wrapper=redis_client_wrapper,
        ).get_wb_manager_hub(SHOP_ID)
        report = await run_full_collect(
            shop_id=SHOP_ID,
            wb_data_manager=hub.wb_data_manager,
            output_dir=output_dir,
            orders_date_from=ADS_FROM.isoformat(),
            max_seconds=DEFAULT_COLLECT_MAX_SECONDS,
            max_api_calls=10_000,
            ads_date_from=ADS_FROM.isoformat(),
            ads_date_to=ADS_TO.isoformat(),
        )
        return report.to_dict()
    finally:
        await httpx_client_handler.shutdown()
        await redis_client_raw.close()


def _read_jsonl_from_zip(zf: zipfile.ZipFile, name: str) -> list[dict[str, Any]]:
    try:
        data = zf.read(name).decode("utf-8")
    except KeyError:
        return []
    rows: list[dict[str, Any]] = []
    for line in data.splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            row = json.loads(line)
            if isinstance(row, dict):
                rows.append(row)
        except json.JSONDecodeError:
            continue
    return rows


def _aggregate_fullstats(rows: list[dict[str, Any]]) -> dict[tuple[int, str], dict[str, Any]]:
    agg: dict[tuple[int, str], dict[str, Any]] = {}
    for row in rows:
        adv_id = _read_int(row, "advertId", "advert_id")
        day = str(row.get("date", ""))[:10]
        if not adv_id or not day:
            continue
        key = (adv_id, day)
        bucket = agg.setdefault(
            key,
            {
                "adv_id": adv_id,
                "date": day,
                "day_state": _day_state(day),
                "views": 0,
                "clicks": 0,
                "spend": 0.0,
                "orders": 0,
                "sum_price": 0.0,
            },
        )
        bucket["views"] += _read_int(row, "views")
        bucket["clicks"] += _read_int(row, "clicks")
        bucket["spend"] += _read_float(row, "sum", "spend")
        bucket["orders"] += _read_int(row, "orders")
        bucket["sum_price"] += _read_float(row, "sum_price")
    return agg


def _orders_store_daily(rows: list[dict[str, Any]]) -> dict[str, dict[str, Any]]:
    by_day: dict[str, dict[str, Any]] = defaultdict(
        lambda: {"factual_orders": 0, "order_value_rub": 0.0, "order_units": 0}
    )
    for row in rows:
        day = str(row.get("date") or row.get("lastChangeDate") or "")[:10]
        if not day or day not in TARGET_DAYS:
            continue
        by_day[day]["factual_orders"] += 1
        price = _read_float(row, "totalPrice", "finishedPrice", "priceWithDisc")
        by_day[day]["order_value_rub"] += price
        by_day[day]["order_units"] += 1
    out: dict[str, dict[str, Any]] = {}
    for day in TARGET_DAYS:
        bucket = by_day.get(day, {"factual_orders": 0, "order_value_rub": 0.0, "order_units": 0})
        out[day] = {
            **bucket,
            "day_state": _day_state(day),
            "source": "GET /api/v1/supplier/orders",
            "semantics": "factual supplier orders (row count = order events)",
        }
    return out


def _funnel_store_daily(rows: list[dict[str, Any]]) -> dict[str, dict[str, float]]:
    by_day: dict[str, dict[str, float]] = defaultdict(
        lambda: {"order_count": 0.0, "order_sum": 0.0, "add_to_cart": 0.0, "open_card": 0.0}
    )

    def _walk(obj: Any) -> None:
        if isinstance(obj, dict):
            day = str(obj.get("date") or obj.get("dt") or "")[:10]
            if day in TARGET_DAYS:
                if "orderCount" in obj or "order_count" in obj:
                    by_day[day]["order_count"] += _read_float(obj, "orderCount", "order_count")
                if "orderSum" in obj or "order_sum" in obj:
                    by_day[day]["order_sum"] += _read_float(obj, "orderSum", "order_sum")
                if "addToCart" in obj or "add_to_cart" in obj:
                    by_day[day]["add_to_cart"] += _read_float(obj, "addToCart", "add_to_cart")
                if "openCard" in obj or "open_card" in obj:
                    by_day[day]["open_card"] += _read_float(obj, "openCard", "open_card")
            for val in obj.values():
                _walk(val)
        elif isinstance(obj, list):
            for item in obj:
                _walk(item)

    for row in rows:
        _walk(row)

    out: dict[str, dict[str, float]] = {}
    for day in TARGET_DAYS:
        vals = by_day.get(day, {})
        out[day] = {
            "order_count": vals.get("order_count", 0.0),
            "order_sum": vals.get("order_sum", 0.0),
            "add_to_cart": vals.get("add_to_cart", 0.0),
            "open_card": vals.get("open_card", 0.0),
            "day_state": _day_state(day),
            "source": "POST /api/analytics/v3/sales-funnel/products/history",
            "semantics": "Sales Funnel store-aggregated metrics (analytics API)",
        }
    return out


def _orders_by_nm_day(rows: list[dict[str, Any]]) -> dict[tuple[int, str], dict[str, Any]]:
    agg: dict[tuple[int, str], dict[str, Any]] = {}
    for row in rows:
        day = str(row.get("date") or row.get("lastChangeDate") or "")[:10]
        nmid = _read_int(row, "nmId", "nm_id", "nmid")
        if not day or not nmid:
            continue
        key = (nmid, day)
        bucket = agg.setdefault(key, {"nm_id": nmid, "date": day, "factual_orders": 0, "order_value_rub": 0.0})
        bucket["factual_orders"] += 1
        bucket["order_value_rub"] += _read_float(row, "totalPrice", "finishedPrice", "priceWithDisc")
    return agg


def _load_ch_spend(root: Path, sql_dir: Path, adv_ids: list[int]) -> dict[tuple[int, str], float]:
    if not adv_ids:
        return {}
    staging = root / "staging"
    staging.mkdir(parents=True, exist_ok=True)
    out_path = staging / "ch_spend_daily.jsonl"
    ids_sql = ",".join(str(i) for i in sorted(set(adv_ids)))
    query = (
        "SELECT adv_id, toString(date) AS date, "
        "argMax(spend, version) AS spend "
        "FROM default_db.full_adv_wb_stat "
        f"WHERE date BETWEEN toDate('{ADS_FROM.isoformat()}') AND toDate('{ADS_TO.isoformat()}') "
        f"AND adv_id IN ({ids_sql}) "
        "GROUP BY adv_id, date"
    )
    st = evidence.run_ch_query(query, out_path, sql_dir / "ch_spend_daily.sql")
    if not st["success"]:
        return {}
    rows = evidence.read_jsonl(out_path)
    return {
        (int(r["adv_id"]), str(r["date"])[:10]): float(r.get("spend") or 0)
        for r in rows
        if r.get("adv_id") and r.get("date")
    }


def _campaign_inventory(
    campaigns: list[dict[str, Any]],
    pg_by_adv: dict[int, dict[str, str]],
) -> dict[int, dict[str, Any]]:
    inv: dict[int, dict[str, Any]] = {}
    for raw in campaigns:
        adv_id = _read_int(raw, "id", "advertId", "advert_id")
        if not adv_id:
            continue
        settings = raw.get("settings") if isinstance(raw.get("settings"), dict) else {}
        nm_settings = raw.get("nm_settings") or raw.get("nmSettings") or []
        nm_ids: list[int] = []
        if isinstance(nm_settings, list):
            for nm in nm_settings:
                if isinstance(nm, dict):
                    nmid = _read_int(nm, "nm_id", "nmId", "nmID")
                    if nmid:
                        nm_ids.append(nmid)
        pg_row = pg_by_adv.get(adv_id, {})
        placements = settings.get("placements") if isinstance(settings.get("placements"), dict) else {}
        inv[adv_id] = {
            "adv_id": adv_id,
            "nm_ids": nm_ids or _parse_nmids(str(pg_row.get("nmids") or "")),
            "wb_status": raw.get("status"),
            "bid_type": raw.get("bid_type"),
            "payment_type": settings.get("payment_type"),
            "placements": placements,
            "name": settings.get("name") or pg_row.get("name"),
        }
    return inv


def _build_store_daily_result(
    orders_daily: dict[str, dict[str, Any]],
    funnel_daily: dict[str, dict[str, float]],
    store_spend: dict[str, float],
) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for day in TARGET_DAYS:
        od = orders_daily.get(day, {})
        fd = funnel_daily.get(day, {})
        rows.append(
            {
                "date": day,
                "day_state": _day_state(day),
                "factual_orders": od.get("factual_orders", 0),
                "order_value_rub": round(float(od.get("order_value_rub") or 0), 2),
                "funnel_order_count": fd.get("order_count", 0),
                "funnel_order_sum": fd.get("order_sum", 0),
                "funnel_add_to_cart": fd.get("add_to_cart", 0),
                "funnel_open_card": fd.get("open_card", 0),
                "store_total_ad_spend_rub": round(float(store_spend.get(day, 0)), 2),
                "orders_source": od.get("source", ""),
                "funnel_source": fd.get("source", ""),
            }
        )
    return rows


def _build_campaign_daily_spend(
    stats: dict[tuple[int, str], dict[str, Any]],
    inventory: dict[int, dict[str, Any]],
    pg_by_adv: dict[int, dict[str, str]],
) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for (adv_id, day), bucket in sorted(stats.items()):
        if day not in TARGET_DAYS:
            continue
        inv = inventory.get(adv_id, {})
        pg = pg_by_adv.get(adv_id, {})
        nm_ids = inv.get("nm_ids") or []
        rows.append(
            {
                "date": day,
                "day_state": bucket.get("day_state"),
                "adv_id": adv_id,
                "nm_ids": ";".join(str(x) for x in nm_ids),
                "primary_nm_id": nm_ids[0] if nm_ids else "",
                "campaign_status": inv.get("wb_status"),
                "bid_type": inv.get("bid_type"),
                "payment_type": inv.get("payment_type"),
                "placements": json.dumps(inv.get("placements") or {}, ensure_ascii=False),
                "spend_rub": round(float(bucket.get("spend") or 0), 2),
                "views": bucket.get("views"),
                "clicks": bucket.get("clicks"),
                "attributed_orders": bucket.get("orders"),
                "attributed_gmv_rub": round(float(bucket.get("sum_price") or 0), 2),
                "direct_associative_split": "API_GAP",
                "campaign_name": inv.get("name") or pg.get("name"),
            }
        )
    return rows


def _top_spend_29(
    stats: dict[tuple[int, str], dict[str, Any]],
    inventory: dict[int, dict[str, Any]],
    orders_nm: dict[tuple[int, str], dict[str, Any]],
    store_spend_day: float,
) -> list[dict[str, Any]]:
    day = "2026-08-29"
    by_adv: dict[int, dict[str, Any]] = {}
    for (adv_id, d), bucket in stats.items():
        if d != day:
            continue
        by_adv[adv_id] = bucket
    ranked = sorted(by_adv.items(), key=lambda x: float(x[1].get("spend") or 0), reverse=True)
    rows: list[dict[str, Any]] = []
    for adv_id, bucket in ranked:
        if float(bucket.get("spend") or 0) <= 0:
            continue
        inv = inventory.get(adv_id, {})
        nm_ids = inv.get("nm_ids") or []
        factual_orders = 0
        factual_gmv = 0.0
        for nmid in nm_ids:
            nm_row = orders_nm.get((nmid, day), {})
            factual_orders += int(nm_row.get("factual_orders") or 0)
            factual_gmv += float(nm_row.get("order_value_rub") or 0)
        spend = float(bucket.get("spend") or 0)
        rows.append(
            {
                "adv_id": adv_id,
                "campaign_name": inv.get("name"),
                "primary_nm_id": nm_ids[0] if nm_ids else "",
                "spend_rub": round(spend, 2),
                "share_of_store_spend_pct": round(100 * spend / store_spend_day, 2) if store_spend_day else 0,
                "attributed_orders": bucket.get("orders"),
                "attributed_gmv_rub": round(float(bucket.get("sum_price") or 0), 2),
                "factual_sku_orders": factual_orders,
                "factual_sku_order_value_rub": round(factual_gmv, 2),
                "causal_claim": "FORBIDDEN",
            }
        )
    return rows


def _watchdog_on(row: dict[str, str]) -> bool:
    return str(row.get("auto_budget_watchdog_enabled")).lower() in ("true", "t", "1")


def _int_limit(val: str | None) -> int:
    try:
        return int(float(val or 0))
    except (TypeError, ValueError):
        return 0


def _build_control_matrix(
    pg_rows: list[dict[str, str]],
    inventory: dict[int, dict[str, Any]],
    stats: dict[tuple[int, str], dict[str, Any]],
    ch_spend: dict[tuple[int, str], float],
) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    seen_pairs: set[int] = set()

    def spend_for(adv_id: int, day: str) -> float:
        return float(stats.get((adv_id, day), {}).get("spend") or ch_spend.get((adv_id, day), 0))

    for row in pg_rows:
        try:
            auto_id = int(row.get("adv_id") or 0)
        except (TypeError, ValueError):
            continue
        if not auto_id:
            continue
        search_raw = (row.get("_search_adv_id") or "").strip()
        search_id = int(search_raw) if search_raw.isdigit() else None
        if search_id and auto_id in seen_pairs:
            continue
        inv_auto = inventory.get(auto_id, {})
        inv_search = inventory.get(search_id, {}) if search_id else {}
        status_auto = inv_auto.get("wb_status")
        status_search = inv_search.get("wb_status") if search_id else None
        is_active = status_auto in ACTIVE_STATUSES or (
            search_id and status_search in ACTIVE_STATUSES
        )
        if not is_active:
            continue
        if search_id:
            seen_pairs.add(auto_id)
        leg = "Auto+Search pair" if search_id else "standalone"
        rows.append(
            {
                "adv_id_auto": auto_id,
                "adv_id_search": search_id or "",
                "leg_type": leg,
                "bot_linked": str(row.get("bot_active")),
                "active_status": row.get("active_status"),
                "auto_budget_daily_limit": row.get("auto_budget_daily_limit"),
                "search_auto_budget_daily_limit": row.get("search_auto_budget_daily_limit"),
                "common_budget_daily_limit": row.get("common_budget_daily_limit"),
                "use_common_budget": row.get("use_common_budget"),
                "watchdog_enabled": row.get("auto_budget_watchdog_enabled"),
                "max_balance_adding_for_day": row.get("max_balance_adding_for_day"),
                "aggressiveness": row.get("aggressiveness"),
                "strategy": row.get("strategy"),
                "wb_budget_total": "API_GAP_IN_MATRIX",
                "spend_2026_08_27": round(spend_for(auto_id, "2026-08-27") + (spend_for(search_id, "2026-08-27") if search_id else 0), 2),
                "spend_2026_08_28": round(spend_for(auto_id, "2026-08-28") + (spend_for(search_id, "2026-08-28") if search_id else 0), 2),
                "spend_2026_08_29": round(spend_for(auto_id, "2026-08-29") + (spend_for(search_id, "2026-08-29") if search_id else 0), 2),
                "enforceable_daily_cap": _enforceable_cap(row),
                "cap_mechanism": _cap_mechanism(row),
            }
        )
    return rows


def _enforceable_cap(row: dict[str, str]) -> int:
    if not _watchdog_on(row):
        return 0
    if str(row.get("use_common_budget")).lower() in ("true", "t", "1"):
        return _int_limit(row.get("common_budget_daily_limit"))
    return _int_limit(row.get("auto_budget_daily_limit")) + _int_limit(
        row.get("search_auto_budget_daily_limit")
    )


def _portfolio_cap_sum(matrix: list[dict[str, Any]]) -> int:
    total = 0
    for row in matrix:
        pg_like = {
            "auto_budget_watchdog_enabled": row.get("watchdog_enabled"),
            "use_common_budget": row.get("use_common_budget"),
            "common_budget_daily_limit": row.get("common_budget_daily_limit"),
            "auto_budget_daily_limit": row.get("auto_budget_daily_limit"),
            "search_auto_budget_daily_limit": row.get("search_auto_budget_daily_limit"),
        }
        total += _enforceable_cap(pg_like)
    return total


def _portfolio_simulation(matrix: list[dict[str, Any]], active_adv_ids: list[int]) -> list[dict[str, Any]]:
    enforceable = [r for r in matrix if _int_limit(str(r.get("enforceable_daily_cap"))) > 0]
    uncontrolled = [r for r in matrix if _int_limit(str(r.get("enforceable_daily_cap"))) == 0]
    sum_caps = _portfolio_cap_sum(matrix)
    rows: list[dict[str, Any]] = []
    for target in PORTFOLIO_TARGETS:
        rows.append(
            {
                "total_daily_target_rub": target,
                "active_campaigns_in_contour": len(active_adv_ids),
                "matrix_rows_active": len(matrix),
                "enforceable_cap_rows": len(enforceable),
                "uncontrolled_rows": len(uncontrolled),
                "sum_configured_enforceable_caps_rub": sum_caps,
                "expected_max_controllable_spend_rub": sum_caps,
                "target_vs_sum_caps_delta": target - sum_caps,
                "portfolio_cap_guaranteed_at_target": (
                    "YES" if sum_caps <= target else "NO_overshoot_risk_if_all_hit_cap"
                ),
                "possible_overshoot_notes": (
                    "~60s watchdog tick; CH spend lag; top-up before pause in same tick; "
                    "H1/limit=0 legs unbounded"
                ),
                "uncontrolled_adv_ids": ";".join(
                    str(r.get("adv_id_auto")) for r in uncontrolled
                ),
            }
        )
    return rows


def _cap_mechanism(row: dict[str, str]) -> str:
    if not _watchdog_on(row):
        return "NONE_watchdog_disabled"
    if _int_limit(row.get("auto_budget_daily_limit")) == 0 and _int_limit(
        row.get("search_auto_budget_daily_limit")
    ) == 0 and _int_limit(row.get("common_budget_daily_limit")) == 0:
        return "NONE_limit_zero"
    if str(row.get("use_common_budget")).lower() in ("true", "t", "1"):
        return "common_budget_daily_limit_combined_auto_search"
    parts = []
    if _int_limit(row.get("auto_budget_daily_limit")) > 0:
        parts.append("auto_budget_daily_limit")
    if _int_limit(row.get("search_auto_budget_daily_limit")) > 0:
        parts.append("search_auto_budget_daily_limit")
    return "+".join(parts) if parts else "NONE"


def _h1_status(pg_by_adv: dict[int, dict[str, str]], inventory: dict[int, dict[str, Any]]) -> dict[str, Any]:
    h1_auto_ok = all(_int_limit(pg_by_adv.get(a, {}).get("auto_budget_daily_limit")) == 0 for a in H1_AUTO)
    h1_search_ok = all(a in inventory for a in H1_SEARCH)
    return {
        "status": "EXECUTED + OBSERVING",
        "observation_window": "OPEN",
        "overall_gate": "CONFIRMED" if h1_auto_ok and h1_search_ok else "CHANGED",
        "auto_campaigns": {
            str(a): {
                "auto_budget_daily_limit": pg_by_adv.get(a, {}).get("auto_budget_daily_limit"),
                "expected": 0,
            }
            for a in H1_AUTO
        },
        "search_campaigns": {
            str(a): {"present_in_wb_inventory": a in inventory} for a in H1_SEARCH
        },
        "causal_result_closed": False,
    }


def _build_code_trace_md() -> str:
    return """# DAILY_LIMIT_CODE_TRACE (adv-bot READ_ONLY)

## Field → enforcement

| PG field (`advsetting`) | Role | Enforced by |
|-------------------------|------|-------------|
| `auto_budget_daily_limit` | Auto leg daily **spend cap** (₽/MSK day), 0=off | `AutoAdvActiveControlService` + `AutoBudgetService` gates |
| `search_auto_budget_daily_limit` | Search/manual auction leg daily spend cap | same, `_search_campaign_handler` |
| `use_common_budget` | Combine Auto+Search spend pool | both legs vs `common_budget_daily_limit` |
| `common_budget_daily_limit` | Combined daily spend cap | `ensure_common_budget` + combined pause |
| `auto_budget_watchdog_enabled` | Master switch for top-up + pause pipeline | `CoroutinesManager.auto_budget_watchdog` |
| `max_balance_adding_for_day` | Daily top-up sum cap (deposit, not spend) | diagnostics only in scripts; not primary spend gate |

**WB `budget.total`** — remaining funds in campaign wallet (GET `/adv/v1/budget`), NOT a daily spend cap.

## Scheduler

`WBShop.run()` → `manager.auto_budget_watchdog()` (`@while_coroutine_decorator(60, 60)` ≈ **60s tick**).

Order per tick:
1. `AutoBudgetService.ensure_budget` / `ensure_common_budget` (top-up if WB balance < `AUTO_BUDGET_MIN_BALANCE`)
2. `finally`: `AutoAdvActiveControlService.ensure_campaigns_active` (pause/start)

Files:
- `app/modules/shop_runner/service_manager/manager.py`
- `app/modules/auto_budget_manager/service.py`
- `app/modules/shop_runner/service_manager/services/auto_adv_active_control/auto_adv_active_control_service.py`

## Spend measurement

- Timezone: **MSK (UTC+3)** calendar day; no cron — reset at 00:00 MSK implicit.
- Source: ClickHouse `default_db.full_adv_wb_stat`, `argMax(spend, version)` per `adv_id, date`.
- SQL: `app/modules/shop_runner/wb_stat_manager/clickhouse_manager/sql/get_spend_by_last_days.sql`

## Stop condition

- Pause when `spend_today >= limit` (limit>0).
- Limit=0 → campaign kept paused / not started by watchdog (`*_LIMIT_0`).
- WB mutation: **pause** via Promotion API (`pause_campaign`), not stop.

## Daily reset

Implicit at 00:00 MSK: new CH date slice + fresh `WBAutoBudgetTopUp.date_msk` sums.

## Answers to decision questions

| Question | Answer |
|----------|--------|
| Is `auto_budget_daily_limit` a real daily spend cap? | **YES** for Auto leg when watchdog on and limit>0 |
| Search manual cap field? | **`search_auto_budget_daily_limit`** on paired `advsetting` row |
| Standalone daily cap? | **YES** via `auto_budget_daily_limit` or `search_auto_budget_daily_limit` on standalone row |
| Common budget limits Auto+Search pair? | **YES** when `use_common_budget=true` — combined spend vs `common_budget_daily_limit` |
| Can watchdog/top-up bypass daily spend cap? | **Top-up blocked** when spend≥limit; **overshoot risk**: 60s tick, CH lag, top-up in `try` before pause in `finally`, fixed `AUTO_BUDGET_TOPUP_AMOUNT` step |
| Timezone reset | **Europe/Moscow** |
| Race/overspend | Spend may exceed cap briefly until next tick; top-up may add up to 1000₽ near limit |

## NOT covered by this pipeline

- Campaigns with `auto_budget_watchdog_enabled=false`
- Campaigns with all limits=0 (e.g. H1 autos)
- WB-native spend outside bot pause control
- WB seller UI autoreplenishment (`NOT_AVAILABLE_IN_API`)
"""


def _feasibility_verdict(matrix: list[dict[str, Any]], active_count: int) -> dict[str, Any]:
    uncontrolled = [r for r in matrix if _int_limit(str(r.get("enforceable_daily_cap"))) == 0]
    enforceable = [r for r in matrix if _int_limit(str(r.get("enforceable_daily_cap"))) > 0]
    h1_in_matrix = [r for r in uncontrolled if int(r.get("adv_id_auto") or 0) in H1_AUTO]
    if len(uncontrolled) > len(h1_in_matrix):
        answer = "PARTIAL"
        mechanism = "Per-leg/common daily limits via watchdog for subset of bot-linked pairs only"
    elif uncontrolled:
        answer = "PARTIAL"
        mechanism = "H1 and limit=0 legs unbounded; enforceable caps on watchdog+limit>0 rows"
    elif enforceable:
        answer = "YES_WITH_MECHANISM"
        mechanism = "Sum of enforceable PG daily limits + 60s pause/top-up gates"
    else:
        answer = "NO"
        mechanism = "No enforceable caps configured"
    return {
        "CAN_FULL_ACTIVE_CONTOUR_BE_BOUNDED_TO_A_PREDICTABLE_DAILY_SPEND": answer,
        "ENFORCEMENT_MECHANISM": mechanism,
        "UNCONTROLLED_CAMPAIGNS": [
            {
                "adv_id_auto": r.get("adv_id_auto"),
                "reason": r.get("cap_mechanism"),
            }
            for r in uncontrolled
        ],
        "EXPECTED_OVERSHOOT": (
            "Up to ~60s spend between ticks; CH ingestion lag; single top-up step (1000₽) "
            "may execute before pause when near cap"
        ),
    }


async def run_package(output_dir: Path, pg_rows: list[dict[str, str]]) -> dict[str, Any]:
    """Собрать полный reconciliation package."""
    output_dir.mkdir(parents=True, exist_ok=True)
    sql_dir = output_dir / "sql"
    sql_dir.mkdir(parents=True, exist_ok=True)
    checked_msk = datetime.now(timezone.utc).astimezone(MSK)

    pg_by_adv = _pg_by_adv_id(pg_rows)

    collect_dir = output_dir / "collect"
    collect_report = await _run_collect(collect_dir)
    zip_path = collect_dir / "wb_readonly_research.zip"
    if not zip_path.exists():
        raise RuntimeError("collect zip missing")

    with zipfile.ZipFile(zip_path) as zf:
        fullstats = _read_jsonl_from_zip(zf, "raw/ads/fullstats.jsonl")
        orders = _read_jsonl_from_zip(zf, "orders.jsonl")
        funnel = _read_jsonl_from_zip(zf, "funnel/funnel.jsonl")
        campaigns = _read_jsonl_from_zip(zf, "raw/ads/campaigns.jsonl")

    stats = _aggregate_fullstats(fullstats)
    inventory = _campaign_inventory(campaigns, pg_by_adv)
    active_adv_ids = sorted(
        adv_id for adv_id, inv in inventory.items() if inv.get("wb_status") in ACTIVE_STATUSES
    )
    ch_spend = _load_ch_spend(output_dir, sql_dir, list(inventory.keys()))

    store_spend = defaultdict(float)
    for (_adv, day), row in stats.items():
        if day in TARGET_DAYS:
            store_spend[day] += float(row.get("spend") or 0)

    orders_daily = _orders_store_daily(orders)
    funnel_daily = _funnel_store_daily(funnel)
    orders_nm = _orders_by_nm_day(orders)

    store_rows = _build_store_daily_result(orders_daily, funnel_daily, dict(store_spend))
    campaign_rows = _build_campaign_daily_spend(stats, inventory, pg_by_adv)
    top29 = _top_spend_29(stats, inventory, orders_nm, float(store_spend.get("2026-08-29", 0)))
    matrix = _build_control_matrix(pg_rows, inventory, stats, ch_spend)
    portfolio = _portfolio_simulation(matrix, active_adv_ids)
    h1 = _h1_status(pg_by_adv, inventory)
    feasibility = _feasibility_verdict(matrix, len(active_adv_ids))

    pkg = output_dir / PACKAGE_NAME
    pkg.mkdir(parents=True, exist_ok=True)

    _write_csv(
        pkg / "STORE_DAILY_RESULT.csv",
        store_rows,
        [
            "date",
            "day_state",
            "factual_orders",
            "order_value_rub",
            "funnel_order_count",
            "funnel_order_sum",
            "funnel_add_to_cart",
            "funnel_open_card",
            "store_total_ad_spend_rub",
            "orders_source",
            "funnel_source",
        ],
    )
    _write_csv(
        pkg / "CAMPAIGN_DAILY_SPEND.csv",
        campaign_rows,
        list(campaign_rows[0].keys()) if campaign_rows else ["date", "adv_id", "spend_rub"],
    )
    _write_csv(
        pkg / "TOP_SPEND_20260829.csv",
        top29,
        list(top29[0].keys()) if top29 else ["adv_id", "spend_rub"],
    )
    _write_csv(
        pkg / "CURRENT_DAILY_SPEND_CONTROL_MATRIX.csv",
        matrix,
        list(matrix[0].keys()) if matrix else ["adv_id_auto"],
    )
    (pkg / "DAILY_LIMIT_CODE_TRACE.md").write_text(_build_code_trace_md(), encoding="utf-8")
    _write_csv(
        pkg / "PORTFOLIO_CAP_SIMULATION.csv",
        portfolio,
        list(portfolio[0].keys()) if portfolio else ["total_daily_target_rub"],
    )

    day29_store = next((r for r in store_rows if r["date"] == "2026-08-29"), {})
    summary = {
        "29_08_STORE_RESULT": day29_store,
        "29_08_TOTAL_AD_SPEND": round(float(store_spend.get("2026-08-29", 0)), 2),
        "29_08_AD_LOAD_BY_DENOMINATOR": {
            "ad_spend_rub": round(float(store_spend.get("2026-08-29", 0)), 2),
            "factual_order_value_rub": day29_store.get("order_value_rub"),
            "funnel_order_sum": day29_store.get("funnel_order_sum"),
            "note": "Ratio is descriptive only; not causal",
        },
        "TOP_SPEND_CAMPAIGNS": top29[:10],
        "FULL_CONTOUR_DAILY_CAP_FEASIBILITY": feasibility,
        "H1_STATUS": h1,
        "GAPS": [
            {
                "kind": "API_GAP",
                "missing": "direct/associative attribution split in fullstats",
            },
            {
                "kind": "API_GAP",
                "missing": "per-campaign WB budget.total in control matrix (live budget call skipped)",
            },
            {
                "kind": "API_GAP",
                "missing": "WB native autoreplenishment settings",
            },
        ],
    }

    payload: dict[str, Any] = {
        "package": PACKAGE_NAME,
        "checked_at_msk": checked_msk.strftime("%Y-%m-%d %H:%M:%S %Z"),
        "shop_id": SHOP_ID,
        "mode": "STRICT_READ_ONLY",
        "provenance": {
            "collect_report": collect_report,
            "zip_path": str(zip_path),
            "ads_date_from": ADS_FROM.isoformat(),
            "ads_date_to": ADS_TO.isoformat(),
        },
        "coverage": {
            "fullstats_rows": len(fullstats),
            "orders_rows": len(orders),
            "funnel_rows": len(funnel),
            "active_campaigns_wb_status_9": len(active_adv_ids),
            "ch_spend_keys": len(ch_spend),
        },
        "STORE_DAILY_RESULT": store_rows,
        "STORE_TOTAL_AD_SPEND_BY_DAY": {d: round(store_spend.get(d, 0), 2) for d in TARGET_DAYS},
        "CURRENT_DAILY_SPEND_CONTROL_MATRIX": matrix,
        "PORTFOLIO_CAP_SIMULATION": portfolio,
        "summary": summary,
    }

    json_path = pkg / f"{PACKAGE_NAME}.json"
    json_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")

    md_lines = [
        f"# {PACKAGE_NAME}",
        "",
        f"**checked_at:** {payload['checked_at_msk']}",
        f"**shop_id:** `{SHOP_ID}`",
        "",
        "## 29.08 snapshot",
        "",
        f"- Factual orders: **{day29_store.get('factual_orders')}**",
        f"- Order value: **{day29_store.get('order_value_rub')} ₽**",
        f"- Funnel orders/sum: **{day29_store.get('funnel_order_count')}** / **{day29_store.get('funnel_order_sum')} ₽**",
        f"- Total ad spend: **{summary['29_08_TOTAL_AD_SPEND']} ₽**",
        "",
        "## Spend vs 27–28.08",
        "",
    ]
    for d in ("2026-08-27", "2026-08-28", "2026-08-29"):
        row = next((r for r in store_rows if r["date"] == d), {})
        md_lines.append(
            f"- {d}: spend **{row.get('store_total_ad_spend_rub')} ₽**, "
            f"orders **{row.get('factual_orders')}**, value **{row.get('order_value_rub')} ₽**"
        )
    md_lines.extend(
        [
            "",
            "## Portfolio cap feasibility",
            "",
            f"- **{feasibility['CAN_FULL_ACTIVE_CONTOUR_BE_BOUNDED_TO_A_PREDICTABLE_DAILY_SPEND']}**",
            f"- Mechanism: {feasibility['ENFORCEMENT_MECHANISM']}",
            f"- Uncontrolled rows: **{len(feasibility['UNCONTROLLED_CAMPAIGNS'])}**",
            "",
            "## H1",
            "",
            f"- Status: **{h1['status']}** ({h1['overall_gate']})",
            "",
            "## Top spend 29.08",
            "",
        ]
    )
    for row in top29[:8]:
        md_lines.append(
            f"- adv_id **{row['adv_id']}**: {row['spend_rub']} ₽ "
            f"({row['share_of_store_spend_pct']}%) — factual SKU orders {row['factual_sku_orders']}"
        )
    (pkg / "RECONCILIATION.md").write_text("\n".join(md_lines), encoding="utf-8")
    payload["output_dir"] = str(pkg.resolve())
    return payload


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="A1 daily spend control reconciliation READ_ONLY.")
    parser.add_argument("--output-dir", default=".tmp/a1_daily_spend_control")
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    out = Path(args.output_dir).resolve()
    _bootstrap_cluster_infra()
    sql_dir = out / "sql"
    pg_rows = _load_pg_advsettings(out, sql_dir)
    result = asyncio.run(run_package(out, pg_rows))
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
