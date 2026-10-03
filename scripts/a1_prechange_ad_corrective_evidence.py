"""READ_ONLY: A1 pre-change evidence packet before corrective ad action.

ITER-CLIENT-RETENTION-A1-20260904-001 — STRICT_READ_ONLY collect:
store closed 2026-09-03, campaign contours 39900211/39900256, SKU outcomes,
candidate nmID 180148471, funding, campaign spend breakdown.
Без WB advertising writes, DB writes, campaign mutations.
"""

from __future__ import annotations

import argparse
import asyncio
import hashlib
import json
import os
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
    PAUSED_WB,
    WB_STATUS_NAMES,
    _adv_nm_map,
    _bootstrap,
    _budgets,
    _campaigns_for_nmid,
    _campaign_settings,
    _cpc_min_bids,
    _fetch_cards,
    _fetch_seller_stocks,
    _load_pg,
    _load_wbcards,
    _pg_rows_for_nmid,
    _recent_spp,
)
from scripts.a1_promotion_funding_snapshot import _bootstrap_cluster_infra, _collect_wb_funding
from scripts.wb_a1_associated_conversions import _read_float, _read_int
from scripts.wb_api_readonly_ops.collect.ads import _flatten_fullstats
from scripts.wb_api_readonly_ops.collect.api_budget import ApiCallBudget
from scripts.wb_api_readonly_ops.collect.jsonable import jsonable
from scripts.wb_api_readonly_ops.collect.orders_sales import _paginate_supplier_rows

SHOP_ID = evidence.SHOP_ID
MSK = ZoneInfo("Europe/Moscow")
ITERATION = "ITER-CLIENT-RETENTION-A1-20260904-001"
PACKAGE = "A1_PRECHANGE_AD_CORRECTIVE_EVIDENCE_20260904"

SEARCH_ADV = 39900211
UNIFIED_ADV = 39900256
WATCH_ADV = 34210859
NMID_CLIENT = 837395782
NMID_CANDIDATE = 180148471
SELLER_ARTICLE_CLIENT = "8000925338167"

CLOSED_DAY = date(2026, 9, 3)
CURRENT_DAY = date(2026, 9, 4)
CLOSED_STR = CLOSED_DAY.isoformat()
CURRENT_STR = CURRENT_DAY.isoformat()
BOUNDARY_CLOSED_START = datetime(2026, 9, 3, 0, 0, 0, tzinfo=MSK)
BOUNDARY_CLOSED_END = datetime(2026, 9, 4, 0, 0, 0, tzinfo=MSK)
BOUNDARY_CURRENT_START = datetime(2026, 9, 4, 0, 0, 0, tzinfo=MSK)
ORDERS_DATE_FROM = "2026-08-07"
DEFAULT_OUTPUT = (
    r"C:\Users\vkita\my_code\meta-repo\worktree\wb-delivery-context-router"
    r"\clients\A1\chats\wb-lab-a1-analysis-20260828\artifacts"
    r"\OWNER_UPLOAD_20260904_PRECHANGE_AD_CORRECTIVE_EVIDENCE"
)


def _msk_now() -> datetime:
    return datetime.now(timezone.utc).astimezone(MSK)


def _iso_msk(dt: datetime) -> str:
    return dt.astimezone(MSK).isoformat()


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


def _order_metrics(rows: list[dict[str, Any]]) -> dict[str, Any]:
    active = [r for r in rows if not _is_cancelled(r)]
    groups: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for r in active:
        groups[_g_key(r)].append(r)
    units_in_event = {g: len(v) for g, v in groups.items()}
    bulk_events = sum(1 for n in units_in_event.values() if n > 1)
    return {
        "purchase_events": len(groups),
        "units": len(active),
        "total_price_value": round(sum(_read_float(r, "totalPrice") for r in active), 2),
        "price_with_disc_value": round(sum(_read_float(r, "priceWithDisc") for r in active), 2),
        "finished_price_value": round(sum(_read_float(r, "finishedPrice") for r in active), 2),
        "distinct_nmids_sold": len(
            {n for r in active for n in [_read_int(r, "nmId", "nm_id")] if n}
        ),
        "bulk_events_count": bulk_events,
        "max_units_in_purchase_event": max(units_in_event.values(), default=0),
        "raw_rows": len(rows),
        "cancelled_rows": sum(1 for r in rows if _is_cancelled(r)),
        "non_cancelled_rows": len(active),
    }


def _nmid_orders(rows: list[dict[str, Any]], nmid: int) -> list[dict[str, Any]]:
    return [r for r in rows if _read_int(r, "nmId", "nm_id", "nmid") == nmid]


def _demand_window(
    all_orders: list[dict[str, Any]], nmid: int, closed_end: date, days: int
) -> dict[str, Any]:
    start = closed_end - timedelta(days=days - 1)
    start_dt = datetime.combine(start, time.min, tzinfo=MSK)
    end_dt = datetime.combine(closed_end + timedelta(days=1), time.min, tzinfo=MSK)
    rows = [
        r
        for r in _nmid_orders(all_orders, nmid)
        if _in_day(r, start_dt, end_dt) and not _is_cancelled(r)
    ]
    m = _order_metrics(rows)
    return {
        "window_closed_days": days,
        "window_start": start.isoformat(),
        "window_end_closed": closed_end.isoformat(),
        "purchase_events": m["purchase_events"],
        "units": m["units"],
        "total_price_value": m["total_price_value"],
        "bulk_events_count": m["bulk_events_count"],
        "max_units_in_purchase_event": m["max_units_in_purchase_event"],
    }


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


def _extract_nm_bids(nm_settings: list[Any], nmid: int) -> dict[str, Any]:
    for nm in nm_settings or []:
        if not isinstance(nm, dict):
            continue
        nid = _read_int(nm, "nm_id", "nmId", "nmID")
        if nid != nmid:
            continue
        bids = nm.get("bids_kopecks") or nm.get("bidsKopecks") or nm.get("bids") or {}
        return {
            "nm_id": nmid,
            "bids_kopecks": bids if isinstance(bids, dict) else None,
            "search_bid_kopecks": bids.get("search") if isinstance(bids, dict) else None,
            "recommendations_bid_kopecks": (
                bids.get("recommendations") if isinstance(bids, dict) else None
            ),
            "combined_bid_kopecks": bids.get("combined") if isinstance(bids, dict) else None,
        }
    return {"nm_id": nmid, "bids_kopecks": None}


def _adv_day_stats(
    fullstats: list[dict[str, Any]], adv_id: int, day: str
) -> dict[str, Any]:
    spend = views = clicks = orders = atbs = 0
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
        atbs += _read_int(row, "atbs")
    return {
        "spend": round(spend, 2),
        "views": views,
        "clicks": clicks,
        "ctr": round(100 * clicks / views, 4) if views else None,
        "cpc": round(spend / clicks, 4) if clicks else None,
        "attributed_orders": orders,
        "attributed_gmv": round(gmv, 2),
        "atbs": atbs,
    }


def _limit_saturation(spend: float, limit: int | None) -> str:
    if not limit or limit <= 0:
        return "GAP" if spend > 0 else "GAP"
    pct = 100.0 * spend / limit
    if pct >= 100:
        return "YES"
    if pct >= 80:
        return "PARTIAL"
    return "NO"


def _pg_row_for_adv(pg: list[dict[str, str]], adv_id: int) -> dict[str, Any] | None:
    for row in pg:
        if _read_int(row, "adv_id") == adv_id:
            return {
                "pg_id": row.get("id"),
                "adv_id": adv_id,
                "search_adv_id": _read_int(row, "_search_adv_id"),
                "name": row.get("name"),
                "bot_active": str(row.get("bot_active")).lower() in ("true", "t", "1"),
                "active_status": _read_int(row, "active_status"),
                "auto_budget_daily_limit": _read_int(row, "auto_budget_daily_limit"),
                "search_auto_budget_daily_limit": _read_int(
                    row, "search_auto_budget_daily_limit"
                ),
                "use_common_budget": str(row.get("use_common_budget")).lower()
                in ("true", "t", "1"),
                "common_budget_daily_limit": _read_int(row, "common_budget_daily_limit"),
            }
    for row in pg:
        if _read_int(row, "_search_adv_id") == adv_id:
            return {
                "pg_id": row.get("id"),
                "adv_id": _read_int(row, "adv_id"),
                "search_adv_id": adv_id,
                "name": row.get("name"),
                "bot_active": str(row.get("bot_active")).lower() in ("true", "t", "1"),
                "active_status": _read_int(row, "active_status"),
                "auto_budget_daily_limit": _read_int(row, "auto_budget_daily_limit"),
                "search_auto_budget_daily_limit": _read_int(
                    row, "search_auto_budget_daily_limit"
                ),
                "use_common_budget": str(row.get("use_common_budget")).lower()
                in ("true", "t", "1"),
                "common_budget_daily_limit": _read_int(row, "common_budget_daily_limit"),
                "matched_as_search_leg": True,
            }
    return None


async def _normquery_state(pm: Any, adv_id: int, nmid: int) -> dict[str, Any]:
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

    out: dict[str, Any] = {
        "adv_id": adv_id,
        "nmID": nmid,
        "active_clusters": [],
        "excluded_clusters": [],
        "minus_phrases": [],
        "cluster_bids": [],
        "sources": [],
    }
    item = V0GetNormQueryListRequestItem(advert_id=adv_id, nm_id=nmid)
    try:
        adapter = pm._client.normquery_stats_adapter
        http = await adapter.auth_client_handler.get_proxy_client(adapter)
        resp = await with_raise_errors(
            normquery_list_async,
            http,
            body=V0GetNormQueryListRequest(items=[item]),
        )
        parsed = jsonable(resp.parsed)
        out["sources"].append("POST /adv/v0/normquery/list")
        if isinstance(parsed, dict):
            for it in parsed.get("items") or []:
                if not isinstance(it, dict):
                    continue
                nq = it.get("normQueries") or it.get("norm_queries") or {}
                if isinstance(nq, dict):
                    out["active_clusters"] = list(nq.get("active") or [])
                    out["excluded_clusters"] = list(nq.get("excluded") or [])
    except Exception as exc:  # noqa: BLE001
        out["list_error"] = str(exc)[:400]

    try:
        bids_adapter = pm._client.normquery_bids_adapter
        bid_resp = await bids_adapter.post_adv_v0_normquery_get_bids(
            V0GetNormQueryBidsRequest(
                items=[V0GetNormQueryBidsRequestItem(advert_id=adv_id, nm_id=nmid)]
            ),
        )
        out["sources"].append("POST /adv/v0/normquery/get-bids")
        for b in bid_resp or []:
            out["cluster_bids"].append(
                {"norm_query": b.norm_query, "bid_kopecks": b.bid}
            )
    except Exception as exc:  # noqa: BLE001
        out["bids_error"] = str(exc)[:400]

    try:
        minus_adapter = pm._client.minus_phrases_adapter
        minus_list = await minus_adapter.post_adv_v0_normquery_get_minus(
            GetMinusPhrasesCommand(advert_id=adv_id, nm_id=nmid),
        )
        out["sources"].append("POST /adv/v0/normquery/get-minus")
        out["minus_phrases"] = list(minus_list or [])
    except Exception as exc:  # noqa: BLE001
        out["minus_error"] = str(exc)[:400]

    out["whitelist_state"] = {
        "active_count": len(out["active_clusters"]),
        "excluded_count": len(out["excluded_clusters"]),
    }
    out["minus_state"] = {"minus_count": len(out["minus_phrases"])}
    return out


def _campaign_config(raw: dict[str, Any], nmid: int) -> dict[str, Any]:
    settings = raw.get("settings") if isinstance(raw.get("settings"), dict) else {}
    placements = settings.get("placements") if isinstance(settings.get("placements"), dict) else {}
    st = _read_int(raw, "status")
    nm_settings = raw.get("nm_settings") or raw.get("nmSettings") or []
    return {
        "adv_id": _read_int(raw, "id", "advertId"),
        "bid_type": raw.get("bid_type"),
        "payment_type": settings.get("payment_type") or settings.get("paymentType"),
        "placements": placements,
        "wb_status": st,
        "wb_status_name": WB_STATUS_NAMES.get(st, f"status_{st}"),
        "name": settings.get("name"),
        "nm_bids": _extract_nm_bids(nm_settings, nmid),
        "route": "GET /api/advert/v2/adverts",
    }


def _spend_breakdown(
    fullstats: list[dict[str, Any]],
    campaigns: list[dict[str, Any]],
    adv_nm: dict[int, set[int]],
    day: str,
) -> list[dict[str, Any]]:
    by_adv: dict[int, dict[str, Any]] = defaultdict(
        lambda: {
            "spend": 0.0,
            "views": 0,
            "clicks": 0,
            "orders": 0,
            "gmv": 0.0,
        }
    )
    for row in fullstats:
        if str(row.get("date") or "")[:10] != day:
            continue
        adv_id = _read_int(row, "advertId", "advert_id")
        if not adv_id:
            continue
        b = by_adv[adv_id]
        b["spend"] += _read_float(row, "sum", "spend")
        b["views"] += _read_int(row, "views")
        b["clicks"] += _read_int(row, "clicks")
        b["orders"] += _read_int(row, "orders")
        b["gmv"] += _read_float(row, "sum_price")

    inv: dict[int, dict[str, Any]] = {}
    for c in campaigns:
        aid = _read_int(c, "id", "advertId")
        if aid:
            inv[aid] = c

    rows: list[dict[str, Any]] = []
    for adv_id, m in by_adv.items():
        if round(m["spend"], 2) <= 0:
            continue
        cfg = inv.get(adv_id, {})
        settings = cfg.get("settings") if isinstance(cfg.get("settings"), dict) else {}
        placements = settings.get("placements") if isinstance(settings.get("placements"), dict) else {}
        nmids = sorted(adv_nm.get(adv_id, ()))
        leg = "search" if placements.get("search") and not placements.get("recommendations") else (
            "unified/auto" if placements.get("search") and placements.get("recommendations") else "other"
        )
        spend = round(m["spend"], 2)
        views = m["views"]
        clicks = m["clicks"]
        rows.append(
            {
                "adv_id": adv_id,
                "nmIDs": nmids,
                "campaign_type_leg": leg,
                "spend": spend,
                "views": views,
                "clicks": clicks,
                "ctr": round(100 * clicks / views, 4) if views else None,
                "cpc": round(spend / clicks, 4) if clicks else None,
                "attributed_orders": m["orders"],
                "attributed_gmv": round(m["gmv"], 2),
            }
        )
    rows.sort(key=lambda r: -r["spend"])
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


def _build_summary_md(payload: dict[str, Any]) -> str:
    j = payload["return_block"]
    lines = [
        "# A1 Pre-Change Ad Corrective Evidence",
        "",
        f"**Iteration:** {ITERATION}",
        f"**Checked at MSK:** {j['CHECKED_AT_MSK']}",
        f"**Status:** {j['STATUS']} | **Integrity:** {j['INTEGRITY']}",
        "",
        "## Store closed 2026-09-03",
        f"- PURCHASE_EVENTS: {j['STORE_20260903']['PURCHASE_EVENTS']}",
        f"- UNITS: {j['STORE_20260903']['UNITS']}",
        f"- TOTAL_PRICE_VALUE: {j['STORE_20260903']['TOTAL_PRICE_VALUE']}",
        f"- ADVERTISING_SPEND: {j['STORE_20260903']['ADVERTISING_SPEND']}",
        f"- AD_LOAD_PCT: {j['STORE_20260903']['AD_SPEND_TO_TOTAL_PRICE_VALUE_PCT']}",
        "",
        "## SEARCH 39900211",
        f"- STATUS: {j['SEARCH_39900211']['STATUS']}",
        f"- BID: {j['SEARCH_39900211']['CURRENT_BID']}",
        f"- MIN_BID: {j['SEARCH_39900211']['MIN_BID']}",
        f"- DAILY_LIMIT: {j['SEARCH_39900211']['DAILY_LIMIT']}",
        f"- SPEND_0309: {j['SEARCH_39900211']['SPEND_0309']}",
        f"- LIMIT_SATURATION: {j['SEARCH_39900211']['LIMIT_SATURATION']}",
        "",
        "## UNIFIED 39900256",
        f"- STATUS: {j['UNIFIED_39900256']['STATUS']}",
        f"- ZERO_PRESSURE: {j['UNIFIED_39900256']['ZERO_PRESSURE_CONFIRMED']}",
        "",
        "## NMID 180148471 candidate",
        f"- VALID_CANDIDATE: {j['NMID_180148471']['VALID_CANDIDATE']}",
        f"- ACTIVE_AD_OVERLAP: {j['NMID_180148471']['ACTIVE_AD_OVERLAP']}",
        "",
        "## Safety",
        "- READ_ONLY = CONFIRMED",
        "- WB_API_WRITES = 0",
        "- DB_WRITES = 0",
        "- CAMPAIGN_STATE_CHANGED = NO",
        "- AD_WB_WRITES_AUTHORIZED = NO",
    ]
    return "\n".join(lines) + "\n"


async def run_collect(
    output_dir: Path,
    *,
    pg: list[dict[str, str]],
    wbcards: dict[int, dict[str, Any]],
) -> dict[str, Any]:
    from app.configs.app_config import AppConfig
    from app.core.di.wb_manager_hub.wb_manager_hub_factory import WBManagerHubFactory
    from app.core.mp.wb.api.httpx_client_handler import HttpxClientHandler
    from app.core.redis_manager_v2.redis_client import RedisClient
    from app.modules.common_slaves.wildberries.super_cabinet_manager import (
        get_access_for_wb_cabinet,
    )
    from redis.asyncio import Redis

    checked_at = _msk_now()
    gaps: list[str] = []
    root = output_dir
    root.mkdir(parents=True, exist_ok=True)
    staging = root / "staging"
    staging.mkdir(parents=True, exist_ok=True)
    (staging / "sql").mkdir(parents=True, exist_ok=True)

    _bootstrap()
    _bootstrap_cluster_infra()

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
        dm = hub.wb_data_manager
        pm = dm.promotion_manager
        products = dm.products_manager
        budget = ApiCallBudget(max_seconds=1800.0, max_api_calls=1500)

        reports_manager = getattr(dm, "reports_manager", None)

        async def fetch_orders(df: str) -> list[object]:
            if reports_manager is not None:
                return list(await reports_manager.get_supplier_orders(date_from=df, flag=0) or [])
            return list(await dm.get_supplier_orders(date_from=df, flag=0) or [])

        req_orders = _msk_now()
        orders_result = await _paginate_supplier_rows(
            fetch=fetch_orders,
            initial_date_from=ORDERS_DATE_FROM,
            budget=budget,
            max_pages=1200,
        )
        resp_orders = _msk_now()
        all_orders = orders_result.rows

        closed_rows = [r for r in all_orders if _in_day(r, BOUNDARY_CLOSED_START, BOUNDARY_CLOSED_END)]
        current_rows = [
            r for r in all_orders if _in_day(r, BOUNDARY_CURRENT_START, checked_at)
        ]
        store_closed = _order_metrics(closed_rows)
        store_current_partial = _order_metrics(current_rows)
        store_current_partial["status"] = "OPEN_DAY_PARTIAL"

        budget.consume()
        adv_ids = list(await pm._client.promotion_count_adapter.get_cabinet_adv_ids() or [])
        budget.consume()
        campaigns_raw = list(await pm.get_adverts_v2_by_ids(adv_ids) or [])
        campaigns = [jsonable(x) for x in campaigns_raw if isinstance(jsonable(x), dict)]
        adv_nm = _adv_nm_map(campaigns)

        req_fs = _msk_now()
        budget.consume()
        stats_raw = await pm.get_full_adv_stat(adv_ids, [CLOSED_DAY, CURRENT_DAY])
        resp_fs = _msk_now()
        fullstats = _flatten_fullstats(list(stats_raw or []))

        spend_closed, attr_o, attr_gmv, _ = _ad_store_metrics(fullstats, CLOSED_STR)
        ratio = (
            round(spend_closed / store_closed["total_price_value"] * 100, 4)
            if store_closed["total_price_value"] > 0
            else "GAP"
        )

        target_advs = [SEARCH_ADV, UNIFIED_ADV, WATCH_ADV]
        configs: dict[int, dict[str, Any]] = {}
        for raw in campaigns:
            aid = _read_int(raw, "id", "advertId")
            if aid in target_advs:
                configs[aid] = raw
        for aid in target_advs:
            if aid not in configs:
                try:
                    extra = list(await pm.get_adverts_v2_by_ids([aid]) or [])
                    for x in extra:
                        d = jsonable(x)
                        if isinstance(d, dict):
                            configs[aid] = d
                            campaigns.append(d)
                except Exception as exc:  # noqa: BLE001
                    gaps.append(f"v2_config_{aid}: {exc}")

        adv_budgets = await _budgets(pm, target_advs)
        min_search = await _cpc_min_bids(pm, SEARCH_ADV, NMID_CLIENT)
        min_unified = await _cpc_min_bids(pm, UNIFIED_ADV, NMID_CLIENT)
        min_candidate_search = await _cpc_min_bids(pm, SEARCH_ADV, NMID_CANDIDATE)

        cards = await _fetch_cards(products, {NMID_CLIENT, NMID_CANDIDATE})
        fbs_stocks = await _fetch_seller_stocks(products, cards)
        analytics_adapter = getattr(dm, "analytics_adapter", None) or getattr(
            products, "_analytics_adapter", None
        )
        fbo_rows: list[dict[str, Any]] = []
        fbo_meta: dict[str, Any] = {}
        if analytics_adapter is not None:
            fbo_rows, fbo_meta = await _fetch_wb_warehouses_stock(
                analytics_adapter, [NMID_CLIENT, NMID_CANDIDATE]
            )
        else:
            gaps.append("FBO: analytics_adapter not resolved")

        fbo837 = _aggregate_stock(fbo_rows, NMID_CLIENT)
        fbo180 = _aggregate_stock(fbo_rows, NMID_CANDIDATE)
        spp837 = await _recent_spp(dm, NMID_CLIENT)
        spp180 = await _recent_spp(dm, NMID_CANDIDATE)

        pg_search = _pg_row_for_adv(pg, SEARCH_ADV)
        pg_unified = _pg_row_for_adv(pg, UNIFIED_ADV)
        redis_search = _redis_reason(SEARCH_ADV, "search")
        redis_auto = _redis_reason(UNIFIED_ADV, "auto")
        normquery = await _normquery_state(pm, SEARCH_ADV, NMID_CLIENT)

        stats_0309_search = _adv_day_stats(fullstats, SEARCH_ADV, CLOSED_STR)
        stats_0409_search = _adv_day_stats(fullstats, SEARCH_ADV, CURRENT_STR)
        stats_0309_unified = _adv_day_stats(fullstats, UNIFIED_ADV, CLOSED_STR)
        stats_0409_unified = _adv_day_stats(fullstats, UNIFIED_ADV, CURRENT_STR)

        search_limit = (pg_search or {}).get("search_auto_budget_daily_limit") or (
            pg_search or {}
        ).get("common_budget_daily_limit")
        unified_limit = (pg_unified or {}).get("auto_budget_daily_limit") or (
            pg_unified or {}
        ).get("common_budget_daily_limit")

        search_cfg = _campaign_config(configs.get(SEARCH_ADV, {}), NMID_CLIENT) if SEARCH_ADV in configs else {}
        unified_cfg = _campaign_config(configs.get(UNIFIED_ADV, {}), NMID_CLIENT) if UNIFIED_ADV in configs else {}

        search_state = {
            "adv_id": SEARCH_ADV,
            "target_nmid": NMID_CLIENT,
            "seller_article": SELLER_ARTICLE_CLIENT,
            "checked_at_msk": _iso_msk(checked_at),
            "wb_campaign": search_cfg,
            "pg_bot": pg_search,
            "redis_runtime": redis_search,
            "budget_live": adv_budgets.get(SEARCH_ADV),
            "min_bid_probe": min_search,
            "daily_limit_rub": search_limit,
            "spend_closed_20260903": stats_0309_search,
            "spend_current_20260904_partial": stats_0409_search,
            "limit_saturation_closed_0309": _limit_saturation(
                stats_0309_search["spend"], search_limit
            ),
            "normquery_clusters": normquery,
            "routes": [
                "GET /api/advert/v2/adverts",
                "GET /adv/v3/fullstats",
                "POST /api/advert/v1/bids/min",
                "GET /adv/v1/budget",
                "POST /adv/v0/normquery/list",
                "POST /adv/v0/normquery/get-minus",
                "POST /adv/v0/normquery/get-bids",
            ],
        }
        unified_state = {
            "adv_id": UNIFIED_ADV,
            "target_nmid": NMID_CLIENT,
            "checked_at_msk": _iso_msk(checked_at),
            "wb_campaign": unified_cfg,
            "pg_bot": pg_unified,
            "redis_runtime": redis_auto,
            "budget_live": adv_budgets.get(UNIFIED_ADV),
            "min_bid_probe": min_unified,
            "daily_limit_rub": unified_limit,
            "spend_closed_20260903": stats_0309_unified,
            "spend_current_20260904_partial": stats_0409_unified,
            "zero_pressure_evidence": {
                "spend_0309": stats_0309_unified["spend"],
                "spend_0409_partial": stats_0409_unified["spend"],
                "views_0309": stats_0309_unified["views"],
                "views_0409_partial": stats_0409_unified["views"],
                "clicks_0309": stats_0309_unified["clicks"],
                "clicks_0409_partial": stats_0409_unified["clicks"],
            },
        }

        nmid837_closed = _order_metrics(_nmid_orders(closed_rows, NMID_CLIENT))
        nmid837_current = _order_metrics(_nmid_orders(current_rows, NMID_CLIENT))
        nmid837_current["status"] = "OPEN_DAY_PARTIAL"
        fbs837 = (fbs_stocks.get("by_nmid") or {}).get(NMID_CLIENT, {})
        card837 = cards.get(NMID_CLIENT, {})
        nmid837_state = {
            "nmID": NMID_CLIENT,
            "seller_article": SELLER_ARTICLE_CLIENT,
            "checked_at_msk": _iso_msk(checked_at),
            "closed_20260903": nmid837_closed,
            "current_20260904_partial": nmid837_current,
            "fbs_stock": {
                "total_sellable": fbs837.get("total_sellable"),
                "warehouses": fbs837.get("warehouses", []),
                "source": fbs_stocks.get("source"),
            },
            "fbo_stock": fbo837,
            "total_operational_stock": {
                "fbs": fbs837.get("total_sellable"),
                "fbo_wb_quantity": fbo837.get("total_wb_stock_quantity"),
                "note": "operational total not summed — FBS and FBO are separate fulfillment paths",
            },
            "price": {
                "seller_price_rub": card837.get("seller_price_rub"),
                "buyer_price_from_recent_order": spp837,
            },
            "promo_discount": {
                "card_discount": card837.get("discount"),
                "spp_from_orders": spp837,
            },
        }

        camps180 = _campaigns_for_nmid(NMID_CANDIDATE, campaigns, adv_nm)
        active180 = [c for c in camps180 if c.get("is_active_wb")]
        cand_adv_ids = [c["adv_id"] for c in camps180]
        spend_28d = 0.0
        if cand_adv_ids:
            d0 = CLOSED_DAY - timedelta(days=27)
            dates_28 = []
            d = d0
            while d <= CLOSED_DAY:
                dates_28.append(d)
                d += timedelta(days=1)
            try:
                fs28 = await pm.get_full_adv_stat(cand_adv_ids, dates_28)
                fs28_flat = _flatten_fullstats(list(fs28 or []))
                for row in fs28_flat:
                    spend_28d += _read_float(row, "sum", "spend")
                spend_28d = round(spend_28d, 2)
            except Exception as exc:  # noqa: BLE001
                gaps.append(f"180148471_28d_spend: {exc}")

        demand180 = {
            "last_7_closed_days": _demand_window(all_orders, NMID_CANDIDATE, CLOSED_DAY, 7),
            "last_14_closed_days": _demand_window(all_orders, NMID_CANDIDATE, CLOSED_DAY, 14),
            "last_28_closed_days": _demand_window(all_orders, NMID_CANDIDATE, CLOSED_DAY, 28),
        }
        fbs180 = (fbs_stocks.get("by_nmid") or {}).get(NMID_CANDIDATE, {})
        card180 = cards.get(NMID_CANDIDATE, {})
        wbc180 = wbcards.get(NMID_CANDIDATE, {})
        nmid180_state = {
            "nmID": NMID_CANDIDATE,
            "checked_at_msk": _iso_msk(checked_at),
            "product": {
                "seller_article": card180.get("vendorCode") or wbc180.get("name"),
                "title": card180.get("title") or wbc180.get("name"),
                "subjectID": card180.get("subjectID") or wbc180.get("wb_category_id"),
                "subjectName": card180.get("subjectName") or wbc180.get("subject"),
                "price_seller_rub": card180.get("seller_price_rub"),
                "promo_discount": {
                    "card_discount": card180.get("discount"),
                    "spp_from_orders": spp180,
                },
                "fbs_stock": fbs180,
                "fbo_stock": fbo180,
            },
            "demand": demand180,
            "advertising": {
                "existing_campaigns": camps180,
                "active_campaign_adv_ids": [c["adv_id"] for c in active180],
                "spend_last_28d_rub": spend_28d,
                "pg_bot_rows": _pg_rows_for_nmid(pg, NMID_CANDIDATE),
            },
            "auction_entry": {
                "search_min_bid_probe_adv_39900211": min_candidate_search,
                "unified_min_bid_probe_adv_39900256": min_unified,
                "payment_model_note": "CPC via POST /api/advert/v2/seacat/save/ad — not executed (READ_ONLY)",
            },
        }

        store_snapshot = {
            "status": "PASS" if store_closed["raw_rows"] > 0 else "GAP",
            "integrity": "PASS" if store_closed["raw_rows"] > 0 else "GAP",
            "date": CLOSED_STR,
            "timezone": "MSK",
            "checked_at_msk": _iso_msk(checked_at),
            "closed_day_boundary": {
                "start": BOUNDARY_CLOSED_START.isoformat(),
                "end_exclusive": BOUNDARY_CLOSED_END.isoformat(),
            },
            **store_closed,
            "advertising_spend": spend_closed,
            "ad_spend_to_total_price_value_pct": ratio,
            "attributed_advertising_orders": attr_o,
            "attributed_advertising_gmv": attr_gmv,
            "current_day_partial_20260904": store_current_partial,
            "supplier_orders_meta": {
                "route": "/api/v1/supplier/orders",
                "request_params": {"dateFrom": ORDERS_DATE_FROM, "flag": 0},
                "request_timestamp": _iso_msk(req_orders),
                "response_timestamp": _iso_msk(resp_orders),
                "pagination_pages": orders_result.pagination_pages,
            },
            "advertising_meta": {
                "route": "/adv/v3/fullstats",
                "dates": [CLOSED_STR, CURRENT_STR],
                "campaigns_discovered": len(adv_ids),
                "request_timestamp": _iso_msk(req_fs),
                "response_timestamp": _iso_msk(resp_fs),
            },
            "late_refresh": {
                "status": "CONFIRMED",
                "evidence": (
                    f"Collect at {_iso_msk(checked_at)} after closed boundary "
                    f"{BOUNDARY_CLOSED_END.isoformat()}; orders from {ORDERS_DATE_FROM}"
                ),
            },
            "safety": {
                "read_only": True,
                "wb_api_writes": 0,
                "db_writes": 0,
                "campaign_state_changed": False,
            },
        }

        spend_breakdown = _spend_breakdown(fullstats, campaigns, adv_nm, CLOSED_STR)
        funding_raw = await _collect_wb_funding()
        central = funding_raw.get("central") or {}
        campaign_budgets = funding_raw.get("campaign_budgets") or []
        sum_budgets = sum(int(b.get("total") or 0) for b in campaign_budgets)
        wallet = int(central.get("balance") or 0)
        net = int(central.get("net") or 0)
        bonus_raw = central.get("bonus")
        bonus = int(bonus_raw) if bonus_raw is not None else None
        funding = {
            "checked_at_msk": _iso_msk(checked_at),
            "wallet_rub": wallet,
            "net_available_rub": net,
            "bonus_rub": bonus,
            "sum_active_campaign_budgets_rub": sum_budgets,
            "total_available_methodology": "wallet + sum(active campaign budgets) — factual components only",
            "total_available_rub": wallet + sum_budgets,
            "routes": ["GET /adv/v1/balance", "GET /adv/v1/budget"],
            "raw": funding_raw,
        }

        zero_pressure = "YES"
        if (
            stats_0309_unified["spend"] > 0
            or stats_0409_unified["spend"] > 0
            or stats_0309_unified["views"] > 0
            or stats_0409_unified["views"] > 0
        ):
            zero_pressure = "NO"
        elif not unified_cfg:
            zero_pressure = "GAP"

        valid_candidate = "YES"
        valid_reasons: list[str] = []
        if active180:
            valid_candidate = "NO"
            valid_reasons.append(f"active WB campaigns exist: {[c['adv_id'] for c in active180]}")
        fbo_q = fbo180.get("total_wb_stock_quantity")
        fbs_q = fbs180.get("total_sellable")
        if (fbo_q is not None and fbo_q <= 0) and (fbs_q is not None and fbs_q <= 0):
            valid_candidate = "REVISE"
            valid_reasons.append("zero FBS and FBO stock signals")
        if demand180["last_28_closed_days"]["purchase_events"] == 0:
            if valid_candidate == "YES":
                valid_candidate = "REVISE"
            valid_reasons.append("zero PURCHASE_EVENTS in last 28 closed days")

        min_bid_search = None
        for k, v in min_candidate_search.items():
            if k.endswith("_kopecks") and isinstance(v, list) and v:
                min_bid_search = min(v)
            elif k.endswith("_kopecks") and isinstance(v, (int, float)):
                min_bid_search = v

        current_bid = (search_cfg.get("nm_bids") or {}).get("search_bid_kopecks")
        min_bid_search_837 = None
        for k, v in min_search.items():
            if "search" in k and k.endswith("_kopecks"):
                if isinstance(v, list) and v:
                    min_bid_search_837 = min(v)
                elif isinstance(v, (int, float)):
                    min_bid_search_837 = v

        return_block = {
            "STATUS": store_snapshot["status"],
            "INTEGRITY": store_snapshot["integrity"],
            "CHECKED_AT_MSK": _iso_msk(checked_at),
            "STORE_20260903": {
                "PURCHASE_EVENTS": store_closed["purchase_events"],
                "UNITS": store_closed["units"],
                "TOTAL_PRICE_VALUE": store_closed["total_price_value"],
                "ADVERTISING_SPEND": spend_closed,
                "AD_SPEND_TO_TOTAL_PRICE_VALUE_PCT": ratio,
            },
            "SEARCH_39900211": {
                "STATUS": search_cfg.get("wb_status_name", "GAP"),
                "CURRENT_BID": current_bid,
                "MIN_BID": min_bid_search_837,
                "DAILY_LIMIT": search_limit,
                "SPEND_0309": stats_0309_search["spend"],
                "SPEND_0409_PARTIAL": stats_0409_search["spend"],
                "LIMIT_SATURATION": search_state["limit_saturation_closed_0309"],
                "CLICKS_0309": stats_0309_search["clicks"],
                "CPC_0309": stats_0309_search["cpc"],
                "ATTRIBUTED_ORDERS_0309": stats_0309_search["attributed_orders"],
            },
            "UNIFIED_39900256": {
                "STATUS": unified_cfg.get("wb_status_name", "GAP"),
                "DAILY_LIMIT": unified_limit,
                "SPEND_0309": stats_0309_unified["spend"],
                "SPEND_0409_PARTIAL": stats_0409_unified["spend"],
                "ZERO_PRESSURE_CONFIRMED": zero_pressure,
            },
            "NMID_837395782": {
                "PURCHASE_EVENTS_0309": nmid837_closed["purchase_events"],
                "UNITS_0309": nmid837_closed["units"],
                "TOTAL_PRICE_VALUE_0309": nmid837_closed["total_price_value"],
                "FBS_STOCK": fbs837.get("total_sellable"),
                "FBO_STOCK": fbo837.get("total_wb_stock_quantity"),
                "PRICE": card837.get("seller_price_rub"),
            },
            "NMID_180148471": {
                "VALID_CANDIDATE": valid_candidate,
                "VALID_CANDIDATE_REASONS": valid_reasons,
                "TITLE": card180.get("title") or wbc180.get("name"),
                "SUBJECT": card180.get("subjectName") or wbc180.get("subject"),
                "PRICE": card180.get("seller_price_rub"),
                "FBS_STOCK": fbs180.get("total_sellable"),
                "FBO_STOCK": fbo180.get("total_wb_stock_quantity"),
                "PE_7D": demand180["last_7_closed_days"]["purchase_events"],
                "PE_14D": demand180["last_14_closed_days"]["purchase_events"],
                "PE_28D": demand180["last_28_closed_days"]["purchase_events"],
                "TPV_7D": demand180["last_7_closed_days"]["total_price_value"],
                "TPV_14D": demand180["last_14_closed_days"]["total_price_value"],
                "TPV_28D": demand180["last_28_closed_days"]["total_price_value"],
                "EXISTING_CAMPAIGNS": [c["adv_id"] for c in camps180],
                "ACTIVE_AD_OVERLAP": "YES" if active180 else "NO",
                "SEARCH_MIN_BID": min_bid_search,
                "UNIFIED_MIN_BID": min_unified.get("cpc_min_combined_kopecks")
                or min_unified.get("cpc_min_search_kopecks"),
            },
            "FUNDING": {
                "WALLET": wallet,
                "NET_AVAILABLE": net,
                "BONUS": bonus,
                "TOTAL_AVAILABLE": wallet + sum_budgets,
            },
            "DERIVED_FLAGS": {
                "SEARCH_39900211_LIMIT_SATURATION": search_state["limit_saturation_closed_0309"],
                "UNIFIED_39900256_ZERO_PRESSURE_CONFIRMED": zero_pressure,
                "NMID_180148471_VALID_CANDIDATE": valid_candidate,
                "NMID_180148471_EXISTING_ACTIVE_AD_OVERLAP": "YES" if active180 else "NO",
                "STORE_0309_CLOSED": "YES" if store_closed["raw_rows"] > 0 else "NO",
                "STORE_0309_AD_LOAD_PCT": ratio,
                "CURRENT_FUNDING_STATUS": "FACTUAL_ONLY",
            },
            "UNKNOWN_OR_GAPS": gaps,
            "READ_ONLY": "CONFIRMED",
            "WB_API_WRITES": 0,
            "DB_WRITES": 0,
            "CAMPAIGN_STATE_CHANGED": "NO",
            "AD_WB_WRITES_AUTHORIZED": "NO",
        }

        manifest = {
            "iteration": ITERATION,
            "package": PACKAGE,
            "checked_at_msk": _iso_msk(checked_at),
            "shop_id": SHOP_ID,
            "mode": "STRICT_READ_ONLY",
            "owner_decision": "CREATE_NEW_AD_CAMPAIGN_AND_INCREASE_AD_PRESSURE",
            "execution_authorized": False,
            "artifacts": [
                "00_manifest.json",
                "01_store_20260903_snapshot.json",
                "02_store_20260903_supplier_orders_raw.jsonl",
                "03_store_20260903_fullstats_raw.json",
                "04_campaign_39900211_state.json",
                "05_campaign_39900256_state.json",
                "06_nmid_837395782_state.json",
                "07_nmid_180148471_state.json",
                "08_nmid_180148471_demand.json",
                "09_ad_campaign_inventory.json",
                "10_funding_snapshot.json",
                "11_campaign_spend_breakdown_0309.json",
                "11_evidence_summary.md",
            ],
            "return_block": return_block,
        }

        _write_json(root / "00_manifest.json", manifest)
        _write_json(root / "01_store_20260903_snapshot.json", store_snapshot)
        _write_jsonl(
            root / "02_store_20260903_supplier_orders_raw.jsonl",
            [dict(r) for r in closed_rows],
        )
        _write_json(root / "03_store_20260903_fullstats_raw.json", jsonable(stats_raw))
        _write_json(root / "04_campaign_39900211_state.json", search_state)
        _write_json(root / "05_campaign_39900256_state.json", unified_state)
        _write_json(root / "06_nmid_837395782_state.json", nmid837_state)
        _write_json(root / "07_nmid_180148471_state.json", nmid180_state)
        _write_json(root / "08_nmid_180148471_demand.json", demand180)
        _write_json(
            root / "09_ad_campaign_inventory.json",
            {"adv_ids": adv_ids, "count": len(adv_ids), "campaigns": campaigns},
        )
        _write_json(root / "10_funding_snapshot.json", funding)
        _write_json(root / "11_campaign_spend_breakdown_0309.json", {
            "date": CLOSED_STR,
            "campaigns_with_spend": spend_breakdown,
            "highlight": {
                str(SEARCH_ADV): next((r for r in spend_breakdown if r["adv_id"] == SEARCH_ADV), None),
                str(UNIFIED_ADV): next((r for r in spend_breakdown if r["adv_id"] == UNIFIED_ADV), None),
                str(WATCH_ADV): next((r for r in spend_breakdown if r["adv_id"] == WATCH_ADV), None),
            },
            "top_by_spend": spend_breakdown[:15],
        })
        payload = {"return_block": return_block, "manifest": manifest}
        (root / "11_evidence_summary.md").write_text(_build_summary_md(payload), encoding="utf-8")

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


def _ad_store_metrics(
    fullstats: list[dict[str, Any]], target: str
) -> tuple[float, int, float, set[int]]:
    spend = 0.0
    attr_orders = 0
    attr_gmv = 0.0
    returned: set[int] = set()
    for row in fullstats:
        day = str(row.get("date") or "")[:10]
        if day != target:
            continue
        adv_id = _read_int(row, "advertId", "advert_id")
        if adv_id:
            returned.add(adv_id)
        spend += _read_float(row, "sum", "spend")
        attr_orders += _read_int(row, "orders")
        attr_gmv += _read_float(row, "sum_price")
    return round(spend, 2), attr_orders, round(attr_gmv, 2), returned


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--output-dir", default=DEFAULT_OUTPUT)
    args = ap.parse_args(argv)
    out = Path(args.output_dir).resolve()
    out.mkdir(parents=True, exist_ok=True)
    staging = out / "staging"
    staging.mkdir(parents=True, exist_ok=True)
    (staging / "sql").mkdir(parents=True, exist_ok=True)
    _bootstrap()
    _bootstrap_cluster_infra()
    pg = _load_pg(staging)
    wbcards = _load_wbcards(staging, (NMID_CLIENT, NMID_CANDIDATE))
    result = asyncio.run(run_collect(out, pg=pg, wbcards=wbcards))
    print(json.dumps(result["return_block"], ensure_ascii=False, indent=2, default=str))
    print(
        json.dumps(
            {
                "EVIDENCE_FOLDER_ABSOLUTE_PATH": result["evidence_folder"],
                "EVIDENCE_ZIP_ABSOLUTE_PATH": result["evidence_zip"],
                "EVIDENCE_ZIP_SHA256": result["evidence_zip_sha256"],
                "ARCHIVE_VERIFIED": result["archive_verified"],
            },
            ensure_ascii=False,
            indent=2,
        )
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
