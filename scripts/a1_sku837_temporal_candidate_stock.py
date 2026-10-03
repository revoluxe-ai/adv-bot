"""READ_ONLY: A1 SKU 837395782 temporal demand + growth-candidate FBO stock.

Период заказов 2026-08-05..2026-09-01; FBO via wb-warehouses analytics API.
Без writes.
"""

from __future__ import annotations

import argparse
import asyncio
import json
import sys
from collections import defaultdict
from datetime import date, datetime, timezone
from pathlib import Path
from typing import Any
from zoneinfo import ZoneInfo

import dotenv

dotenv.load_dotenv()

from scripts.wb_a1_associated_conversions import _read_float, _read_int
from scripts.wb_api_readonly_ops.collect.api_budget import ApiCallBudget
from scripts.wb_api_readonly_ops.collect.jsonable import jsonable
from scripts.wb_api_readonly_ops.collect.orders_sales import _paginate_supplier_rows

SHOP_ID = "5339e9ad-cbfe-50fc-8d77-b9f337a80417"
MSK = ZoneInfo("Europe/Moscow")
PACKAGE = "A1-SKU837-TEMPORAL-CANDIDATE-STOCK"

TARGET_NMID = 837395782
PERIOD_FROM = date(2026, 8, 5)
PERIOD_TO = date(2026, 9, 1)
CANDIDATE_NMIDS = (206697189, 288483603, 14824677, 180145507)
DOW_NAMES = ("Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun")


def _msk_now() -> datetime:
    return datetime.now(timezone.utc).astimezone(MSK)


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


def _in_period(row: dict[str, Any]) -> bool:
    dt = _msk_dt(row)
    if not dt:
        return False
    d = dt.date()
    return PERIOD_FROM <= d <= PERIOD_TO


def _sku_temporal(orders: list[dict[str, Any]]) -> dict[str, Any]:
    """Агрегация PURCHASE_EVENTS / TPV / bulk по часу и DOW для одного SKU."""
    groups_by_hour: dict[int, dict[str, list[dict[str, Any]]]] = defaultdict(dict)
    groups_by_dow: dict[int, dict[str, list[dict[str, Any]]]] = defaultdict(dict)

    for row in orders:
        if _read_int(row, "nmId", "nm_id", "nmid") != TARGET_NMID:
            continue
        if _is_cancelled(row) or not _in_period(row):
            continue
        dt = _msk_dt(row)
        if not dt:
            continue
        gk = _g_key(row)
        hour = dt.hour
        dow = dt.weekday()
        groups_by_hour[hour].setdefault(gk, []).append(row)
        groups_by_dow[dow].setdefault(gk, []).append(row)

    def _metrics(groups: dict[str, list[dict[str, Any]]]) -> dict[str, Any]:
        pe = len(groups)
        units = sum(len(v) for v in groups.values())
        bulk = sum(1 for v in groups.values() if len(v) >= 2)
        single = pe - bulk
        tpv = round(sum(_read_float(r, "totalPrice") for rs in groups.values() for r in rs), 2)
        return {
            "PURCHASE_EVENTS": pe,
            "single_unit_events": single,
            "bulk_events": bulk,
            "UNITS": units,
            "TOTAL_PRICE_VALUE": tpv,
        }

    by_hour = []
    for hour in sorted(groups_by_hour):
        m = _metrics(groups_by_hour[hour])
        by_hour.append({"hour_msk": hour, **m})

    by_dow = []
    for dow in sorted(groups_by_dow):
        m = _metrics(groups_by_dow[dow])
        by_dow.append({"day_of_week": DOW_NAMES[dow], "dow_idx": dow, **m})

    tpv_by_hour = [{"hour_msk": h["hour_msk"], "TOTAL_PRICE_VALUE": h["TOTAL_PRICE_VALUE"]} for h in by_hour]
    bulk_by_hour = [{"hour_msk": h["hour_msk"], "bulk_events": h["bulk_events"]} for h in by_hour]
    pe_by_hour = [{"hour_msk": h["hour_msk"], "PURCHASE_EVENTS": h["PURCHASE_EVENTS"]} for h in by_hour]

    # Top-5 clean: rank by single_unit_events (excludes bulk checkout distortion)
    clean_rank = sorted(
        [
            {
                "hour_msk": h["hour_msk"],
                "single_unit_events": h["single_unit_events"],
                "bulk_events": h["bulk_events"],
                "raw_PURCHASE_EVENTS": h["PURCHASE_EVENTS"],
                "TOTAL_PRICE_VALUE": h["TOTAL_PRICE_VALUE"],
            }
            for h in by_hour
            if h["single_unit_events"] > 0
        ],
        key=lambda x: (-x["single_unit_events"], -x["TOTAL_PRICE_VALUE"]),
    )[:5]

    return {
        "nmID": TARGET_NMID,
        "period": f"{PERIOD_FROM.isoformat()}..{PERIOD_TO.isoformat()}",
        "PURCHASE_EVENTS_BY_HOUR_MSK": pe_by_hour,
        "PURCHASE_EVENTS_BY_DAY_OF_WEEK": by_dow,
        "TOTAL_PRICE_VALUE_BY_HOUR_MSK": tpv_by_hour,
        "BULK_EVENTS_BY_HOUR_MSK": bulk_by_hour,
        "TOP_5_HOURS_CLEAN": clean_rank,
        "interpretation_note": (
            "TOP_5_HOURS_CLEAN ranked by single_unit_events (gNumber with 1 unit); "
            "bulk_events (>=2 units per gNumber) excluded from ranking"
        ),
    }


async def _fetch_wb_stock(adapter: Any, nmids: list[int]) -> list[dict[str, Any]]:
    client = await adapter.auth_client_handler.get_proxy_client(adapter)
    body = {"nmIds": nmids, "limit": 250000, "offset": 0}
    http = client.get_async_httpx_client()
    response = await http.request(
        method="post",
        url="/api/analytics/v1/stocks-report/wb-warehouses",
        json=body,
        headers={"Content-Type": "application/json"},
    )
    if response.status_code != 200:
        raise RuntimeError(f"wb-warehouses HTTP {response.status_code}: {response.text[:500]}")

    payload = response.json()
    rows: list[dict[str, Any]] = []
    if isinstance(payload, dict):
        data = payload.get("data") or payload.get("stocks") or payload.get("items")
        if isinstance(data, list):
            rows = [x if isinstance(x, dict) else jsonable(x) for x in data]
    elif isinstance(payload, list):
        rows = [x if isinstance(x, dict) else jsonable(x) for x in payload]

    agg: dict[int, dict[str, int]] = {
        n: {"stock": 0, "inWayToClient": 0, "inWayFromClient": 0} for n in nmids
    }
    for r in rows:
        if not isinstance(r, dict):
            continue
        nmid = _read_int(r, "nmId", "nm_id", "nmid")
        if nmid not in agg:
            continue
        agg[nmid]["stock"] += _read_int(r, "quantity") or 0
        agg[nmid]["inWayToClient"] += _read_int(r, "inWayToClient") or 0
        agg[nmid]["inWayFromClient"] += _read_int(r, "inWayFromClient") or 0

    return [
        {"nmID": n, **agg[n]}
        for n in nmids
    ]


async def run() -> dict[str, Any]:
    from app.configs.app_config import AppConfig
    from app.core.di.wb_manager_hub.wb_manager_hub_factory import WBManagerHubFactory
    from app.core.mp.wb.api.httpx_client_handler import HttpxClientHandler
    from app.core.redis_manager_v2.redis_client import RedisClient
    from app.modules.common_slaves.wildberries.super_cabinet_manager import get_access_for_wb_cabinet
    from redis.asyncio import Redis

    checked = _msk_now()
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
        budget = ApiCallBudget(max_seconds=900.0, max_api_calls=800)
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
        temporal = _sku_temporal(orders_res.rows)

        analytics = dm._analytics_manager._AnalyticsManager__wb_api_client.sales_funnel_adapter
        candidate_stock = await _fetch_wb_stock(analytics, list(CANDIDATE_NMIDS))

        return {
            "CHECKED_AT_MSK": checked.strftime("%Y-%m-%d %H:%M:%S %Z"),
            "SKU_837395782_TEMPORAL": temporal,
            "CANDIDATE_FBO_STOCK": candidate_stock,
            "NO_WRITES": "CONFIRMED",
        }
    finally:
        await httpx.shutdown()
        await redis_raw.aclose()


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--output-dir", default=".tmp/a1_sku837_temporal_stock")
    args = ap.parse_args(argv)
    root = Path(args.output_dir).resolve()
    root.mkdir(parents=True, exist_ok=True)

    payload = asyncio.run(run())
    pkg = root / PACKAGE
    pkg.mkdir(parents=True, exist_ok=True)
    (pkg / f"{PACKAGE}.json").write_text(
        json.dumps(payload, ensure_ascii=False, indent=2, default=str), encoding="utf-8",
    )
    out = {
        "CHECKED_AT_MSK": payload["CHECKED_AT_MSK"],
        "SKU_837395782_TEMPORAL": payload["SKU_837395782_TEMPORAL"],
        "CANDIDATE_FBO_STOCK": payload["CANDIDATE_FBO_STOCK"],
        "NO_WRITES": payload["NO_WRITES"],
    }
    print(json.dumps(out, ensure_ascii=False, indent=2, default=str))
    return 0


if __name__ == "__main__":
    sys.exit(main())
