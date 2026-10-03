"""READ_ONLY: SKU 837395782 bulk/purchase-event forensic (A1).

Проверяет структуру всплесков 29–30.08: independent events vs bulk checkout.
Без production mutations и causal ad claims.
"""

from __future__ import annotations

import argparse
import asyncio
import json
import sys
from collections import defaultdict
from datetime import datetime
from typing import Any
from zoneinfo import ZoneInfo

import dotenv

dotenv.load_dotenv()

from scripts.wb_a1_associated_conversions import _read_float, _read_int
from scripts.wb_api_readonly_ops.collect.api_budget import ApiCallBudget
from scripts.wb_api_readonly_ops.collect.orders_sales import _paginate_supplier_rows

SHOP_ID = "5339e9ad-cbfe-50fc-8d77-b9f337a80417"
MSK = ZoneInfo("Europe/Moscow")
TARGET_SKU = 837395782
SERIES_DAYS = ("2026-08-27", "2026-08-28", "2026-08-29", "2026-08-30")
FOCUS_DAYS = ("2026-08-29", "2026-08-30")

# Prior growth forensic: ad spend/clicks ~0 on 29–30.08 for this SKU contour.
AD_CONTEXT_29 = {"spend_rub": 0.0, "clicks": 0, "attributed_orders": 0}
AD_CONTEXT_30 = {"spend_rub": 0.0, "clicks": 0, "attributed_orders": 0}


def _order_day(row: dict[str, Any]) -> str:
    return str(row.get("date") or "")[:10]


def _lcd(row: dict[str, Any]) -> str:
    return str(row.get("lastChangeDate") or row.get("last_change_date") or "")


def _parse_ts(text: str) -> datetime | None:
    if not text or text.startswith("0001"):
        return None
    try:
        return datetime.fromisoformat(text.replace("Z", "+00:00")).astimezone(MSK)
    except ValueError:
        return None


def _g_key(row: dict[str, Any]) -> str:
    g = str(row.get("gNumber") or "").strip()
    return g if g else f"srid:{row.get('srid')}"


def _is_cancelled(row: dict[str, Any]) -> bool:
    v = row.get("isCancel")
    return str(v).lower() in ("true", "1", "t")


def _classify_bulk(rows: list[dict[str, Any]], by_g: dict[str, list[dict[str, Any]]]) -> str:
    if not rows:
        return "INCONCLUSIVE"
    n = len(rows)
    distinct_g = len(by_g)
    largest = max((len(v) for v in by_g.values()), default=0)
    if largest == n and distinct_g == 1 and n > 1:
        return "CONFIRMED"
    if largest >= 2 and distinct_g < n:
        bulk_units = sum(len(v) for v in by_g.values() if len(v) > 1)
        if bulk_units >= n * 0.5:
            return "CONFIRMED" if distinct_g <= 2 else "LIKELY"
        return "LIKELY"
    if distinct_g == n and largest == 1:
        return "NOT_SUPPORTED"
    return "INCONCLUSIVE"


def _day_analysis(rows: list[dict[str, Any]], day: str) -> dict[str, Any]:
    day_rows = [r for r in rows if _order_day(r) == day]
    by_g: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for r in day_rows:
        by_g[_g_key(r)].append(r)

    distinct_g = len(by_g)
    distinct_srid = len({str(r.get("srid")) for r in day_rows if r.get("srid")})
    multi_unit = sum(1 for members in by_g.values() if len(members) > 1)
    largest = max((len(v) for v in by_g.values()), default=0)
    bulk_units = sum(len(v) for v in by_g.values() if len(v) > 1)
    independent_events = sum(1 for v in by_g.values() if len(v) == 1)

    event_table: list[dict[str, Any]] = []
    value_by_group: list[dict[str, Any]] = []
    for gnum, members in sorted(by_g.items(), key=lambda x: -len(x[1])):
        ts_list = [_parse_ts(str(m.get("date") or "")) for m in members]
        ts_list = [t for t in ts_list if t]
        cancelled = sum(1 for m in members if _is_cancelled(m))
        region = members[0].get("regionName") or members[0].get("oblastOkrugName") or ""
        event_table.append(
            {
                "date": day,
                "gNumber": gnum,
                "units_order_rows": len(members),
                "first_timestamp": min(ts_list).isoformat() if ts_list else "",
                "last_timestamp": max(ts_list).isoformat() if ts_list else "",
                "region": region,
                "cancelled_units": cancelled,
            }
        )
        value_by_group.append(
            {
                "date": day,
                "gNumber": gnum,
                "units": len(members),
                "sum_totalPrice": round(sum(_read_float(m, "totalPrice") for m in members), 2),
                "sum_priceWithDisc": round(sum(_read_float(m, "priceWithDisc") for m in members), 2),
                "sum_finishedPrice": round(sum(_read_float(m, "finishedPrice") for m in members), 2),
            }
        )

    pattern = _classify_bulk(day_rows, by_g)
    return {
        "date": day,
        "RAW_ORDER_ROWS": len(day_rows),
        "DISTINCT_GNUMBER": distinct_g,
        "DISTINCT_SRID": distinct_srid,
        "DISTINCT_PURCHASE_EVENTS": distinct_g,
        "MULTI_UNIT_GROUPS": multi_unit,
        "LARGEST_GROUP_SIZE": largest,
        "BULK_PURCHASE_PATTERN": pattern,
        "units_in_bulk_groups": bulk_units,
        "units_in_single_unit_groups": len(day_rows) - bulk_units,
        "independent_purchase_events": independent_events,
        "PURCHASE_EVENT_TABLE": event_table,
        "VALUE_BY_PURCHASE_GROUP": value_by_group,
    }


def _extract_raw(row: dict[str, Any], n: int) -> dict[str, Any]:
    return {
        "row_num": n,
        "gNumber": row.get("gNumber", ""),
        "srid": row.get("srid", ""),
        "date": row.get("date", ""),
        "lastChangeDate": _lcd(row),
        "warehouseName": row.get("warehouseName", ""),
        "warehouseType": row.get("warehouseType", ""),
        "countryName": row.get("countryName", ""),
        "oblastOkrugName": row.get("oblastOkrugName", ""),
        "regionName": row.get("regionName", ""),
        "totalPrice": row.get("totalPrice", ""),
        "priceWithDisc": row.get("priceWithDisc", ""),
        "finishedPrice": row.get("finishedPrice", ""),
        "discountPercent": row.get("discountPercent", ""),
        "spp": row.get("spp", ""),
        "isCancel": row.get("isCancel", ""),
        "cancelDate": row.get("cancelDate", ""),
        "nmId": row.get("nmId", ""),
    }


def _store_purchase_events(all_rows: list[dict[str, Any]]) -> dict[str, Any]:
    out: dict[str, dict[str, int]] = {d: {"raw_rows": 0, "distinct_gNumber": 0} for d in SERIES_DAYS}
    by_day_g: dict[str, set[str]] = {d: set() for d in SERIES_DAYS}
    for row in all_rows:
        day = _order_day(row)
        if day not in SERIES_DAYS:
            continue
        out[day]["raw_rows"] += 1
        g = str(row.get("gNumber") or "").strip()
        if g:
            by_day_g[day].add(g)
    series: dict[str, dict[str, int]] = {}
    for d in SERIES_DAYS:
        series[d] = {
            "raw_order_rows": out[d]["raw_rows"],
            "distinct_gNumber": len(by_day_g[d]),
        }
    return {
        "STORE_PURCHASE_EVENT_SERIES": series,
        "STORE_PURCHASE_EVENTS": "AVAILABLE",
        "note": "distinct gNumber across all nmId in supplier orders by order date",
    }


def analyze(all_rows: list[dict[str, Any]], sku_rows: list[dict[str, Any]]) -> dict[str, Any]:
    checked = datetime.now(MSK)
    gaps: list[str] = ["no_quantity_field_in_supplier_orders_api"]

    units_series = {d: sum(1 for r in sku_rows if _order_day(r) == d) for d in SERIES_DAYS}
    purchase_event_series: dict[str, int] = {}
    units_per_event: dict[str, Any] = {}
    for d in SERIES_DAYS:
        day_rows = [r for r in sku_rows if _order_day(r) == d]
        gs = {_g_key(r) for r in day_rows}
        purchase_event_series[d] = len(gs)
        units_per_event[d] = (
            round(len(day_rows) / len(gs), 2) if gs else 0
        )

    day_29 = _day_analysis(sku_rows, "2026-08-29")
    day_30 = _day_analysis(sku_rows, "2026-08-30")
    store = _store_purchase_events(all_rows)

    # Store implication 29.08: prior claim 23→33 raw rows (+10), SKU 0→11 (+11)
    s28 = store["STORE_PURCHASE_EVENT_SERIES"]["2026-08-28"]
    s29 = store["STORE_PURCHASE_EVENT_SERIES"]["2026-08-29"]
    store_delta_rows = s29["raw_order_rows"] - s28["raw_order_rows"]
    store_delta_events = s29["distinct_gNumber"] - s28["distinct_gNumber"]
    sku_delta_rows = units_series["2026-08-29"] - units_series["2026-08-28"]
    sku_delta_events = (
        purchase_event_series["2026-08-29"] - purchase_event_series["2026-08-28"]
    )

    # Ad context — prior forensic, no re-collect
    ad_explains = "NOT_SUPPORTED"
    if day_29["BULK_PURCHASE_PATTERN"] in ("CONFIRMED", "LIKELY") or day_30["BULK_PURCHASE_PATTERN"] in (
        "CONFIRMED",
        "LIKELY",
    ):
        if AD_CONTEXT_29["clicks"] == 0 and AD_CONTEXT_30["clicks"] == 0:
            ad_explains = "NOT_SUPPORTED"

    raw_29_30 = [
        _extract_raw(r, i + 1)
        for i, r in enumerate(sku_rows)
        if _order_day(r) in FOCUS_DAYS
    ]

    interpretation_parts = []
    for label, day_data in [("29.08", day_29), ("30.08", day_30)]:
        interpretation_parts.append(
            f"{label}: {day_data['RAW_ORDER_ROWS']} raw rows = "
            f"{day_data['DISTINCT_PURCHASE_EVENTS']} purchase event(s), "
            f"{day_data['units_in_bulk_groups']} units in multi-unit groups, "
            f"pattern={day_data['BULK_PURCHASE_PATTERN']}."
        )
    interpretation = " ".join(interpretation_parts)
    interpretation += (
        f" Store 28→29: raw rows {s28['raw_order_rows']}→{s29['raw_order_rows']} "
        f"(Δ{store_delta_rows}), distinct gNumber {s28['distinct_gNumber']}→{s29['distinct_gNumber']} "
        f"(Δ{store_delta_events}). SKU units Δ{sku_delta_rows}, purchase events Δ{sku_delta_events}."
    )

    return {
        "SKU": TARGET_SKU,
        "PERIOD": "2026-08-29 → 2026-08-30 (series 27–30)",
        "29.08": {
            k: day_29[k]
            for k in (
                "RAW_ORDER_ROWS",
                "DISTINCT_PURCHASE_EVENTS",
                "MULTI_UNIT_GROUPS",
                "LARGEST_GROUP_SIZE",
                "BULK_PURCHASE_PATTERN",
                "units_in_bulk_groups",
                "independent_purchase_events",
            )
        },
        "30.08": {
            k: day_30[k]
            for k in (
                "RAW_ORDER_ROWS",
                "DISTINCT_PURCHASE_EVENTS",
                "MULTI_UNIT_GROUPS",
                "LARGEST_GROUP_SIZE",
                "BULK_PURCHASE_PATTERN",
                "units_in_bulk_groups",
                "independent_purchase_events",
            )
        },
        "29.08_DETAIL": day_29,
        "30.08_DETAIL": day_30,
        "UNITS_SERIES_27_30": units_series,
        "PURCHASE_EVENT_SERIES_27_30": purchase_event_series,
        "UNITS_PER_EVENT_SERIES": units_per_event,
        "STORE_PURCHASE_EVENTS": store,
        "STORE_28_TO_29_RECONCILIATION": {
            "prior_claim_store_raw_rows": "23 → 33 (+10)",
            "observed_store_raw_rows": f"{s28['raw_order_rows']} → {s29['raw_order_rows']} (Δ{store_delta_rows})",
            "observed_store_distinct_gNumber": f"{s28['distinct_gNumber']} → {s29['distinct_gNumber']} (Δ{store_delta_events})",
            "prior_claim_sku_raw_rows": "0 → 11 (+11)",
            "observed_sku_raw_rows": f"{units_series['2026-08-28']} → {units_series['2026-08-29']} (Δ{sku_delta_rows})",
            "observed_sku_distinct_purchase_events": (
                f"{purchase_event_series['2026-08-28']} → {purchase_event_series['2026-08-29']} "
                f"(Δ{sku_delta_events})"
            ),
        },
        "VALUE_BY_PURCHASE_GROUP": day_29["VALUE_BY_PURCHASE_GROUP"]
        + day_30["VALUE_BY_PURCHASE_GROUP"],
        "PURCHASE_EVENT_TABLE": day_29["PURCHASE_EVENT_TABLE"] + day_30["PURCHASE_EVENT_TABLE"],
        "CURRENT_ADS_EXPLAIN_BULK_EVENTS": ad_explains,
        "AD_CONTEXT_NOTE": "29–30.08 ad spend/clicks≈0 from prior A1-SKU-837395782-GROWTH-FORENSIC; not re-collected",
        "FINAL_INTERPRETATION": interpretation,
        "OPEN_GAPS": gaps,
        "CHECKED_AT_MSK": checked.strftime("%Y-%m-%d %H:%M:%S %Z"),
        "RAW_ORDER_RECORDS_29_30": raw_29_30,
    }


async def fetch_orders(date_from: str) -> list[dict[str, Any]]:
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
        reports_manager = getattr(dm, "reports_manager", None)
        budget = ApiCallBudget(max_seconds=900.0, max_api_calls=800)

        async def fetch(df: str) -> list[object]:
            if reports_manager is not None:
                return list(await reports_manager.get_supplier_orders(date_from=df, flag=0) or [])
            return list(await dm.get_supplier_orders(date_from=df, flag=0) or [])

        result = await _paginate_supplier_rows(
            fetch=fetch,
            initial_date_from=date_from,
            budget=budget,
            max_pages=800,
        )
        return result.rows
    finally:
        await httpx.shutdown()
        await redis_raw.aclose()


async def run(date_from: str) -> dict[str, Any]:
    all_rows = await fetch_orders(date_from)
    sku_rows = [r for r in all_rows if _read_int(r, "nmId", "nm_id", "nmid") == TARGET_SKU]
    return analyze(all_rows, sku_rows)


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--date-from", default="2026-08-27")
    args = ap.parse_args(argv)
    out = asyncio.run(run(args.date_from))
    print(json.dumps(out, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
