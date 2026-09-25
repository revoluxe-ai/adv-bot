"""READ_ONLY: A1 current-state gap collector (cabinet 401).

Закрывает GAP секций store economics, funnel, price/stock, runtime ad state и
promo для постоянного A1 refresh без повторного полного campaign inventory.
Production writes = 0; machine-readable JSON + human report + SHA-256 sidecar.
"""

from __future__ import annotations

import argparse
import asyncio
import hashlib
import json
import re
import sys
from collections import defaultdict
from datetime import date, datetime, timedelta, timezone
from pathlib import Path
from typing import Any
from zoneinfo import ZoneInfo

import dotenv

dotenv.load_dotenv()

from scripts.a1_cpc_two_sku_safety_preflight import _fetch_seller_stocks
from scripts.a1_sale_price_snapshot import fetch_prices
from scripts.wb_a1_associated_conversions import _read_float, _read_int
from scripts.wb_api_readonly_ops.collect.api_budget import ApiCallBudget
from scripts.wb_api_readonly_ops.collect.cards import collect_cards
from scripts.wb_api_readonly_ops.collect.jsonable import jsonable
from scripts.wb_api_readonly_ops.collect.orders_sales import _paginate_supplier_rows

SHOP_ID = "5339e9ad-cbfe-50fc-8d77-b9f337a80417"
WB_CABINET_ID = 401
MSK = ZoneInfo("Europe/Moscow")
PACKAGE = "A1-CURRENT-STATE-GAP"
NAME_SEARCH = re.compile(r"<!-\[(\d+)\]-!>")
ACTIVE_WB = {9, 11}

FUNNEL_FIELD_SEMANTICS = {
    "views": "CH full_adv_wb_stat.views — physical ad impressions (argMax by version)",
    "clicks": "CH full_adv_wb_stat.clicks — physical ad clicks",
    "orders": "CH full_adv_wb_stat.orders — WB-attributed orders on adv row (not store factual)",
    "gmv": "CH full_adv_wb_stat.sum_price_orders — attributed GMV on adv row",
    "opens_transitions": "GAP — not in full_adv_wb_stat; use wb_common_stat separately",
    "carts": "GAP — not in full_adv_wb_stat",
    "direct_orders": "GAP in this collector — see associated-conversions pack",
    "associative_orders": "GAP in this collector — see associated-conversions pack",
}


def _msk_now() -> datetime:
    return datetime.now(timezone.utc).astimezone(MSK)


def _iso_msk(dt: datetime) -> str:
    return dt.astimezone(MSK).isoformat()


def _parse_nmids(raw: str) -> list[int]:
    if not raw:
        return []
    try:
        val = json.loads(str(raw).replace("'", '"'))
        return [int(x) for x in val if str(x).isdigit()] if isinstance(val, list) else []
    except json.JSONDecodeError:
        return []


def _resolved_search(row: dict[str, Any]) -> int | None:
    raw = str(row.get("_search_adv_id") or "").strip()
    if raw.isdigit() and int(raw) > 0:
        return int(raw)
    m = NAME_SEARCH.search(str(row.get("name") or "").replace(" ", ""))
    return int(m.group(1)) if m else None


def _order_day_msk(row: dict[str, Any]) -> str | None:
    for key in ("date", "lastChangeDate", "orderDate", "createdAt"):
        val = row.get(key)
        if not val:
            continue
        try:
            if isinstance(val, str):
                if "T" in val:
                    dt = datetime.fromisoformat(val.replace("Z", "+00:00"))
                else:
                    return val[:10]
                return dt.astimezone(MSK).date().isoformat()
        except (TypeError, ValueError):
            continue
    return None


def _is_cancelled(row: dict[str, Any]) -> bool:
    for key in ("isCancel", "cancelDate"):
        if row.get(key):
            return True
    return str(row.get("status", "")).lower() in {"cancel", "cancelled", "canceled"}


def _sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


async def _pg_rows() -> list[dict[str, Any]]:
    from sqlalchemy import text
    from app.utils.db.session_maker import get_async_session_maker

    q = text(
        """
        SELECT a.*, c.shop_id
        FROM public.advsetting a
        JOIN public.wbcabinet c ON a.wb_cabinet_id = c.id
        WHERE c.id = :cab
        """
    )
    async with get_async_session_maker(read_only=True) as session:
        rows = (await session.execute(q, {"cab": WB_CABINET_ID})).mappings().all()
    return [dict(r) for r in rows]


def _bot_active_v3_contours(pg_rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = []
    for r in pg_rows:
        bot = str(r.get("bot_active")).lower() in ("true", "t", "1")
        if not bot:
            continue
        sid = _resolved_search(r)
        if str(r.get("automatic_version")) != "3" and not sid:
            continue
        nmids = _parse_nmids(str(r.get("nmids") or ""))
        out.append(
            {
                "adv_id": int(r["adv_id"]),
                "search_adv_id": sid,
                "nmids": nmids,
                "primary_nmid": nmids[0] if nmids else None,
                "active_status": r.get("active_status"),
                "aggressiveness": r.get("aggressiveness"),
                "automatic_version": r.get("automatic_version"),
                "strategy": r.get("strategy"),
                "base_target_cpo": r.get("target_price_for_order"),
                "base_max_cpo": r.get("max_price_for_order"),
                "auto_budget_daily_limit": r.get("auto_budget_daily_limit"),
                "search_auto_budget_daily_limit": r.get("search_auto_budget_daily_limit"),
            }
        )
    return out


async def _supplier_orders_sales(
    date_from: date,
) -> tuple[list[dict[str, Any]], list[dict[str, Any]], list[str]]:
    from app.core.di.app_container import AppContainer
    from app.core.di.di_manager import DIManager

    gaps: list[str] = []
    async with await DIManager.create(AppContainer) as container:  # type: ignore[attr-defined]
        factory = (
            container.module_resources.wb_manager_hub_factory_container.wb_manager_hub_factory()
        )
        hub = factory.get_wb_manager_hub(SHOP_ID)
        dm = hub.wb_data_manager
        reports_manager = getattr(dm, "reports_manager", None)
        budget = ApiCallBudget(max_seconds=1800.0, max_api_calls=5000)

        async def fetch_orders(df: str) -> list[object]:
            if reports_manager is not None:
                return list(
                    await reports_manager.get_supplier_orders(date_from=df, flag=0) or []
                )
            return list(await dm.get_supplier_orders(date_from=df, flag=0) or [])

        async def fetch_sales(df: str) -> list[object]:
            if reports_manager is not None:
                return list(
                    await reports_manager.get_supplier_sales(date_from=df, flag=0) or []
                )
            return list(await dm.get_supplier_sales(date_from=df, flag=0) or [])

        orders_res = await _paginate_supplier_rows(
            fetch=fetch_orders,
            initial_date_from=date_from.isoformat(),
            budget=budget,
            max_pages=1500,
        )
        sales_res = await _paginate_supplier_rows(
            fetch=fetch_sales,
            initial_date_from=date_from.isoformat(),
            budget=budget,
            max_pages=1500,
        )
        if orders_res.duplicate_page_detected:
            gaps.append("supplier_orders_duplicate_page_detected")
        if sales_res.duplicate_page_detected:
            gaps.append("supplier_sales_duplicate_page_detected")
        orders = [jsonable(r) for r in orders_res.rows if isinstance(jsonable(r), dict)]
        sales = [jsonable(r) for r in sales_res.rows if isinstance(jsonable(r), dict)]
    return orders, sales, gaps


def _store_economics(
    orders: list[dict[str, Any]],
    sales: list[dict[str, Any]],
    closed_start: date,
    closed_end: date,
    open_day: date,
) -> dict[str, Any]:
    daily: dict[str, dict[str, Any]] = defaultdict(
        lambda: {
            "order_rows": 0,
            "units": 0,
            "gmv_orders_field": 0.0,
            "cancelled_rows": 0,
            "purchase_events_sales": 0,
            "sales_gmv": 0.0,
            "day_class": "UNKNOWN",
        }
    )
    order_rows_out: list[dict[str, Any]] = []
    for row in orders:
        day = _order_day_msk(row)
        if not day:
            continue
        nmid = _read_int(row, "nmId", "nmID", "nmid")
        qty = _read_int(row, "quantity", "qty") or 1
        price = _read_float(row, "totalPrice", "priceWithDisc", "finishedPrice")
        gmv = (price or 0.0) * qty if price else 0.0
        cancelled = _is_cancelled(row)
        rec = {
            "day_msk": day,
            "nmId": nmid,
            "quantity": qty,
            "totalPrice": price,
            "gmv_estimate": round(gmv, 2),
            "is_cancelled": cancelled,
            "srid": row.get("srid") or row.get("orderId") or "GAP",
            "source": "statistics-api supplier orders",
        }
        order_rows_out.append(rec)
        if day < closed_start.isoformat() or day > open_day.isoformat():
            continue
        bucket = daily[day]
        bucket["order_rows"] += 1
        if not cancelled:
            bucket["units"] += qty
            bucket["gmv_orders_field"] += gmv
        else:
            bucket["cancelled_rows"] += 1
    for row in sales:
        day = _order_day_msk(row)
        if not day or day < closed_start.isoformat() or day > open_day.isoformat():
            continue
        bucket = daily[day]
        bucket["purchase_events_sales"] += 1
        bucket["sales_gmv"] += _read_float(row, "forPay", "finishedPrice", "totalPrice") or 0.0

    for day, bucket in daily.items():
        if closed_start.isoformat() <= day <= closed_end.isoformat():
            bucket["day_class"] = "CLOSED"
        elif day == open_day.isoformat():
            bucket["day_class"] = "OPEN_DAY"
        else:
            bucket["day_class"] = "OUT_OF_SCOPE"

    closed_totals = {
        "order_rows": 0,
        "units": 0,
        "gmv_orders_field": 0.0,
        "cancelled_rows": 0,
        "purchase_events_sales": 0,
        "sales_gmv": 0.0,
    }
    open_totals = dict(closed_totals)
    for day, bucket in daily.items():
        target = open_totals if bucket["day_class"] == "OPEN_DAY" else closed_totals
        if bucket["day_class"] != "CLOSED" and bucket["day_class"] != "OPEN_DAY":
            continue
        for k in closed_totals:
            target[k] += bucket[k]
    for t in (closed_totals, open_totals):
        for k, v in t.items():
            if isinstance(v, float):
                t[k] = round(v, 2)

    return {
        "semantics": {
            "order_date": "MSK calendar day from supplier order row timestamp fields",
            "gmv_orders_field": "totalPrice×qty on non-cancelled order rows (supplier orders)",
            "sales_gmv": "supplier sales forPay/finishedPrice — purchase event economics",
            "attribution_vs_factual": "NOT joined to adv attribution dates",
        },
        "by_day": {k: daily[k] for k in sorted(daily)},
        "closed_period": f"{closed_start}..{closed_end}",
        "closed_totals": closed_totals,
        "open_day": open_day.isoformat(),
        "open_day_totals": open_totals,
        "order_rows_sample_cap": 5000,
        "order_rows": order_rows_out[:5000],
        "order_rows_truncated": len(order_rows_out) > 5000,
    }


async def _ch_funnel_and_spend(
    adv_ids: list[int],
    closed_start: date,
    closed_end: date,
    open_day: date,
) -> dict[str, Any]:
    from app.utils.click_house.client import get_clickhouse_client

    if not adv_ids:
        return {"gap": "no_adv_ids", "rows": []}
    ids = ",".join(str(i) for i in sorted(set(adv_ids)))
    q = f"""
    SELECT adv_id, date,
           argMax(spend, version) AS spend,
           argMax(views, version) AS views,
           argMax(clicks, version) AS clicks,
           argMax(orders, version) AS orders,
           argMax(sum_price_orders, version) AS attributed_gmv
    FROM default_db.full_adv_wb_stat
    WHERE adv_id IN ({ids})
      AND date >= toDate('{closed_start.isoformat()}')
      AND date <= toDate('{open_day.isoformat()}')
    GROUP BY adv_id, date
    ORDER BY date, adv_id
    """
    async with get_clickhouse_client() as client:
        rows = [dict(r) for r in (await client.query(q)).named_results()]

    by_day_closed: dict[str, dict[str, float]] = defaultdict(
        lambda: {"spend": 0.0, "views": 0.0, "clicks": 0.0, "orders": 0.0, "attributed_gmv": 0.0}
    )
    by_day_open: dict[str, float] = defaultdict(float)
    for r in rows:
        day = str(r.get("date"))[:10]
        spend = float(r.get("spend") or 0)
        if day <= closed_end.isoformat():
            b = by_day_closed[day]
            b["spend"] += spend
            b["views"] += float(r.get("views") or 0)
            b["clicks"] += float(r.get("clicks") or 0)
            b["orders"] += float(r.get("orders") or 0)
            b["attributed_gmv"] += float(r.get("attributed_gmv") or 0)
        elif day == open_day.isoformat():
            by_day_open["spend"] += spend
            by_day_open["views"] += float(r.get("views") or 0)
            by_day_open["clicks"] += float(r.get("clicks") or 0)
            by_day_open["orders"] += float(r.get("orders") or 0)
            by_day_open["attributed_gmv"] += float(r.get("attributed_gmv") or 0)

    return {
        "source": "default_db.full_adv_wb_stat",
        "semantics": FUNNEL_FIELD_SEMANTICS,
        "cumulative_vs_interval": "daily interval rows (not cumulative)",
        "by_day_closed": {k: {kk: round(vv, 2) for kk, vv in by_day_closed[k].items()} for k in sorted(by_day_closed)},
        "open_day": {k: round(v, 2) for k, v in by_day_open.items()},
        "raw_row_count": len(rows),
    }


async def _runtime_ad_state(contours: list[dict[str, Any]]) -> dict[str, Any]:
    from app.utils.click_house.client import get_clickhouse_client

    adv_nm: list[tuple[int, int]] = []
    for c in contours:
        nmid = c.get("primary_nmid")
        if not nmid:
            continue
        for aid in (c.get("adv_id"), c.get("search_adv_id")):
            if aid:
                adv_nm.append((int(aid), int(nmid)))

    runtime: list[dict[str, Any]] = []
    gaps: list[str] = []
    if not adv_nm:
        return {"rows": runtime, "gaps": ["no_contours"]}

    async with get_clickhouse_client() as client:
        for adv_id, nmid in adv_nm:
            q = f"""
            SELECT
              argMax(target_cpo, version) AS runtime_target_cpo,
              argMax(max_cpo, version) AS runtime_max_cpo,
              argMax(final_bid, version) AS live_final_bid,
              argMax(cpm_curr, version) AS live_cpm_curr,
              argMax(decision_time, version) AS decision_time,
              argMax(aggressiveness, version) AS runtime_aggressiveness
            FROM default_db.bid_decision_log
            WHERE adv_id = {adv_id} AND nmid = {nmid}
            """
            try:
                res = list((await client.query(q)).named_results())
            except Exception as exc:  # noqa: BLE001
                gaps.append(f"bid_decision_log_query_fail adv={adv_id}: {exc}")
                res = []
            row = res[0] if res else {}
            runtime.append(
                {
                    "adv_id": adv_id,
                    "nmid": nmid,
                    "base_target_cpo": next(
                        (c["base_target_cpo"] for c in contours if c.get("adv_id") == adv_id or c.get("search_adv_id") == adv_id),
                        "GAP",
                    ),
                    "base_max_cpo": next(
                        (c["base_max_cpo"] for c in contours if c.get("adv_id") == adv_id or c.get("search_adv_id") == adv_id),
                        "GAP",
                    ),
                    "runtime_target_cpo": row.get("runtime_target_cpo"),
                    "runtime_max_cpo": row.get("runtime_max_cpo"),
                    "live_final_bid": row.get("live_final_bid"),
                    "live_cpm_curr": row.get("live_cpm_curr"),
                    "runtime_aggressiveness": row.get("runtime_aggressiveness"),
                    "decision_time": row.get("decision_time"),
                    "bid_source": "CH bid_decision_log argMax(version) — internal not WB API",
                    "promo_overlay_adjusted": "GAP — not derived in this collector",
                }
            )
    return {"rows": runtime, "gaps": gaps}


async def _promo_snapshot() -> dict[str, Any]:
    from app.configs.app_config import AppConfig
    from app.core.di.wb_manager_hub.wb_manager_hub_factory import WBManagerHubFactory
    from app.core.mp.wb.api.httpx_client_handler import HttpxClientHandler
    from app.core.redis_manager_v2.redis_client import RedisClient
    from app.modules.common_slaves.wildberries.super_cabinet_manager import (
        get_access_for_wb_cabinet,
    )
    from redis.asyncio import Redis

    app_config = AppConfig.create()
    rc = app_config.infrastructure.redis
    redis_raw: Redis[str] = Redis(
        host=rc.host, port=rc.port, db=rc.db, password=rc.password, decode_responses=True
    )
    httpx = HttpxClientHandler()
    await httpx.init()
    out: dict[str, Any] = {"historical_m2_expired_2026-09-11": "NOT_ACTIVE_WITHOUT_LIVE_EVIDENCE"}
    try:
        await get_access_for_wb_cabinet(SHOP_ID)
        hub = WBManagerHubFactory(
            httpx_client_handler=httpx, redis_client_wrapper=RedisClient(redis_client=redis_raw)
        ).get_wb_manager_hub(SHOP_ID)
        finance = hub.wb_data_manager.promotion_manager._client.finance_adapter
        bal = await finance.get_campaign_balance()
        out["balance_raw"] = json.loads(json.dumps(bal, default=str))
        out["promo_active_evidence"] = "UNKNOWN"
        out["owner_funded_spend"] = "UNKNOWN"
    finally:
        await httpx.shutdown()
        await redis_raw.aclose()
    return out


async def _price_stock(nmids: list[int], checked_at: datetime) -> dict[str, Any]:
    from app.core.di.app_container import AppContainer
    from app.core.di.di_manager import DIManager

    nmids = sorted({int(n) for n in nmids if n})
    gaps: list[str] = []
    prices: dict[int, Any] = {}
    stocks: dict[int, Any] = {}
    async with await DIManager.create(AppContainer) as container:  # type: ignore[attr-defined]
        factory = (
            container.module_resources.wb_manager_hub_factory_container.wb_manager_hub_factory()
        )
        hub = factory.get_wb_manager_hub(SHOP_ID)
        dm = hub.wb_data_manager
        budget = ApiCallBudget(max_seconds=600.0, max_api_calls=500)
        from scripts.wb_api_readonly_ops.collect.raw_store import RawStore

        card_store = RawStore(Path("/tmp/a1_gap_cards_raw"))
        _, cards_list = await collect_cards(dm, store=card_store, budget=budget, page_limit=100)
        cards = {
            _read_int(c, "nmID", "nmId"): jsonable(c)
            for c in cards_list
            if _read_int(c, "nmID", "nmId")
        }
        subset = {n: cards[n] for n in nmids if n in cards}
        missing_cards = [n for n in nmids if n not in cards]
        if missing_cards:
            gaps.append(f"content_cards_missing_nmids={missing_cards}")
        try:
            price_rows, _route, pgaps = await fetch_prices(nmids)
            gaps.extend(pgaps)
            for pr in price_rows:
                nid = _read_int(pr, "nmID", "nmId")
                if nid:
                    prices[nid] = pr
        except Exception as exc:  # noqa: BLE001
            gaps.append(f"price_api_fail:{exc}")
        try:
            seller = await _fetch_seller_stocks(dm.products_manager, subset)
            by_nmid = seller.get("by_nmid") or {}
            for nmid in nmids:
                entry = by_nmid.get(nmid, {})
                fbs = entry.get("total_sellable")
                stocks[nmid] = {
                    "fbs": fbs if fbs is not None else "MISSING",
                    "fbo": "MISSING",
                    "total": fbs if fbs is not None else "MISSING",
                    "warehouse_breakdown": entry.get("warehouses") or "GAP",
                    "source": seller.get("source", "POST /api/v3/stocks/{warehouse_id}"),
                    "checked_at_msk": _iso_msk(checked_at),
                }
        except Exception as exc:  # noqa: BLE001
            gaps.append(f"stock_api_fail:{exc}")

    rows = []
    for nmid in nmids:
        pr = prices.get(nmid, {})
        st = stocks.get(nmid, {})
        rows.append(
            {
                "nmid": nmid,
                "seller_price": pr.get("price"),
                "wb_display_discounted_price": pr.get("discountedPrice"),
                "discount_percent": pr.get("discount"),
                "spp_semantics": "discount field from goods/filter — not confirmed SPP",
                "price_status": pr.get("STATUS", "MISSING"),
                "fbs": st.get("fbs", "MISSING"),
                "fbo": st.get("fbo", "MISSING"),
                "total_stock": st.get("total", "MISSING"),
                "stock_source": st.get("source"),
                "checked_at_msk": st.get("checked_at_msk"),
            }
        )
    return {"rows": rows, "gaps": gaps, "missing_not_zero": True}


def _write_report_md(path: Path, payload: dict[str, Any]) -> None:
    gaps = payload.get("gaps") or []
    lines = [
        f"# {PACKAGE}",
        f"**CHECKED_AT_MSK:** {payload.get('checked_at_msk')}",
        f"**CLOSED:** {payload.get('closed_period')}",
        f"**OPEN_DAY:** {payload.get('open_day')}",
        "",
        "## Store economics (closed totals)",
        json.dumps(payload.get("store_economics", {}).get("closed_totals"), ensure_ascii=False),
        "",
        "## OPEN_DAY totals",
        json.dumps(payload.get("store_economics", {}).get("open_day_totals"), ensure_ascii=False),
        "",
        "## Funnel (CH closed by day)",
        "See JSON `funnel.by_day_closed`",
        "",
        "## Remaining GAPs",
    ]
    lines.extend(f"- {g}" for g in gaps)
    lines.append("\n**BUSINESS_WRITES: 0**")
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


async def run_collect(
    output_dir: Path,
    closed_start: date,
    closed_end: date,
    open_day: date,
) -> dict[str, Any]:
    checked_at = _msk_now()
    gaps: list[str] = []
    pg_rows = await _pg_rows()
    contours = _bot_active_v3_contours(pg_rows)
    nmids = sorted(
        {n for c in contours for n in (c.get("nmids") or []) if n}
    )

    orders, sales, ogaps = await _supplier_orders_sales(closed_start - timedelta(days=1))
    gaps.extend(ogaps)
    store = _store_economics(orders, sales, closed_start, closed_end, open_day)

    adv_ids: set[int] = set()
    for c in contours:
        if c.get("adv_id"):
            adv_ids.add(int(c["adv_id"]))
        if c.get("search_adv_id"):
            adv_ids.add(int(c["search_adv_id"]))
    funnel = await _ch_funnel_and_spend(list(adv_ids), closed_start, closed_end, open_day)
    runtime = await _runtime_ad_state(contours)
    gaps.extend(runtime.get("gaps") or [])
    promo = await _promo_snapshot()
    price_stock = await _price_stock(nmids, checked_at)
    gaps.extend(price_stock.get("gaps") or [])

    payload: dict[str, Any] = {
        "package": PACKAGE,
        "mode": "STRICT_READ_ONLY",
        "shop_id": SHOP_ID,
        "wb_cabinet_id": WB_CABINET_ID,
        "timezone": "Europe/Moscow",
        "checked_at_msk": _iso_msk(checked_at),
        "closed_period": f"{closed_start}..{closed_end}",
        "open_day": open_day.isoformat(),
        "bot_active_v3_contour_count": len(contours),
        "bot_active_nmids": nmids,
        "store_economics": store,
        "funnel": funnel,
        "price_stock": price_stock,
        "runtime_ad_state": runtime,
        "promo": promo,
        "integrity": {
            "missing_null_failure_unsupported": "explicit GAP/MISSING in fields",
            "campaign_inventory": "SKIPPED — use prior refresh JSON",
        },
        "gaps": gaps,
        "business_writes": 0,
    }

    output_dir.mkdir(parents=True, exist_ok=True)
    primary_name = f"{PACKAGE}_{open_day.isoformat()}.json"
    primary = output_dir / primary_name
    primary.write_text(json.dumps(payload, ensure_ascii=False, indent=2, default=str) + "\n", encoding="utf-8")
    digest = _sha256_file(primary)
    (output_dir / f"{primary_name}.sha256").write_text(digest + "\n", encoding="utf-8")
    report = output_dir / f"{PACKAGE}_{open_day.isoformat()}_REPORT.md"
    _write_report_md(report, payload)

    return {
        "EXECUTION_STATUS": "COMPLETE_WITH_GAPS" if gaps else "COMPLETE",
        "PRIMARY_ARTIFACT": primary_name,
        "PRIMARY_SHA256": digest,
        "ZIP_ABSOLUTE_PATH": str(primary.resolve()),
        "LOCAL_REPORT": str(report.resolve()),
        "GAPS": gaps,
        **{k: 0 for k in ("WB_API_WRITES", "POSTGRES_WRITES", "CLICKHOUSE_WRITES")},
    }


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="A1 current-state gap READ_ONLY collector.")
    parser.add_argument("--output-dir", default="/tmp/a1_current_state_gap")
    parser.add_argument("--closed-start", default="2026-09-07")
    parser.add_argument("--closed-end", default="2026-09-13")
    parser.add_argument("--open-day", default="2026-09-14")
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    try:
        result = asyncio.run(
            run_collect(
                Path(args.output_dir),
                date.fromisoformat(args.closed_start),
                date.fromisoformat(args.closed_end),
                date.fromisoformat(args.open_day),
            )
        )
    except Exception as exc:  # noqa: BLE001
        print(f"ops-script: failed; error={exc}", file=sys.stderr)
        return 1
    print(json.dumps(result, ensure_ascii=False, indent=2))
    print(f"PRIMARY_SHA256={result['PRIMARY_SHA256']}")
    print(f"PRIMARY_ARTIFACT={result['PRIMARY_ARTIFACT']}")
    print("ops-script: success; holding for output copy")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
