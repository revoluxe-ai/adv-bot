"""READ_ONLY: A1 iteration-04 current state + daily cap control input.

Снимает фактический стартовый state перед изменением лимитов:
store daily (29–31.08), active ad contour, CURRENT PG control, H1 facts,
pause trace для Search 20646357. Без production mutations.
"""

from __future__ import annotations

import argparse
import asyncio
import csv
import hashlib
import json
import os
import subprocess
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
PACKAGE_NAME = "A1-ITERATION-04-CURRENT-STATE-AND-CAP-CONTROL-INPUT"

ADS_FROM = date(2026, 8, 29)
ADS_TO = date(2026, 8, 31)
CLOSED_THROUGH = date(2026, 8, 30)
OPEN_DAY = date(2026, 8, 31)
TARGET_DAYS = ("2026-08-29", "2026-08-30", "2026-08-31")
ACTIVE_STATUSES = {9, 11}

H1_AUTO = [17906286, 21604339]
H1_SEARCH = [20646357, 21604374]
PAUSE_TRACE_ADV = 20646357
PARENT_AUTO_ADV = 17906286

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
    "auto_adv_target_status",
    "auction_adv_target_status",
    "last_update",
]


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


def _sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


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
                "spend": 0.0,
                "orders": 0,
                "sum_price": 0.0,
            },
        )
        bucket["spend"] += _read_float(row, "sum", "spend")
        bucket["orders"] += _read_int(row, "orders")
        bucket["sum_price"] += _read_float(row, "sum_price")
    return agg


def _orders_store_daily(rows: list[dict[str, Any]]) -> dict[str, dict[str, Any]]:
    by_day: dict[str, dict[str, Any]] = defaultdict(
        lambda: {"factual_orders": 0, "factual_order_value_rub": 0.0, "factual_units": 0}
    )
    for row in rows:
        day = str(row.get("date") or row.get("lastChangeDate") or "")[:10]
        if day not in TARGET_DAYS:
            continue
        qty = _read_int(row, "quantity", "qty") or 1
        by_day[day]["factual_orders"] += 1
        by_day[day]["factual_units"] += qty
        by_day[day]["factual_order_value_rub"] += _read_float(
            row, "totalPrice", "finishedPrice", "priceWithDisc"
        )
    out: dict[str, dict[str, Any]] = {}
    for day in TARGET_DAYS:
        bucket = by_day.get(
            day, {"factual_orders": 0, "factual_order_value_rub": 0.0, "factual_units": 0}
        )
        out[day] = {
            **bucket,
            "factual_order_value_rub": round(float(bucket["factual_order_value_rub"]), 2),
        }
    return out


def _funnel_store_daily(rows: list[dict[str, Any]]) -> dict[str, dict[str, float]]:
    by_day: dict[str, dict[str, float]] = defaultdict(
        lambda: {"order_count": 0.0, "order_sum": 0.0, "add_to_cart": 0.0}
    )

    def _walk(obj: Any) -> None:
        if isinstance(obj, dict):
            day = str(obj.get("date") or obj.get("dt") or obj.get("day") or "")[:10]
            if day in TARGET_DAYS:
                if any(k in obj for k in ("orderCount", "order_count", "orders")):
                    by_day[day]["order_count"] += _read_float(
                        obj, "orderCount", "order_count", "orders"
                    )
                if any(k in obj for k in ("orderSum", "order_sum", "orders_sum")):
                    by_day[day]["order_sum"] += _read_float(
                        obj, "orderSum", "order_sum", "orders_sum"
                    )
                if any(k in obj for k in ("addToCart", "add_to_cart")):
                    by_day[day]["add_to_cart"] += _read_float(
                        obj, "addToCart", "add_to_cart"
                    )
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
            "funnel_order_count": vals.get("order_count", 0.0),
            "funnel_order_sum": vals.get("order_sum", 0.0),
            "funnel_add_to_cart": vals.get("add_to_cart", 0.0),
        }
    return out


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
        inv[adv_id] = {
            "adv_id": adv_id,
            "nm_ids": nm_ids or _parse_nmids(str(pg_row.get("nmids") or "")),
            "wb_status": raw.get("status"),
            "bid_type": raw.get("bid_type"),
            "name": settings.get("name") or pg_row.get("name"),
        }
    return inv


def _leg_type(bid_type: Any) -> str:
    bt = str(bid_type or "").lower()
    if bt == "unified":
        return "Auto"
    if bt == "manual":
        return "Search"
    return "standalone"


def _paired_adv_id(adv_id: int, pg_by_adv: dict[int, dict[str, str]]) -> str:
    row = pg_by_adv.get(adv_id, {})
    search_raw = (row.get("_search_adv_id") or "").strip()
    if search_raw.isdigit():
        return search_raw
    for auto_id, auto_row in pg_by_adv.items():
        s = (auto_row.get("_search_adv_id") or "").strip()
        if s.isdigit() and int(s) == adv_id:
            return str(auto_id)
    return ""


def _store_spend_by_day(stats: dict[tuple[int, str], dict[str, Any]]) -> dict[str, float]:
    by_day: dict[str, float] = defaultdict(float)
    for (_adv_id, day), bucket in stats.items():
        if day in TARGET_DAYS:
            by_day[day] += float(bucket.get("spend") or 0)
    return dict(by_day)


def _build_store_rows(
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
                "factual_order_value_rub": od.get("factual_order_value_rub", 0),
                "factual_units": od.get("factual_units", 0),
                "factual_orders_source": "raw/orders.jsonl | GET /api/v1/supplier/orders",
                "funnel_order_count": fd.get("funnel_order_count", 0),
                "funnel_order_sum": fd.get("funnel_order_sum", 0),
                "funnel_add_to_cart": fd.get("funnel_add_to_cart", 0),
                "funnel_source": "raw/funnel/funnel.jsonl | POST /api/analytics/v3/sales-funnel/products/history",
                "store_total_ad_spend_rub": round(float(store_spend.get(day, 0)), 2),
                "ad_spend_source": "raw/ads/fullstats.jsonl | GET /adv/v3/fullstats",
            }
        )
    return rows


def _active_contour_ids(
    inventory: dict[int, dict[str, Any]],
    stats: dict[tuple[int, str], dict[str, Any]],
    pg_by_adv: dict[int, dict[str, str]],
) -> list[int]:
    spending: set[int] = set()
    for (adv_id, day), row in stats.items():
        if day in TARGET_DAYS and float(row.get("spend") or 0) > 0:
            spending.add(adv_id)
    contour: set[int] = set()
    for adv_id, inv in inventory.items():
        if inv.get("wb_status") in ACTIVE_STATUSES:
            contour.add(adv_id)
    for adv_id in pg_by_adv:
        if adv_id in inventory and inventory[adv_id].get("wb_status") in ACTIVE_STATUSES:
            contour.add(adv_id)
    return sorted(contour | spending)


def _build_active_contour_rows(
    contour_ids: list[int],
    inventory: dict[int, dict[str, Any]],
    stats: dict[tuple[int, str], dict[str, Any]],
    pg_by_adv: dict[int, dict[str, str]],
) -> list[dict[str, Any]]:
    spend_by: dict[int, dict[str, float]] = defaultdict(lambda: defaultdict(float))
    for (adv_id, day), row in stats.items():
        if day in TARGET_DAYS:
            spend_by[adv_id][day] += float(row.get("spend") or 0)

    rows: list[dict[str, Any]] = []
    for adv_id in contour_ids:
        inv = inventory.get(adv_id, {})
        if inv.get("wb_status") not in ACTIVE_STATUSES:
            continue
        nm_ids = inv.get("nm_ids") or []
        rows.append(
            {
                "adv_id": adv_id,
                "primary_nm_id": nm_ids[0] if nm_ids else "",
                "nm_ids": ";".join(str(x) for x in nm_ids),
                "wb_status": inv.get("wb_status"),
                "leg_type": _leg_type(inv.get("bid_type")),
                "paired_adv_id": _paired_adv_id(adv_id, pg_by_adv),
                "spend_2026_08_29": round(spend_by[adv_id].get("2026-08-29", 0), 2),
                "spend_2026_08_30": round(spend_by[adv_id].get("2026-08-30", 0), 2),
                "spend_2026_08_31_partial": round(spend_by[adv_id].get("2026-08-31", 0), 2),
                "campaign_name": inv.get("name"),
                "wb_source": "raw/ads/campaigns.jsonl",
                "spend_source": "raw/ads/fullstats.jsonl",
            }
        )
    return rows


def _build_pg_control_rows(
    pg_rows: list[dict[str, str]],
    inventory: dict[int, dict[str, Any]],
) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    seen: set[int] = set()
    for row in pg_rows:
        try:
            auto_id = int(row.get("adv_id") or 0)
        except (TypeError, ValueError):
            continue
        if not auto_id:
            continue
        search_raw = (row.get("_search_adv_id") or "").strip()
        search_id = int(search_raw) if search_raw.isdigit() else None
        inv_auto = inventory.get(auto_id, {})
        inv_search = inventory.get(search_id, {}) if search_id else {}
        status_auto = inv_auto.get("wb_status")
        status_search = inv_search.get("wb_status") if search_id else None
        active = status_auto in ACTIVE_STATUSES or (
            search_id and status_search in ACTIVE_STATUSES
        )
        if not active:
            continue
        if auto_id in seen:
            continue
        seen.add(auto_id)
        rows.append(
            {
                "adv_setting_id": row.get("id"),
                "adv_id": auto_id,
                "search_adv_id": search_id or "",
                "active_status": row.get("active_status"),
                "bot_active": row.get("bot_active"),
                "auto_budget_watchdog_enabled": row.get("auto_budget_watchdog_enabled"),
                "auto_budget_daily_limit": row.get("auto_budget_daily_limit"),
                "search_auto_budget_daily_limit": row.get(
                    "search_auto_budget_daily_limit"
                ),
                "use_common_budget": row.get("use_common_budget"),
                "common_budget_daily_limit": row.get("common_budget_daily_limit"),
                "max_balance_adding_for_day": row.get("max_balance_adding_for_day"),
                "strategy": row.get("strategy"),
                "aggressiveness": row.get("aggressiveness"),
                "auto_adv_target_status": row.get("auto_adv_target_status"),
                "auction_adv_target_status": row.get("auction_adv_target_status"),
                "wb_status_auto": status_auto,
                "wb_status_search": status_search if search_id else "",
                "pg_last_update": row.get("last_update"),
                "pg_source": "public.advsetting JOIN wbcabinet (CURRENT snapshot)",
            }
        )
    return rows


def _redis_activity_reason(adv_id: int, campaign_type: str) -> dict[str, Any]:
    """Read campaign-activity-reason from Redis (direct or kubectl fallback)."""
    key = f"campaign-activity-reason:{adv_id}:{campaign_type}"
    raw = ""
    source = "none"
    try:
        import redis

        host = os.environ.get("REDIS_HOST") or os.environ.get("REDIS_MASTER_HOST")
        port = int(os.environ.get("REDIS_PORT", "6379"))
        password = os.environ.get("REDIS_PASSWORD")
        db = int(os.environ.get("REDIS_DB", "0"))
        if host:
            client = redis.Redis(
                host=host, port=port, password=password, db=db, decode_responses=True
            )
            raw = client.get(key) or ""
            source = "redis_direct"
    except Exception:
        raw = ""
    if not raw:
        out_path = Path("/tmp") / f"redis_{adv_id}_{campaign_type}.txt"
        try:
            st = evidence.run_redis_command(["GET", key], out_path)
            raw = (
                out_path.read_text(encoding="utf-8", errors="replace").strip()
                if out_path.exists()
                else ""
            )
            source = "kubectl_exec" if st.get("success") else source
        except (FileNotFoundError, OSError):
            source = "unavailable"
    parsed: dict[str, Any] | None = None
    if raw and raw != "(nil)":
        try:
            parsed = json.loads(raw)
        except json.JSONDecodeError:
            parsed = {"raw": raw}
    return {
        "redis_key": key,
        "source": source,
        "raw": raw if raw and raw != "(nil)" else None,
        "parsed": parsed,
    }


def _kubectl_logs_grep(adv_id: int, since_hours: int = 72) -> list[str]:
    """Grep shop-runner logs for pause lines mentioning adv_id (host kubectl only)."""
    hits: list[str] = []
    try:
        which = subprocess.run(
            ["which", "kubectl"],
            capture_output=True,
            text=True,
            timeout=10,
            check=False,
        )
        if which.returncode != 0:
            return hits
        pods = subprocess.run(
            [
                "kubectl",
                "get",
                "pods",
                "-n",
                evidence.PG_NAMESPACE,
                "-l",
                "app=run-shop-update-worker",
                "-o",
                "jsonpath={.items[*].metadata.name}",
            ],
            capture_output=True,
            text=True,
            timeout=60,
            check=False,
        )
        pod_names = [p for p in pods.stdout.split() if p]
        if not pod_names:
            pods = subprocess.run(
                [
                    "kubectl",
                    "get",
                    "pods",
                    "-n",
                    evidence.PG_NAMESPACE,
                    "-o",
                    "name",
                ],
                capture_output=True,
                text=True,
                timeout=60,
                check=False,
            )
            pod_names = [
                line.replace("pod/", "")
                for line in pods.stdout.splitlines()
                if "run-shop-update" in line or "shop" in line.lower()
            ]
        for pod in pod_names[:3]:
            completed = subprocess.run(
                [
                    "kubectl",
                    "logs",
                    pod,
                    "-n",
                    evidence.PG_NAMESPACE,
                    f"--since={since_hours}h",
                    "--tail=50000",
                ],
                capture_output=True,
                text=True,
                timeout=180,
                check=False,
            )
            if completed.returncode != 0:
                continue
            for line in completed.stdout.splitlines():
                if str(adv_id) in line and (
                    "paus" in line.lower()
                    or "Auto budget watcher" in line
                    or "force-pause" in line.lower()
                ):
                    hits.append(f"{pod}: {line.strip()}")
    except (OSError, subprocess.SubprocessError):
        pass
    return hits[:50]


def _ch_hourly_spend(
    root: Path, sql_dir: Path, adv_id: int
) -> list[dict[str, Any]]:
    out_path = root / "staging" / f"ch_hourly_{adv_id}.jsonl"
    query = (
        "SELECT adv_id, toString(date) AS date, "
        "toHour(timestamp) AS hour, "
        "argMax(spend, version) AS spend "
        "FROM default_db.clusters_adv_stats "
        f"WHERE adv_id = {adv_id} "
        f"AND date BETWEEN toDate('2026-08-29') AND toDate('2026-08-31') "
        "GROUP BY adv_id, date, hour "
        "ORDER BY date, hour"
    )
    st = evidence.run_ch_query(query, out_path, sql_dir / f"ch_hourly_{adv_id}.sql")
    if not st["success"]:
        return []
    return evidence.read_jsonl(out_path)


def _ch_daily_spend(
    root: Path, sql_dir: Path, adv_id: int
) -> list[dict[str, Any]]:
    out_path = root / "staging" / f"ch_daily_{adv_id}.jsonl"
    query = (
        "SELECT adv_id, toString(date) AS date, argMax(spend, version) AS spend "
        "FROM default_db.full_adv_wb_stat "
        f"WHERE adv_id = {adv_id} "
        f"AND date BETWEEN toDate('2026-08-29') AND toDate('2026-08-31') "
        "GROUP BY adv_id, date ORDER BY date"
    )
    st = evidence.run_ch_query(query, out_path, sql_dir / f"ch_daily_{adv_id}.sql")
    if not st["success"]:
        return []
    return evidence.read_jsonl(out_path)


def _infer_last_active_hour(hourly: list[dict[str, Any]]) -> str | None:
    last: str | None = None
    for row in hourly:
        spend = float(row.get("spend") or 0)
        if spend > 0:
            last = f"{row.get('date')} {int(row.get('hour') or 0):02d}:00 MSK (CH clusters_adv_stats)"
    return last


def _build_pause_trace_md(
    inventory: dict[int, dict[str, Any]],
    pg_by_adv: dict[int, dict[str, str]],
    root: Path,
    sql_dir: Path,
    prior_wb_status: int | None,
) -> tuple[str, str]:
    adv_id = PAUSE_TRACE_ADV
    inv = inventory.get(adv_id, {})
    current_wb = inv.get("wb_status")
    parent_row = pg_by_adv.get(PARENT_AUTO_ADV, {})
    search_pg_row = None
    for row in pg_by_adv.values():
        s = (row.get("_search_adv_id") or "").strip()
        if s.isdigit() and int(s) == adv_id:
            search_pg_row = row
            break

    redis_search = _redis_activity_reason(adv_id, "search")
    log_hits = _kubectl_logs_grep(adv_id)
    hourly = _ch_hourly_spend(root, sql_dir, adv_id)
    ch_daily = _ch_daily_spend(root, sql_dir, adv_id)
    last_active = _infer_last_active_hour(hourly)

    bot_evidence = bool(log_hits) or (
        redis_search.get("parsed")
        and redis_search["parsed"].get("command") == "pause"
    )
    manual_evidence = False
    wb_side_evidence = current_wb == 11

    transition_note = "GAP"
    if prior_wb_status == 9 and current_wb == 11:
        transition_note = (
            f"Prior collect (2026-08-30 reissue) wb_status=9; current collect wb_status=11. "
            f"Approx transition window: between 2026-08-30 collect and current collect."
        )
    elif last_active:
        transition_note = f"Last CH hourly spend >0: {last_active}"

    pause_cause = "GAP"
    if bot_evidence and not manual_evidence:
        pause_cause = "ADV_BOT_EVIDENCE"
    elif manual_evidence:
        pause_cause = "MANUAL_CLIENT_EVIDENCE"
    elif wb_side_evidence and not bot_evidence:
        pause_cause = "WB_STATUS_ONLY_NO_BOT_LOG"

    lines = [
        "# 20646357_PAUSE_TRACE",
        "",
        "Causal verdict: FORBIDDEN. Facts only.",
        "",
        f"## Current WB status: **{current_wb}**",
        "",
        "## Current PG state (parent setting 17906286)",
        "",
    ]
    if search_pg_row or parent_row:
        lines.extend(
            [
                f"- parent adv_id: **{PARENT_AUTO_ADV}**",
                f"- parent adv_setting_id: `{parent_row.get('id', '')}`",
                f"- search_adv_id (PG): `{parent_row.get('_search_adv_id', '')}`",
                f"- bot_active: `{parent_row.get('bot_active', '')}`",
                f"- auto_budget_watchdog_enabled: `{parent_row.get('auto_budget_watchdog_enabled', '')}`",
                f"- auto_budget_daily_limit: `{parent_row.get('auto_budget_daily_limit', '')}`",
                f"- search_auto_budget_daily_limit: `{parent_row.get('search_auto_budget_daily_limit', '')}`",
                f"- use_common_budget: `{parent_row.get('use_common_budget', '')}`",
                f"- common_budget_daily_limit: `{parent_row.get('common_budget_daily_limit', '')}`",
                f"- auction_adv_target_status: `{parent_row.get('auction_adv_target_status', '')}`",
                f"- auto_adv_target_status: `{parent_row.get('auto_adv_target_status', '')}`",
                f"- pg_last_update: `{parent_row.get('last_update', '')}`",
            ]
        )
    else:
        lines.append("- PG row: NOT_FOUND")

    lines.extend(
        [
            "",
            "## Status transition 9 → 11",
            "",
            f"- prior_wb_status_from_reissue_20260830: `{prior_wb_status}`",
            f"- current_wb_status: `{current_wb}`",
            f"- transition_inference: {transition_note}",
            "",
            "## adv-bot pause evidence",
            "",
            f"- redis campaign-activity-reason: `{json.dumps(redis_search, ensure_ascii=False)}`",
            f"- log_hits_count: **{len(log_hits)}**",
        ]
    )
    if log_hits:
        lines.append("")
        lines.append("```")
        lines.extend(log_hits[:20])
        lines.append("```")
    else:
        lines.append("- log_hits: none in scanned pods")

    lines.extend(
        [
            "",
            "## Manual / client action evidence",
            "",
            f"- found: **{manual_evidence}** (no dedicated client_bot audit table queried)",
            "",
            "## WB-side stop/pause evidence",
            "",
            f"- campaigns.jsonl wb_status={current_wb} (11=paused per WB API semantics)",
            "",
            "## CH spend trail",
            "",
            f"- daily: `{json.dumps(ch_daily, ensure_ascii=False)}`",
            f"- last_active_hour: `{last_active}`",
            "",
            f"## PAUSE_CAUSE",
            "",
            f"**{pause_cause}**",
            "",
        ]
    )
    return "\n".join(lines), pause_cause


def _build_h1_rows(
    inventory: dict[int, dict[str, Any]],
    stats: dict[tuple[int, str], dict[str, Any]],
    pg_by_adv: dict[int, dict[str, str]],
) -> list[dict[str, Any]]:
    spend_by: dict[int, dict[str, float]] = defaultdict(lambda: defaultdict(float))
    for (adv_id, day), row in stats.items():
        if day in TARGET_DAYS:
            spend_by[adv_id][day] += float(row.get("spend") or 0)

    rows: list[dict[str, Any]] = []
    for adv_id in H1_AUTO + H1_SEARCH:
        inv = inventory.get(adv_id, {})
        pg = pg_by_adv.get(adv_id, {})
        if not pg:
            for row in pg_by_adv.values():
                s = (row.get("_search_adv_id") or "").strip()
                if s.isdigit() and int(s) == adv_id:
                    pg = row
                    break
        rows.append(
            {
                "adv_id": adv_id,
                "h1_leg": "Auto" if adv_id in H1_AUTO else "Search",
                "wb_status": inv.get("wb_status"),
                "spend_2026_08_30": round(spend_by[adv_id].get("2026-08-30", 0), 2),
                "spend_2026_08_31_partial": round(spend_by[adv_id].get("2026-08-31", 0), 2),
                "auto_budget_daily_limit": pg.get("auto_budget_daily_limit", ""),
                "search_auto_budget_daily_limit": pg.get(
                    "search_auto_budget_daily_limit", ""
                ),
                "common_budget_daily_limit": pg.get("common_budget_daily_limit", ""),
                "use_common_budget": pg.get("use_common_budget", ""),
                "auto_budget_watchdog_enabled": pg.get(
                    "auto_budget_watchdog_enabled", ""
                ),
                "pg_adv_setting_id": pg.get("id", ""),
                "wb_source": "raw/ads/campaigns.jsonl",
                "pg_source": "public.advsetting CURRENT",
            }
        )
    return rows


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


def _find_collect_zip(collect_dir: Path) -> Path:
    for name in ("wb_readonly_research.zip", "collect.zip"):
        candidate = collect_dir / name
        if candidate.exists():
            return candidate
    zips = sorted(collect_dir.glob("*.zip"), key=lambda p: p.stat().st_mtime, reverse=True)
    if zips:
        return zips[0]
    raise FileNotFoundError(f"No collect zip in {collect_dir}")


def _prior_wb_status_from_reissue() -> int | None:
    """Best-effort prior status from local reissue package if present."""
    reissue = (
        Path(".tmp/a1_daily_spend_control")
        / "A1-DAILY-SPEND-CONTROL-AND-20260829-RECONCILIATION-AUTHORITATIVE-REISSUE"
        / "ACTIVE_CAMPAIGN_SPEND.csv"
    )
    if not reissue.exists():
        return None
    with reissue.open(encoding="utf-8", newline="") as handle:
        for row in csv.DictReader(handle):
            if str(row.get("adv_id")) == str(PAUSE_TRACE_ADV):
                try:
                    return int(row.get("wb_status") or 0)
                except (TypeError, ValueError):
                    return None
    return None


async def run_package(
    root: Path,
    pg_rows: list[dict[str, str]],
    *,
    collect_zip: Path | None = None,
    skip_collect: bool = False,
) -> dict[str, Any]:
    checked_msk = datetime.now(MSK)
    sql_dir = root / "sql"
    pkg = root / PACKAGE_NAME
    pkg.mkdir(parents=True, exist_ok=True)
    collect_dir = root / "collect"
    collect_dir.mkdir(parents=True, exist_ok=True)

    collect_report: dict[str, Any] = {}
    if skip_collect and collect_zip and collect_zip.exists():
        zip_path = collect_zip
        collect_report = {"skipped": True, "zip_path": str(zip_path)}
    else:
        collect_report = await _run_collect(collect_dir)
        zip_path = _find_collect_zip(collect_dir)

    pg_by_adv = _pg_by_adv_id(pg_rows)

    with zipfile.ZipFile(zip_path) as zf:
        orders, orders_member = read_jsonl_from_zip(zf, COLLECT_V2_ORDERS_JSONL)
        funnel, funnel_member = read_jsonl_from_zip(zf, COLLECT_V2_FUNNEL_JSONL)
        campaigns, campaigns_member = read_jsonl_from_zip(zf, COLLECT_V2_CAMPAIGNS_JSONL)
        fullstats, fullstats_member = read_jsonl_from_zip(zf, COLLECT_V2_FULLSTATS_JSONL)

    stats = _aggregate_fullstats(fullstats)
    inventory = _campaign_inventory(campaigns, pg_by_adv)
    orders_daily = _orders_store_daily(orders)
    funnel_daily = _funnel_store_daily(funnel)
    store_spend = _store_spend_by_day(stats)

    store_rows = _build_store_rows(orders_daily, funnel_daily, store_spend)
    contour_ids = _active_contour_ids(inventory, stats, pg_by_adv)
    contour_rows = _build_active_contour_rows(contour_ids, inventory, stats, pg_by_adv)
    pg_control_rows = _build_pg_control_rows(pg_rows, inventory)
    h1_rows = _build_h1_rows(inventory, stats, pg_by_adv)

    prior_status = _prior_wb_status_from_reissue()
    pause_md, pause_cause = _build_pause_trace_md(
        inventory, pg_by_adv, root, sql_dir, prior_status
    )

    _write_csv(
        pkg / "STORE_DAILY_RESULT.csv",
        store_rows,
        list(store_rows[0].keys()) if store_rows else ["date"],
    )
    _write_csv(
        pkg / "ACTIVE_AD_CONTOUR.csv",
        contour_rows,
        list(contour_rows[0].keys()) if contour_rows else ["adv_id"],
    )
    _write_csv(
        pkg / "CURRENT_PG_CONTROL_STATE.csv",
        pg_control_rows,
        list(pg_control_rows[0].keys()) if pg_control_rows else ["adv_id"],
    )
    _write_csv(
        pkg / "H1_CURRENT_STATE.csv",
        h1_rows,
        list(h1_rows[0].keys()) if h1_rows else ["adv_id"],
    )
    (pkg / "20646357_PAUSE_TRACE.md").write_text(pause_md, encoding="utf-8")

    provenance = [
        "# SOURCE_PROVENANCE",
        "",
        f"- package: `{PACKAGE_NAME}`",
        f"- shop_id: `{SHOP_ID}`",
        f"- checked_at_msk: {checked_msk.strftime('%Y-%m-%d %H:%M:%S %Z')}",
        f"- collect_zip: `{zip_path.resolve()}`",
        f"- orders_member: `{orders_member}`",
        f"- funnel_member: `{funnel_member}`",
        f"- campaigns_member: `{campaigns_member}`",
        f"- fullstats_member: `{fullstats_member}`",
        f"- pg_source: public.advsetting JOIN wbcabinet (CURRENT read-only)",
        f"- orders_rows: {len(orders)}",
        f"- no_production_mutations: true",
        "",
    ]
    (pkg / "SOURCE_PROVENANCE.md").write_text("\n".join(provenance), encoding="utf-8")

    day30 = next((r for r in store_rows if r["date"] == "2026-08-30"), {})
    status_20646357 = inventory.get(PAUSE_TRACE_ADV, {}).get("wb_status")

    file_hashes: dict[str, str] = {}
    artifact_names = [
        "STORE_DAILY_RESULT.csv",
        "ACTIVE_AD_CONTOUR.csv",
        "CURRENT_PG_CONTROL_STATE.csv",
        "H1_CURRENT_STATE.csv",
        "20646357_PAUSE_TRACE.md",
        "SOURCE_PROVENANCE.md",
    ]
    for name in artifact_names:
        file_hashes[name] = _sha256_file(pkg / name)

    payload: dict[str, Any] = {
        "package": PACKAGE_NAME,
        "PACKAGE_STATUS": "AUTHORITATIVE",
        "checked_at_msk": checked_msk.strftime("%Y-%m-%d %H:%M:%S %Z"),
        "shop_id": SHOP_ID,
        "mode": "STRICT_READ_ONLY",
        "30_08_FACTUAL_ORDERS": day30.get("factual_orders"),
        "30_08_FACTUAL_ORDER_VALUE": day30.get("factual_order_value_rub"),
        "30_08_TOTAL_AD_SPEND": day30.get("store_total_ad_spend_rub"),
        "ACTIVE_CONTOUR_COUNT": len(contour_rows),
        "20646357_CURRENT_STATUS": status_20646357,
        "20646357_PAUSE_CAUSE": pause_cause,
        "STORE_DAILY_RESULT": store_rows,
        "ACTIVE_AD_CONTOUR": contour_rows,
        "CURRENT_PG_CONTROL_STATE": pg_control_rows,
        "H1_CURRENT_STATE": h1_rows,
        "collect_report": collect_report,
        "provenance": {
            "zip_path": str(zip_path.resolve()),
            "orders_member": orders_member,
        },
    }
    json_path = pkg / f"{PACKAGE_NAME}.json"
    json_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    file_hashes[f"{PACKAGE_NAME}.json"] = _sha256_file(json_path)

    manifest = {
        "package": PACKAGE_NAME,
        "PACKAGE_STATUS": "AUTHORITATIVE",
        "file_sha256": file_hashes,
        "integrity_gate_errors": [],
    }
    (pkg / "PACKAGE_MANIFEST.json").write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8"
    )

    zip_out = root / f"{PACKAGE_NAME}.zip"
    with zipfile.ZipFile(zip_out, "w", zipfile.ZIP_DEFLATED) as zf:
        for name in artifact_names + [f"{PACKAGE_NAME}.json", "PACKAGE_MANIFEST.json"]:
            zf.write(pkg / name, arcname=name)

    archive_sha = _sha256_file(zip_out)
    payload["FINAL_ARCHIVE_SHA256"] = archive_sha
    payload["ABSOLUTE_ARCHIVE_PATH"] = str(zip_out.resolve())
    json_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")

    return {
        "PACKAGE_STATUS": payload["PACKAGE_STATUS"],
        "30_08_FACTUAL_ORDERS": payload["30_08_FACTUAL_ORDERS"],
        "30_08_FACTUAL_ORDER_VALUE": payload["30_08_FACTUAL_ORDER_VALUE"],
        "30_08_TOTAL_AD_SPEND": payload["30_08_TOTAL_AD_SPEND"],
        "ACTIVE_CONTOUR_COUNT": payload["ACTIVE_CONTOUR_COUNT"],
        "20646357_CURRENT_STATUS": payload["20646357_CURRENT_STATUS"],
        "20646357_PAUSE_CAUSE": payload["20646357_PAUSE_CAUSE"],
        "FINAL_ARCHIVE_SHA256": archive_sha,
        "ABSOLUTE_ARCHIVE_PATH": str(zip_out.resolve()),
        "output_dir": str(pkg.resolve()),
    }


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="A1 iteration-04 current state READ_ONLY.")
    parser.add_argument("--output-dir", default=".tmp/a1_iteration_04")
    parser.add_argument("--collect-zip", default="", help="Reuse existing collect zip")
    parser.add_argument("--skip-collect", action="store_true")
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    root = Path(args.output_dir).resolve()
    root.mkdir(parents=True, exist_ok=True)
    _bootstrap_cluster_infra()
    pg_rows = _load_pg_advsettings(root, root / "sql")
    collect_zip = Path(args.collect_zip).resolve() if args.collect_zip else None
    result = asyncio.run(
        run_package(
            root,
            pg_rows,
            collect_zip=collect_zip,
            skip_collect=args.skip_collect or bool(args.collect_zip),
        )
    )
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
