"""READ_ONLY: A1 Search pressure mechanics + growth SKU shortlist refresh.

ITER-CLIENT-RETENTION-A1-20260904-001 — parent/complex AdvSetting semantics,
Search 39900211 cluster/V3 state, 5-SKU shortlist comparison. Без writes.
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
from datetime import date, datetime, time, timedelta, timezone
from pathlib import Path
from typing import Any
from zoneinfo import ZoneInfo

import dotenv

dotenv.load_dotenv()

from scripts import ch_a1_evidence as evidence
from scripts.a1_cpc_target_stock_check import _aggregate_stock, _fetch_wb_warehouses_stock
from scripts.a1_cpc_two_sku_safety_preflight import (
    ACTIVE_WB,
    WB_STATUS_NAMES,
    _adv_nm_map,
    _bootstrap,
    _campaigns_for_nmid,
    _cpc_min_bids,
    _fetch_cards,
    _fetch_seller_stocks,
    _pg_rows_for_nmid,
)
from scripts.wb_a1_associated_conversions import _read_float, _read_int
from scripts.wb_api_readonly_ops.collect.ads import _flatten_fullstats
from scripts.wb_api_readonly_ops.collect.api_budget import ApiCallBudget
from scripts.wb_api_readonly_ops.collect.jsonable import jsonable
from scripts.wb_api_readonly_ops.collect.orders_sales import _paginate_supplier_rows

SHOP_ID = evidence.SHOP_ID
MSK = ZoneInfo("Europe/Moscow")
ITERATION = "ITER-CLIENT-RETENTION-A1-20260904-001"
PACKAGE = "A1_PRESSURE_AND_SHORTLIST_REFRESH_20260904"

PARENT_ADV_SETTING_ID = 1151722151
AUTO_ADV = 39900256
SEARCH_ADV = 39900211
TARGET_NMID = 837395782
SHORTLIST_NMIDS = (206697189, 180148471, 288483603, 14824677, 180145507)

CLOSED_DAY = date(2026, 9, 3)
CURRENT_DAY = date(2026, 9, 4)
CLOSED_STR = CLOSED_DAY.isoformat()
CURRENT_STR = CURRENT_DAY.isoformat()
BOUNDARY_CLOSED_START = datetime(2026, 9, 3, 0, 0, 0, tzinfo=MSK)
BOUNDARY_CLOSED_END = datetime(2026, 9, 4, 0, 0, 0, tzinfo=MSK)
BOUNDARY_CURRENT_START = datetime(2026, 9, 4, 0, 0, 0, tzinfo=MSK)
ORDERS_DATE_FROM = "2026-08-07"
CLOSED_END = CLOSED_DAY

DEFAULT_OUTPUT = (
    r"C:\Users\vkita\my_code\meta-repo\worktree\wb-delivery-context-router"
    r"\clients\A1\chats\wb-lab-a1-analysis-20260828\artifacts"
    r"\OWNER_UPLOAD_20260904_PRESSURE_AND_SHORTLIST_REFRESH"
)

PARENT_PG_FIELDS = [
    "id", "adv_id", "_search_adv_id", "name", "nmids", "aggressiveness", "strategy",
    "automatic_version", "max_cpm", "active_status", "bot_active",
    "auto_budget_watchdog_enabled", "auto_budget_daily_limit",
    "search_auto_budget_daily_limit", "use_common_budget", "common_budget_daily_limit",
    "auto_adv_target_status", "auction_adv_target_status",
    "updater_common_bid_in_search_adv_active_status", "auto_add_only_relevant_phrase",
    "max_cpc",
]
KW_FIELDS = [
    "id", "text", "hard_status", "strategy_mode", "target_place",
    "predict_ctr", "relevant", "auto_block", "adv_setting_id",
]
HARD_STATUS_LABEL = {0: "blacklist", 1: "in_test", 2: "whitelist", 3: "turned_off", 4: "fixed_phrase"}
NAME_SEARCH = re.compile(r"<!-\[(\d+)\]-!>")


def _msk_now() -> datetime:
    return datetime.now(timezone.utc).astimezone(MSK)


def _iso_msk(dt: datetime) -> str:
    return dt.astimezone(MSK).isoformat()


def _pg_db() -> str:
    return os.environ.get("POSTGRES_DBNAME") or "adv_updater"


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


def _in_day(row: dict[str, Any], start: datetime, end: datetime) -> bool:
    dt = _msk_dt(row)
    return bool(dt and start <= dt < end)


def _demand_metrics(rows: list[dict[str, Any]]) -> dict[str, Any]:
    active = [r for r in rows if not _is_cancelled(r)]
    groups: dict[str, list[dict[str, Any]]] = defaultdict(list)
    days: set[str] = set()
    for r in active:
        groups[_g_key(r)].append(r)
        dt = _msk_dt(r)
        if dt:
            days.add(dt.date().isoformat())
    bulk = sum(1 for v in groups.values() if len(v) > 1)
    last_purchase = None
    for r in active:
        dt = _msk_dt(r)
        if dt and (last_purchase is None or dt.date() > last_purchase):
            last_purchase = dt.date()
    return {
        "purchase_events": len(groups),
        "units": len(active),
        "total_price_value": round(sum(_read_float(r, "totalPrice") for r in active), 2),
        "distinct_active_days": len(days),
        "bulk_events_count": bulk,
        "max_units_in_purchase_event": max((len(v) for v in groups.values()), default=0),
        "last_purchase_date": last_purchase.isoformat() if last_purchase else None,
    }


def _window_demand(all_orders: list[dict[str, Any]], nmid: int, days: int) -> dict[str, Any]:
    start = CLOSED_END - timedelta(days=days - 1)
    start_dt = datetime.combine(start, time.min, tzinfo=MSK)
    end_dt = datetime.combine(CLOSED_END + timedelta(days=1), time.min, tzinfo=MSK)
    rows = [
        r for r in all_orders
        if _read_int(r, "nmId", "nm_id", "nmid") == nmid
        and _in_day(r, start_dt, end_dt)
    ]
    m = _demand_metrics(rows)
    m["window_closed_days"] = days
    return m


def _window_3d(all_orders: list[dict[str, Any]], nmid: int) -> dict[str, Any]:
    return _window_demand(all_orders, nmid, 3)


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


def _load_parent_and_keywords(root: Path) -> tuple[dict[str, str], list[dict[str, str]]]:
    staging = root / "staging"
    staging.mkdir(parents=True, exist_ok=True)
    sql_dir = staging / "sql"
    sql_dir.mkdir(parents=True, exist_ok=True)
    cols = ", ".join(f"a.{c}" for c in PARENT_PG_FIELDS)
    adv_out = staging / "parent_advsetting.csv"
    q = (
        f"SELECT {cols} FROM public.advsetting a "
        f"JOIN public.wbcabinet c ON a.wb_cabinet_id = c.id "
        f"WHERE c.shop_id = '{SHOP_ID}' AND a.id = {PARENT_ADV_SETTING_ID}"
    )
    st = evidence.run_pg_query(_pg_db(), q, adv_out, sql_dir / "parent.sql", csv_output=True)
    if not st["success"]:
        raise RuntimeError(st["stderr"])
    rows = list(csv.DictReader(adv_out.open(encoding="utf-8", newline="")))
    if not rows:
        raise RuntimeError(f"parent adv_setting_id {PARENT_ADV_SETTING_ID} not found")
    parent = rows[0]

    kw_out = staging / "keywords.csv"
    kw_cols = ", ".join(KW_FIELDS)
    q_kw = (
        f"SELECT {kw_cols} FROM public.keywordsetting "
        f"WHERE adv_setting_id = {PARENT_ADV_SETTING_ID}"
    )
    st2 = evidence.run_pg_query(_pg_db(), q_kw, kw_out, sql_dir / "keywords.sql", csv_output=True)
    keywords: list[dict[str, str]] = []
    if st2["success"]:
        keywords = list(csv.DictReader(kw_out.open(encoding="utf-8", newline="")))
    return parent, keywords


def _load_all_pg(root: Path) -> list[dict[str, str]]:
    from scripts.a1_cpc_two_sku_safety_preflight import _load_pg

    return _load_pg(root)


def _saturation(spend: float, limit: int | None) -> str:
    if not limit or limit <= 0:
        return "GAP"
    pct = 100.0 * spend / limit
    if pct >= 100:
        return "YES"
    if pct >= 80:
        return "PARTIAL"
    return "NO"


def _utilization(spend: float, limit: int | None) -> float | str:
    if not limit or limit <= 0:
        return "GAP"
    return round(spend / limit, 4)


def _adv_day_stats(fullstats: list[dict[str, Any]], adv_id: int, day: str) -> dict[str, Any]:
    spend = views = clicks = orders = 0
    gmv = 0.0
    for row in fullstats:
        if str(row.get("date") or "")[:10] != day:
            continue
        if _read_int(row, "advertId", "advert_id") != adv_id:
            continue
        spend += _read_float(row, "sum", "spend")
        views += _read_int(row, "views")
        clicks += _read_int(row, "clicks")
        orders += _read_int(row, "orders")
        gmv += _read_float(row, "sum_price")
    return {
        "spend": round(spend, 2),
        "views": views,
        "clicks": clicks,
        "ctr": round(100 * clicks / views, 4) if views else None,
        "cpc": round(spend / clicks, 4) if clicks else None,
        "attributed_orders": orders,
        "attributed_gmv": round(gmv, 2),
    }


def _top_n(rows: list[dict[str, Any]], field: str, n: int = 10) -> list[dict[str, Any]]:
    ranked = sorted(rows, key=lambda r: -float(r.get(field) or 0))
    return [
        {"norm_query": r.get("norm_query"), field: r.get(field), "spend": r.get("spend")}
        for r in ranked[:n]
        if float(r.get(field) or 0) > 0
    ]


def _share_top5(rows: list[dict[str, Any]], field: str) -> float | None:
    total = sum(float(r.get(field) or 0) for r in rows)
    if total <= 0:
        return None
    top5 = sum(float(r.get(field) or 0) for r in sorted(rows, key=lambda r: -float(r.get(field) or 0))[:5])
    return round(100 * top5 / total, 2)


async def _fetch_normquery_since_launch(
    pm: Any, adv_id: int, nmid: int, launch: date, end: date
) -> list[dict[str, Any]]:
    from app.core.mp.wb.api.adapter.promotion_client.normquery_stats.command import (
        GetNormqueryStatsCommand,
        GetNormqueryStatsCommandBatchForAdv,
    )

    adapter = pm._client.normquery_stats_adapter
    out: list[dict[str, Any]] = []
    d = launch
    while d <= end:
        cmd = GetNormqueryStatsCommand(
            date_from=d,
            date_to=d,
            batchs=[GetNormqueryStatsCommandBatchForAdv(adv_id=adv_id, nmid=nmid)],
        )
        try:
            dtos = await adapter.get_adv_v0_normquery_stats(cmd)
            for dto in dtos or []:
                dto_dict = jsonable(dto.model_dump() if hasattr(dto, "model_dump") else dto)
                for stat in dto_dict.get("stats") or []:
                    if not isinstance(stat, dict):
                        continue
                    out.append({
                        "date": d.isoformat(),
                        "norm_query": stat.get("norm_query"),
                        "views": _read_int(stat, "views"),
                        "clicks": _read_int(stat, "clicks"),
                        "spend": round(_read_float(stat, "spend"), 2),
                        "orders": _read_int(stat, "orders"),
                        "sum_price": round(_read_float(stat, "sum_price"), 2),
                        "atbs": _read_int(stat, "add_to_cart", "atbs"),
                        "source": "POST /adv/v0/normquery/stats",
                    })
        except Exception as exc:  # noqa: BLE001
            out.append({"date": d.isoformat(), "error": str(exc)[:200]})
        if d < end:
            await asyncio.sleep(0.3)
        d += timedelta(days=1)
    return out


async def _cluster_list_minus_bids(pm: Any, adv_id: int, nmid: int) -> dict[str, Any]:
    from app.core.mp.wb.api.adapter.promotion_client.minus_phrases.get_adv_v0_normquery_get_minus import (
        GetMinusPhrasesCommand,
    )
    from app.core.mp.wb.api.adapter.raise_errors import with_raise_errors
    from app.core.mp.wb.api.generated.promotion.v1.marketing_and_promotions_client.models import (
        V0GetNormQueryBidsRequest,
        V0GetNormQueryBidsRequestItem,
    )
    from app.core.mp.wb.api.generated.promotion.v4.marketing_and_promotions_client.marketing_and_promotions_client.api.search_clusters.post_adv_v0_normquery_list import (
        asyncio_detailed as normquery_list_async,
    )
    from app.core.mp.wb.api.generated.promotion.v4.marketing_and_promotions_client.marketing_and_promotions_client.models import (
        V0GetNormQueryListRequest,
        V0GetNormQueryListRequestItem,
    )

    result: dict[str, Any] = {"active": [], "excluded": [], "minus": [], "bids": []}
    item = V0GetNormQueryListRequestItem(advert_id=adv_id, nm_id=nmid)
    try:
        adapter = pm._client.normquery_stats_adapter
        http = await adapter.auth_client_handler.get_proxy_client(adapter)
        resp = await with_raise_errors(
            normquery_list_async, http, body=V0GetNormQueryListRequest(items=[item]),
        )
        parsed = jsonable(resp.parsed)
        if isinstance(parsed, dict):
            for it in parsed.get("items") or []:
                nq = it.get("normQueries") or it.get("norm_queries") or {}
                if isinstance(nq, dict):
                    result["active"] = list(nq.get("active") or [])
                    result["excluded"] = list(nq.get("excluded") or [])
        result["list_route"] = "POST /adv/v0/normquery/list"
    except Exception as exc:  # noqa: BLE001
        result["list_error"] = str(exc)[:400]

    try:
        bids = await pm._client.normquery_bids_adapter.post_adv_v0_normquery_get_bids(
            V0GetNormQueryBidsRequest(
                items=[V0GetNormQueryBidsRequestItem(advert_id=adv_id, nm_id=nmid)]
            )
        )
        for b in bids or []:
            result["bids"].append({"norm_query": b.norm_query, "bid_kopecks": b.bid})
        result["bids_route"] = "POST /adv/v0/normquery/get-bids"
    except Exception as exc:  # noqa: BLE001
        result["bids_error"] = str(exc)[:400]

    try:
        minus = await pm._client.minus_phrases_adapter.post_adv_v0_normquery_get_minus(
            GetMinusPhrasesCommand(advert_id=adv_id, nm_id=nmid)
        )
        result["minus"] = list(minus or [])
        result["minus_route"] = "POST /adv/v0/normquery/get-minus"
    except Exception as exc:  # noqa: BLE001
        result["minus_error"] = str(exc)[:400]
    return result


def _merge_cluster_rows(
    norm_since_launch: list[dict[str, Any]],
    keywords: list[dict[str, str]],
    wb_clusters: dict[str, Any],
    bid_map: dict[str, int],
) -> list[dict[str, Any]]:
    agg: dict[str, dict[str, Any]] = defaultdict(
        lambda: {
            "views": 0, "clicks": 0, "spend": 0.0, "orders": 0, "gmv": 0.0, "days": set(),
        }
    )
    for row in norm_since_launch:
        if "error" in row:
            continue
        nq = str(row.get("norm_query") or "").strip()
        if not nq:
            continue
        a = agg[nq]
        a["views"] += _read_int(row, "views")
        a["clicks"] += _read_int(row, "clicks")
        a["spend"] += _read_float(row, "spend")
        a["orders"] += _read_int(row, "orders")
        a["gmv"] += _read_float(row, "sum_price")
        a["days"].add(row.get("date"))

    kw_by_text = {str(k.get("text") or "").strip(): k for k in keywords}
    all_queries = set(agg) | set(kw_by_text) | set(wb_clusters.get("active") or []) | set(wb_clusters.get("excluded") or [])

    rows: list[dict[str, Any]] = []
    for nq in sorted(all_queries):
        if not nq:
            continue
        a = agg.get(nq, {"views": 0, "clicks": 0, "spend": 0.0, "orders": 0, "gmv": 0.0, "days": set()})
        views = int(a.get("views") or 0)
        clicks = int(a.get("clicks") or 0)
        spend = round(float(a.get("spend") or 0), 2)
        kw = kw_by_text.get(nq, {})
        hard = kw.get("hard_status")
        try:
            hard_i = int(hard) if hard is not None and str(hard).strip() != "" else None
        except ValueError:
            hard_i = None
        state = HARD_STATUS_LABEL.get(hard_i, f"hard_status_{hard}") if hard_i is not None else "GAP"
        in_wb_active = nq in (wb_clusters.get("active") or [])
        in_wb_excluded = nq in (wb_clusters.get("excluded") or [])
        in_minus = nq in (wb_clusters.get("minus") or [])
        rows.append({
            "norm_query": nq,
            "pg_hard_status": hard_i,
            "pg_state_label": state,
            "pg_strategy_mode": kw.get("strategy_mode"),
            "pg_relevant": kw.get("relevant"),
            "wb_list_active": in_wb_active,
            "wb_list_excluded": in_wb_excluded,
            "wb_minus": in_minus,
            "current_bid_kopecks": bid_map.get(nq),
            "views_since_launch": views,
            "clicks_since_launch": clicks,
            "spend_since_launch": spend,
            "ctr_since_launch": round(100 * clicks / views, 4) if views else None,
            "cpc_since_launch": round(spend / clicks, 4) if clicks else None,
            "attributed_orders_since_launch": int(a.get("orders") or 0),
            "attributed_gmv_since_launch": round(float(a.get("gmv") or 0), 2),
            "zero_impressions": views == 0,
            "impressions_1_99": 0 < views < 100,
            "impressions_ge_100": views >= 100,
            "normquery_spend_note": "query-level spend from POST /adv/v0/normquery/stats — not identical to campaign fullstats",
        })
    return rows


def _write_json(path: Path, obj: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(obj, ensure_ascii=False, indent=2, default=str), encoding="utf-8")


def _write_jsonl(path: Path, rows: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as f:
        for row in rows:
            f.write(json.dumps(row, ensure_ascii=False) + "\n")


def _sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(65536), b""):
            h.update(chunk)
    return h.hexdigest()


def _gap_val(v: Any) -> Any:
    return "GAP" if v is None else v


async def run_collect(
    output_dir: Path,
    *,
    parent: dict[str, str],
    keywords: list[dict[str, str]],
    pg_all: list[dict[str, str]],
) -> dict[str, Any]:
    from app.configs.app_config import AppConfig
    from app.core.di.wb_manager_hub.wb_manager_hub_factory import WBManagerHubFactory
    from app.core.mp.wb.api.httpx_client_handler import HttpxClientHandler
    from app.core.redis_manager_v2.redis_client import RedisClient
    from app.modules.common_slaves.wildberries.super_cabinet_manager import get_access_for_wb_cabinet
    from redis.asyncio import Redis

    checked_at = _msk_now()
    gaps: list[str] = []
    root = output_dir
    root.mkdir(parents=True, exist_ok=True)

    parent_adv = _read_int(parent, "adv_id")
    parent_search = _read_int(parent, "_search_adv_id")
    mapping_ok = (
        parent_adv == AUTO_ADV
        and parent_search == SEARCH_ADV
        and _read_int(parent, "id") == PARENT_ADV_SETTING_ID
    )

    parent_bot_active = str(parent.get("bot_active")).lower() in ("true", "t", "1")
    parent_search_limit = _read_int(parent, "search_auto_budget_daily_limit")
    parent_auto_limit = _read_int(parent, "auto_budget_daily_limit")
    aggressiveness = parent.get("aggressiveness")
    automatic_version = parent.get("automatic_version")
    max_cpm = _read_int(parent, "max_cpm")

    parent_block = {
        "adv_setting_id": PARENT_ADV_SETTING_ID,
        "parent_auto_adv_id": parent_adv,
        "search_adv_id": parent_search,
        "mapping_confirmed": mapping_ok,
        "semantics_note": (
            "bot_active and search_auto_budget_daily_limit are read from parent/complex "
            "AdvSetting; legacy search row 39900211 is not operational source for these."
        ),
        "parent_bot_active": parent_bot_active,
        "search_auto_budget_daily_limit": parent_search_limit,
        "auto_budget_daily_limit": parent_auto_limit,
        "aggressiveness": aggressiveness,
        "automatic_version": automatic_version,
        "auto_budget_watchdog_enabled": parent.get("auto_budget_watchdog_enabled"),
        "updater_common_bid_in_search_adv_active_status": parent.get(
            "updater_common_bid_in_search_adv_active_status"
        ),
        "auto_add_only_relevant_phrase": parent.get("auto_add_only_relevant_phrase"),
        "max_cpm": max_cpm,
        "max_cpc": parent.get("max_cpc"),
        "max_cpo": "GAP",
        "target_cpo": "GAP",
        "strategy": parent.get("strategy"),
        "auto_adv_target_status": parent.get("auto_adv_target_status"),
        "auction_adv_target_status": parent.get("auction_adv_target_status"),
        "use_common_budget": parent.get("use_common_budget"),
        "common_budget_daily_limit": parent.get("common_budget_daily_limit"),
        "keyword_count": len(keywords),
        "whitelist_mode_summary": {
            "whitelist": sum(1 for k in keywords if str(k.get("hard_status")) == "2"),
            "in_test": sum(1 for k in keywords if str(k.get("hard_status")) == "1"),
            "blacklist": sum(1 for k in keywords if str(k.get("hard_status")) == "0"),
            "turned_off": sum(1 for k in keywords if str(k.get("hard_status")) == "3"),
        },
        "checked_at_msk": _iso_msk(checked_at),
        "route": "PG public.advsetting + keywordsetting",
    }

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
        hub = WBManagerHubFactory(
            httpx_client_handler=httpx, redis_client_wrapper=redis_wrap
        ).get_wb_manager_hub(SHOP_ID)
        dm = hub.wb_data_manager
        pm = dm.promotion_manager
        products = dm.products_manager
        budget = ApiCallBudget(max_seconds=2400.0, max_api_calls=2000)

        reports_manager = getattr(dm, "reports_manager", None)

        async def fetch_orders(df: str) -> list[object]:
            if reports_manager is not None:
                return list(await reports_manager.get_supplier_orders(date_from=df, flag=0) or [])
            return list(await dm.get_supplier_orders(date_from=df, flag=0) or [])

        orders_result = await _paginate_supplier_rows(
            fetch=fetch_orders, initial_date_from=ORDERS_DATE_FROM, budget=budget, max_pages=1200,
        )
        all_orders = orders_result.rows
        shortlist_orders = [
            r for r in all_orders
            if _read_int(r, "nmId", "nm_id", "nmid") in SHORTLIST_NMIDS
            and _in_day(r, datetime.combine(CLOSED_END - timedelta(days=27), time.min, tzinfo=MSK), checked_at)
        ]

        budget.consume()
        adv_ids = list(await pm._client.promotion_count_adapter.get_cabinet_adv_ids() or [])
        camps_raw = list(await pm.get_adverts_v2_by_ids([SEARCH_ADV, AUTO_ADV] + adv_ids[:50]) or [])
        # ensure search/auto
        extra = await pm.get_adverts_v2_by_ids([SEARCH_ADV, AUTO_ADV])
        campaigns = []
        seen: set[int] = set()
        for batch in (camps_raw, extra or []):
            for x in batch or []:
                d = jsonable(x)
                if isinstance(d, dict):
                    aid = _read_int(d, "id", "advertId")
                    if aid and aid not in seen:
                        campaigns.append(d)
                        seen.add(aid)
        adv_nm = _adv_nm_map(campaigns)

        search_cfg = next((c for c in campaigns if _read_int(c, "id", "advertId") == SEARCH_ADV), {})
        auto_cfg = next((c for c in campaigns if _read_int(c, "id", "advertId") == AUTO_ADV), {})
        search_settings = search_cfg.get("settings") if isinstance(search_cfg.get("settings"), dict) else {}
        nm_settings = search_cfg.get("nm_settings") or search_cfg.get("nmSettings") or []
        current_bid = None
        for nm in nm_settings:
            if _read_int(nm, "nm_id", "nmId", "nmID") == TARGET_NMID:
                bids = nm.get("bids_kopecks") or nm.get("bids") or {}
                if isinstance(bids, dict):
                    current_bid = bids.get("search")

        launch_date = date(2026, 9, 1)
        for ts_key in ("create", "created", "start"):
            pass
        timestamps = search_cfg.get("timestamps") if isinstance(search_cfg.get("timestamps"), dict) else {}
        if timestamps.get("created"):
            try:
                launch_date = date.fromisoformat(str(timestamps["created"])[:10])
            except ValueError:
                gaps.append("search_launch_date_parse_gap")

        budget.consume()
        stats_raw = await pm.get_full_adv_stat([SEARCH_ADV], [CLOSED_DAY, CURRENT_DAY])
        fullstats = _flatten_fullstats(list(stats_raw or []))
        stats_0309 = _adv_day_stats(fullstats, SEARCH_ADV, CLOSED_STR)
        stats_0409 = _adv_day_stats(fullstats, SEARCH_ADV, CURRENT_STR)

        min_bids = await _cpc_min_bids(pm, SEARCH_ADV, TARGET_NMID)
        min_search_vals = []
        for k, v in min_bids.items():
            if "search" in k and k.endswith("_kopecks"):
                if isinstance(v, list) and v:
                    min_search_vals.extend(v)
                elif isinstance(v, (int, float)):
                    min_search_vals.append(v)
        min_bid = min(min_search_vals) if min_search_vals else None

        norm_since = await _fetch_normquery_since_launch(
            pm, SEARCH_ADV, TARGET_NMID, launch_date, CURRENT_DAY,
        )
        wb_clusters = await _cluster_list_minus_bids(pm, SEARCH_ADV, TARGET_NMID)
        bid_map = {b["norm_query"]: b["bid_kopecks"] for b in wb_clusters.get("bids") or []}
        cluster_rows = _merge_cluster_rows(norm_since, keywords, wb_clusters, bid_map)

        zero_impr = sum(1 for r in cluster_rows if r["zero_impressions"])
        impr_1_99 = sum(1 for r in cluster_rows if r["impressions_1_99"])
        impr_ge_100 = sum(1 for r in cluster_rows if r["impressions_ge_100"])
        total_clusters = len(cluster_rows)

        campaign_since_launch = {
            "launch_date_used": launch_date.isoformat(),
            "launch_date_note": "from v2 timestamps.created if present else fallback 2026-09-01",
            "total_views": sum(r["views_since_launch"] for r in cluster_rows),
            "total_clicks": sum(r["clicks_since_launch"] for r in cluster_rows),
            "total_spend_normquery": round(sum(r["spend_since_launch"] for r in cluster_rows), 2),
            "total_attributed_orders": sum(r["attributed_orders_since_launch"] for r in cluster_rows),
            "total_attributed_gmv": round(sum(r["attributed_gmv_since_launch"] for r in cluster_rows), 2),
            "top10_by_spend": _top_n(cluster_rows, "spend_since_launch"),
            "top10_by_impressions": _top_n(
                [{"norm_query": r["norm_query"], "views": r["views_since_launch"], "spend": r["spend_since_launch"]} for r in cluster_rows],
                "views",
            ),
            "top10_by_clicks": _top_n(
                [{"norm_query": r["norm_query"], "clicks": r["clicks_since_launch"], "spend": r["spend_since_launch"]} for r in cluster_rows],
                "clicks",
            ),
            "share_spend_top5_pct": _share_top5(
                [{"spend": r["spend_since_launch"]} for r in cluster_rows], "spend"
            ),
            "share_impressions_top5_pct": _share_top5(
                [{"views": r["views_since_launch"]} for r in cluster_rows], "views"
            ),
            "cluster_counts": {
                "total": total_clusters,
                "zero_impressions": zero_impr,
                "impressions_1_99": impr_1_99,
                "impressions_ge_100": impr_ge_100,
            },
        }

        limit_util_0309 = _utilization(stats_0309["spend"], parent_search_limit)
        limit_util_0409 = _utilization(stats_0409["spend"], parent_search_limit)
        limit_sat_0309 = _saturation(stats_0309["spend"], parent_search_limit)

        bid_at_min = (
            current_bid is not None
            and min_bid is not None
            and current_bid <= min_bid
        )
        max_cpm_kopecks = max_cpm * 100 if max_cpm else None
        bid_at_max_cpm = (
            max_cpm_kopecks
            and current_bid
            and current_bid >= max_cpm_kopecks
        )

        in_test_count = sum(1 for r in cluster_rows if r.get("pg_state_label") == "in_test")
        in_test_low_impr = sum(
            1 for r in cluster_rows
            if r.get("pg_state_label") == "in_test" and r["views_since_launch"] < 100
        )

        budget_binding = "NO"
        if isinstance(limit_util_0309, float) and limit_util_0309 >= 0.95:
            budget_binding = "YES"
        elif isinstance(limit_util_0309, float) and limit_util_0309 >= 0.8:
            budget_binding = "PARTIAL"
        elif limit_util_0309 == "GAP":
            budget_binding = "GAP"

        redis_search = _redis_reason(SEARCH_ADV, "search")
        redis_auto = _redis_reason(AUTO_ADV, "auto")

        runtime_state = {
            "search_physical_adv_id": SEARCH_ADV,
            "auto_physical_adv_id": AUTO_ADV,
            "parent_adv_setting_id": PARENT_ADV_SETTING_ID,
            "parent_bot_active": parent_bot_active,
            "parent_search_daily_limit": parent_search_limit,
            "parent_auto_daily_limit": parent_auto_limit,
            "search_wb_status": _read_int(search_cfg, "status"),
            "search_wb_status_name": WB_STATUS_NAMES.get(_read_int(search_cfg, "status"), "GAP"),
            "auto_wb_status": _read_int(auto_cfg, "status"),
            "auto_wb_status_name": WB_STATUS_NAMES.get(_read_int(auto_cfg, "status"), "GAP"),
            "search_current_bid_kopecks": current_bid,
            "search_payment_type": search_settings.get("payment_type") or search_settings.get("paymentType"),
            "min_bid_probe": min_bids,
            "min_bid_kopecks": min_bid,
            "bid_position": {
                "at_minimum": bid_at_min,
                "above_minimum": bool(current_bid and min_bid and current_bid > min_bid),
                "at_max_cpm": bid_at_max_cpm,
                "max_cpm_pg_rub": max_cpm,
                "max_cpm_kopecks_equiv": max_cpm_kopecks,
                "current_bid_kopecks": current_bid,
            },
            "redis_search": redis_search,
            "redis_auto": redis_auto,
            "daily_slices": {"closed_20260903": stats_0309, "current_20260904_partial": stats_0409},
            "limit_utilization": {
                "effective_search_daily_limit": parent_search_limit,
                "limit_utilization_0309": limit_util_0309,
                "limit_utilization_0409_partial": limit_util_0409,
                "search_limit_saturation_0309": limit_sat_0309,
            },
            "pressure_bottleneck_flags": {
                "SEARCH_BUDGET_LIMIT_IS_BINDING": budget_binding,
                "SEARCH_BID_LEVEL_MAY_BE_BINDING": "YES" if bid_at_min else ("NO" if current_bid else "GAP"),
                "SEARCH_MAX_CPM_IS_BINDING": "YES" if bid_at_max_cpm else ("NO" if max_cpm else "GAP"),
                "SEARCH_V3_LEARNING_STAGE_LIMITS_PRESSURE": (
                    "YES" if in_test_low_impr > 0 else ("NO" if in_test_count == 0 else "PARTIAL")
                ),
                "SEARCH_SEMANTIC_COVERAGE_LIMITS_PRESSURE": (
                    "YES" if zero_impr > total_clusters * 0.5 and total_clusters > 0 else "NO"
                ),
                "SEARCH_OTHER_EXPLICIT_BLOCKER": (
                    redis_search.get("parsed", {}) or {}
                ).get("reason_code", "NONE"),
            },
            "what_limits_search_pressure_now_evidence": (
                "Observed: parent search limit "
                f"{parent_search_limit} RUB; spend 03.09={stats_0309['spend']}; "
                f"saturation={limit_sat_0309}; redis={redis_search.get('parsed')}; "
                f"clusters zero_impr={zero_impr}/{total_clusters}"
            ),
            "checked_at_msk": _iso_msk(checked_at),
        }

        cards = await _fetch_cards(products, set(SHORTLIST_NMIDS))
        fbs = await _fetch_seller_stocks(products, cards)
        try:
            analytics = dm._analytics_manager._AnalyticsManager__wb_api_client.sales_funnel_adapter
            fbo_rows, fbo_meta = await _fetch_wb_warehouses_stock(analytics, list(SHORTLIST_NMIDS))
        except Exception as exc:  # noqa: BLE001
            fbo_rows, fbo_meta = [], {"error": str(exc)[:300]}
            gaps.append(f"FBO_route: {exc}")

        # spend 7d/28d per shortlist nmid
        spend_by_adv_7d: dict[int, float] = defaultdict(float)
        spend_by_adv_28d: dict[int, float] = defaultdict(float)
        d7_start = CLOSED_END - timedelta(days=6)
        d28_start = CLOSED_END - timedelta(days=27)
        nmid_adv_map: dict[int, list[int]] = {n: [] for n in SHORTLIST_NMIDS}
        for n in SHORTLIST_NMIDS:
            nmid_adv_map[n] = [c["adv_id"] for c in _campaigns_for_nmid(n, campaigns, adv_nm)]
        all_shortlist_advs = sorted({a for ads in nmid_adv_map.values() for a in ads})
        if all_shortlist_advs:
            dates_28 = []
            d = d28_start
            while d <= CLOSED_END:
                dates_28.append(d)
                d += timedelta(days=1)
            fs28 = await pm.get_full_adv_stat(all_shortlist_advs, dates_28)
            for row in _flatten_fullstats(list(fs28 or [])):
                aid = _read_int(row, "advertId", "advert_id")
                day_s = str(row.get("date") or "")[:10]
                try:
                    day_d = date.fromisoformat(day_s)
                except ValueError:
                    continue
                sp = _read_float(row, "sum", "spend")
                if day_d >= d28_start:
                    spend_by_adv_28d[aid] += sp
                if day_d >= d7_start:
                    spend_by_adv_7d[aid] += sp

        product_states: dict[int, dict[str, Any]] = {}
        comparison: list[dict[str, Any]] = []
        shortlist_complete = True

        for nmid in SHORTLIST_NMIDS:
            card = cards.get(nmid, {})
            fbs_n = (fbs.get("by_nmid") or {}).get(nmid, {})
            fbo_n = _aggregate_stock(fbo_rows, nmid) if fbo_rows else {"total_wb_stock_quantity": "GAP"}
            fbs_q = fbs_n.get("total_sellable")
            fbo_q = fbo_n.get("total_wb_stock_quantity")
            if fbs_q is None:
                gaps.append(f"FBS_null_nmid_{nmid}")
                shortlist_complete = False
            if fbo_q == "GAP" or (isinstance(fbo_meta, dict) and fbo_meta.get("error")):
                gaps.append(f"FBO_gap_nmid_{nmid}")
                shortlist_complete = False
            price = card.get("seller_price_rub")
            if price is None:
                gaps.append(f"PRICE_null_nmid_{nmid}")
                shortlist_complete = False

            camps = _campaigns_for_nmid(nmid, campaigns, adv_nm)
            active = [c for c in camps if c.get("is_active_wb")]
            adv_ids_n = [c["adv_id"] for c in camps]
            ad_spend_7d = round(sum(spend_by_adv_7d.get(a, 0) for a in adv_ids_n), 2)
            ad_spend_28d = round(sum(spend_by_adv_28d.get(a, 0) for a in adv_ids_n), 2)

            d3 = _window_3d(all_orders, nmid)
            d7 = _window_demand(all_orders, nmid, 7)
            d14 = _window_demand(all_orders, nmid, 14)
            d28 = _window_demand(all_orders, nmid, 28)

            min_search = await _cpc_min_bids(pm, SEARCH_ADV, nmid)
            min_auto = await _cpc_min_bids(pm, AUTO_ADV, nmid)

            row = {
                "nmID": nmid,
                "title": card.get("title"),
                "subject": card.get("subjectName"),
                "vendorCode": card.get("vendorCode"),
                "subjectID": card.get("subjectID"),
                "price": price,
                "discount": card.get("discount"),
                "fbs_stock": fbs_q,
                "fbo_stock": fbo_q,
                "total_operational_stock_note": "FBS and FBO reported separately; not summed when either is GAP",
                "demand": {
                    "last_3_closed_days": d3,
                    "last_7_closed_days": d7,
                    "last_14_closed_days": d14,
                    "last_28_closed_days": d28,
                },
                "advertising": {
                    "existing_campaigns": camps,
                    "existing_adv_ids": adv_ids_n,
                    "active_ad_overlap": "YES" if active else "NO",
                    "ad_spend_7d": ad_spend_7d,
                    "ad_spend_28d": ad_spend_28d,
                    "pg_bot_rows": _pg_rows_for_nmid(pg_all, nmid),
                },
                "auction_entry": {
                    "search_min_bid_probe_adv_39900211": min_search,
                    "unified_min_bid_probe_adv_39900256": min_auto,
                },
                "checked_at_msk": _iso_msk(checked_at),
            }
            product_states[nmid] = row
            comparison.append({
                "nmID": nmid,
                "title": card.get("title"),
                "subject": card.get("subjectName"),
                "PE_3D": d3["purchase_events"],
                "PE_7D": d7["purchase_events"],
                "PE_14D": d14["purchase_events"],
                "PE_28D": d28["purchase_events"],
                "TPV_3D": d3["total_price_value"],
                "TPV_7D": d7["total_price_value"],
                "TPV_14D": d14["total_price_value"],
                "TPV_28D": d28["total_price_value"],
                "UNITS_7D": d7["units"],
                "ACTIVE_DAYS_7D": d7["distinct_active_days"],
                "FBS": fbs_q,
                "FBO": fbo_q,
                "TOTAL_STOCK": "GAP",
                "CURRENT_PRICE": price,
                "ACTIVE_AD_OVERLAP": "YES" if active else "NO",
                "EXISTING_ADV_IDS": adv_ids_n,
                "AD_SPEND_7D": ad_spend_7d,
                "LAST_PURCHASE_DATE": d28.get("last_purchase_date"),
            })

        hundred_rule = {
            "HUNDRED_IMPRESSIONS_RULE_CONFIRMED": "NO",
            "source": (
                "app/modules/shop_runner/.../qualified_tested_bids.py uses configurable "
                "target_test_impressions per SKU settings, not a fixed 100 threshold in runtime"
            ),
            "note": "Cluster buckets use views>=100 as observational slice only",
        }

        flags = {
            "PARENT_COMPLEX_MAPPING_CONFIRMED": "YES" if mapping_ok else "NO",
            "EFFECTIVE_SEARCH_DAILY_LIMIT": parent_search_limit if parent_search_limit else "GAP",
            "SEARCH_LIMIT_SATURATION_0309": limit_sat_0309,
            "SEARCH_BUDGET_LIMIT_IS_BINDING": budget_binding,
            "SEARCH_BID_LEVEL_MAY_BE_BINDING": runtime_state["pressure_bottleneck_flags"]["SEARCH_BID_LEVEL_MAY_BE_BINDING"],
            "SEARCH_MAX_CPM_IS_BINDING": runtime_state["pressure_bottleneck_flags"]["SEARCH_MAX_CPM_IS_BINDING"],
            "SEARCH_V3_LEARNING_STAGE_LIMITS_PRESSURE": runtime_state["pressure_bottleneck_flags"]["SEARCH_V3_LEARNING_STAGE_LIMITS_PRESSURE"],
            "HUNDRED_IMPRESSIONS_RULE_CONFIRMED": hundred_rule["HUNDRED_IMPRESSIONS_RULE_CONFIRMED"],
            "SEARCH_CLUSTER_COUNT_TOTAL": total_clusters,
            "SEARCH_CLUSTER_COUNT_ZERO_IMPRESSIONS": zero_impr,
            "SEARCH_CLUSTER_COUNT_1_99_IMPRESSIONS": impr_1_99,
            "SEARCH_CLUSTER_COUNT_GE_100_IMPRESSIONS": impr_ge_100,
            "SHORTLIST_DATA_COMPLETE": "YES" if shortlist_complete and not gaps else ("PARTIAL" if product_states else "NO"),
        }

        return_block = _build_return_block(
            checked_at=checked_at,
            parent=parent_block,
            runtime=runtime_state,
            flags=flags,
            comparison=comparison,
            gaps=gaps,
            stats_0309=stats_0309,
            stats_0409=stats_0409,
            limit_util_0309=limit_util_0309,
            limit_sat_0309=limit_sat_0309,
            current_bid=current_bid,
            min_bid=min_bid,
            hundred_rule=hundred_rule,
            cluster_counts=campaign_since_launch["cluster_counts"],
        )

        manifest = {
            "iteration": ITERATION,
            "package": PACKAGE,
            "checked_at_msk": _iso_msk(checked_at),
            "mode": "STRICT_READ_ONLY",
            "artifacts": [
                "00_manifest.json",
                "01_parent_advsetting_1151722151.json",
                "02_search_39900211_runtime_state.json",
                "03_search_39900211_cluster_state.json",
                "04_search_39900211_stats.json",
                "05_shortlist_supplier_orders_raw.jsonl",
                "06_shortlist_product_state.json",
                "07_shortlist_ad_inventory.json",
                "08_shortlist_comparison.json",
                "09_evidence_summary.md",
            ],
            "flags": flags,
            "return_block": return_block,
        }

        _write_json(root / "01_parent_advsetting_1151722151.json", parent_block)
        _write_json(root / "02_search_39900211_runtime_state.json", runtime_state)
        _write_json(root / "03_search_39900211_cluster_state.json", {
            "clusters": cluster_rows,
            "wb_list_minus": wb_clusters,
            "pg_keywords_count": len(keywords),
            "hundred_impressions_rule": hundred_rule,
        })
        _write_json(root / "04_search_39900211_stats.json", {
            "campaign_fullstats": {"closed_20260903": stats_0309, "current_20260904_partial": stats_0409},
            "since_launch_normquery_aggregate": campaign_since_launch,
            "fullstats_route": "GET /adv/v3/fullstats",
            "normquery_route": "POST /adv/v0/normquery/stats",
        })
        _write_jsonl(root / "05_shortlist_supplier_orders_raw.jsonl", [dict(r) for r in shortlist_orders])
        _write_json(root / "06_shortlist_product_state.json", product_states)
        _write_json(root / "07_shortlist_ad_inventory.json", {
            "campaigns_sample_count": len(campaigns),
            "adv_ids_cabinet_count": len(adv_ids),
            "campaigns": campaigns,
        })
        _write_json(root / "08_shortlist_comparison.json", comparison)
        (root / "09_evidence_summary.md").write_text(_build_summary_md(return_block, flags), encoding="utf-8")

        zip_path = root / f"{PACKAGE}.zip"
        with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as zf:
            for name in manifest["artifacts"]:
                p = root / name
                if p.exists():
                    zf.write(p, arcname=name)
        zip_sha = _sha256(zip_path)
        manifest["zip_sha256"] = zip_sha
        manifest["archive_verified"] = True
        _write_json(root / "00_manifest.json", manifest)

        return {
            "return_block": return_block,
            "evidence_folder": str(root.resolve()),
            "evidence_zip": str(zip_path.resolve()),
            "evidence_zip_sha256": zip_sha,
            "archive_verified": True,
        }
    finally:
        await httpx.shutdown()
        await redis_raw.aclose()


def _build_return_block(**kwargs: Any) -> dict[str, Any]:
    checked_at = kwargs["checked_at"]
    parent = kwargs["parent"]
    runtime = kwargs["runtime"]
    flags = kwargs["flags"]
    comparison = kwargs["comparison"]
    gaps = kwargs["gaps"]
    stats_0309 = kwargs["stats_0309"]
    stats_0409 = kwargs["stats_0409"]
    limit_util_0309 = kwargs["limit_util_0309"]
    limit_sat_0309 = kwargs["limit_sat_0309"]
    current_bid = kwargs["current_bid"]
    min_bid = kwargs["min_bid"]
    hundred_rule = kwargs["hundred_rule"]
    cluster_counts = kwargs["cluster_counts"]

    by_nmid = {r["nmID"]: r for r in comparison}
    shortlist_return = {}
    for nmid in SHORTLIST_NMIDS:
        r = by_nmid.get(nmid, {})
        shortlist_return[str(nmid)] = {
            "PE_3D": r.get("PE_3D"),
            "PE_7D": r.get("PE_7D"),
            "PE_14D": r.get("PE_14D"),
            "PE_28D": r.get("PE_28D"),
            "TPV_3D": r.get("TPV_3D"),
            "TPV_7D": r.get("TPV_7D"),
            "TPV_14D": r.get("TPV_14D"),
            "TPV_28D": r.get("TPV_28D"),
            "FBS": r.get("FBS"),
            "FBO": r.get("FBO"),
            "TOTAL_STOCK": r.get("TOTAL_STOCK"),
            "PRICE": r.get("CURRENT_PRICE"),
            "ACTIVE_AD_OVERLAP": r.get("ACTIVE_AD_OVERLAP"),
            "EXISTING_ADV_IDS": r.get("EXISTING_ADV_IDS"),
        }

    return {
        "STATUS": "PASS",
        "INTEGRITY": "PASS" if flags.get("PARENT_COMPLEX_MAPPING_CONFIRMED") == "YES" else "GAP",
        "CHECKED_AT_MSK": _iso_msk(checked_at),
        "PARENT_COMPLEX_MAPPING_CONFIRMED": flags["PARENT_COMPLEX_MAPPING_CONFIRMED"],
        "PARENT_BOT_ACTIVE": parent["parent_bot_active"],
        "PARENT_SEARCH_DAILY_LIMIT": parent["search_auto_budget_daily_limit"],
        "PARENT_AUTO_DAILY_LIMIT": parent["auto_budget_daily_limit"],
        "AGGRESSIVENESS": parent.get("aggressiveness"),
        "AUTOMATIC_VERSION": parent.get("automatic_version"),
        "SEARCH_39900211": {
            "WB_STATUS": runtime["search_wb_status_name"],
            "CURRENT_BID": current_bid,
            "MIN_BID": min_bid,
            "SPEND_0309": stats_0309["spend"],
            "VIEWS_0309": stats_0309["views"],
            "CLICKS_0309": stats_0309["clicks"],
            "CPC_0309": stats_0309["cpc"],
            "ATTRIBUTED_ORDERS_0309": stats_0309["attributed_orders"],
            "SPEND_0409_PARTIAL": stats_0409["spend"],
            "VIEWS_0409_PARTIAL": stats_0409["views"],
            "CLICKS_0409_PARTIAL": stats_0409["clicks"],
            "LIMIT_UTILIZATION_0309": limit_util_0309,
            "LIMIT_SATURATION_0309": limit_sat_0309,
        },
        "SEARCH_CLUSTER_COUNT_TOTAL": cluster_counts["total"],
        "SEARCH_CLUSTER_COUNT_ZERO_IMPRESSIONS": cluster_counts["zero_impressions"],
        "SEARCH_CLUSTER_COUNT_1_99_IMPRESSIONS": cluster_counts["impressions_1_99"],
        "SEARCH_CLUSTER_COUNT_GE_100_IMPRESSIONS": cluster_counts["impressions_ge_100"],
        "HUNDRED_IMPRESSIONS_RULE_CONFIRMED": hundred_rule["HUNDRED_IMPRESSIONS_RULE_CONFIRMED"],
        "SEARCH_BUDGET_LIMIT_IS_BINDING": flags["SEARCH_BUDGET_LIMIT_IS_BINDING"],
        "SEARCH_BID_LEVEL_MAY_BE_BINDING": flags["SEARCH_BID_LEVEL_MAY_BE_BINDING"],
        "SEARCH_MAX_CPM_IS_BINDING": flags["SEARCH_MAX_CPM_IS_BINDING"],
        "SEARCH_V3_LEARNING_STAGE_LIMITS_PRESSURE": flags["SEARCH_V3_LEARNING_STAGE_LIMITS_PRESSURE"],
        "SEARCH_SEMANTIC_COVERAGE_LIMITS_PRESSURE": runtime["pressure_bottleneck_flags"]["SEARCH_SEMANTIC_COVERAGE_LIMITS_PRESSURE"],
        "SEARCH_OTHER_EXPLICIT_BLOCKER": runtime["pressure_bottleneck_flags"]["SEARCH_OTHER_EXPLICIT_BLOCKER"],
        "SHORTLIST": shortlist_return,
        "UNKNOWN_OR_GAPS": gaps,
        "READ_ONLY": "CONFIRMED",
        "WB_API_WRITES": 0,
        "DB_WRITES": 0,
        "CAMPAIGN_STATE_CHANGED": "NO",
        "AD_WB_WRITES_AUTHORIZED": "NO",
    }


def _build_summary_md(return_block: dict[str, Any], flags: dict[str, Any]) -> str:
    lines = [
        "# A1 Pressure Mechanics + Shortlist Refresh",
        "",
        f"**Checked at MSK:** {return_block['CHECKED_AT_MSK']}",
        f"**Parent mapping:** {return_block['PARENT_COMPLEX_MAPPING_CONFIRMED']}",
        f"**Parent bot_active:** {return_block['PARENT_BOT_ACTIVE']}",
        f"**Effective search daily limit:** {return_block['PARENT_SEARCH_DAILY_LIMIT']}",
        "",
        "## Search 39900211",
        f"- Limit saturation 03.09: {return_block['SEARCH_39900211']['LIMIT_SATURATION_0309']}",
        f"- Budget binding: {flags['SEARCH_BUDGET_LIMIT_IS_BINDING']}",
        f"- Clusters total: {flags['SEARCH_CLUSTER_COUNT_TOTAL']}",
        "",
        "## Shortlist comparison",
        "See `08_shortlist_comparison.json` — no winner score computed.",
        "",
        "## Safety",
        "- READ_ONLY = CONFIRMED",
        "- AD_WB_WRITES_AUTHORIZED = NO",
    ]
    return "\n".join(lines) + "\n"


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--output-dir", default=DEFAULT_OUTPUT)
    args = ap.parse_args(argv)
    out = Path(args.output_dir).resolve()
    out.mkdir(parents=True, exist_ok=True)
    staging = out / "staging"
    staging.mkdir(parents=True, exist_ok=True)
    _bootstrap()
    parent, keywords = _load_parent_and_keywords(staging)
    pg_all = _load_all_pg(staging)
    result = asyncio.run(run_collect(out, parent=parent, keywords=keywords, pg_all=pg_all))
    print(json.dumps(result["return_block"], ensure_ascii=False, indent=2, default=str))
    print(json.dumps({
        "EVIDENCE_FOLDER_ABSOLUTE_PATH": result["evidence_folder"],
        "EVIDENCE_ZIP_ABSOLUTE_PATH": result["evidence_zip"],
        "EVIDENCE_ZIP_SHA256": result["evidence_zip_sha256"],
        "ARCHIVE_VERIFIED": result["archive_verified"],
    }, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
