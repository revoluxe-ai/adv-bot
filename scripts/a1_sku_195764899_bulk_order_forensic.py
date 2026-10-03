"""READ_ONLY: SKU 195764899 bulk-order forensic for 2026-09-01 (A1).

Проверяет, являются ли 10 factual orders независимыми событиями или bulk/multi-unit.
Без production mutations.
"""

from __future__ import annotations

import argparse
import asyncio
import csv
import json
import sys
from collections import defaultdict
from datetime import datetime
from pathlib import Path
from typing import Any
from zoneinfo import ZoneInfo

import dotenv

dotenv.load_dotenv()

from scripts.wb_a1_associated_conversions import _read_float, _read_int
from scripts.wb_api_readonly_ops.collect.api_budget import ApiCallBudget
from scripts.wb_api_readonly_ops.collect.orders_sales import _paginate_supplier_rows

SHOP_ID = "5339e9ad-cbfe-50fc-8d77-b9f337a80417"
MSK = ZoneInfo("Europe/Moscow")
TARGET_SKU = 195764899
TARGET_DATE = "2026-09-01"

RAW_COLS = [
    "row_num",
    "srid",
    "gNumber",
    "date",
    "lastChangeDate",
    "warehouseName",
    "warehouseType",
    "countryName",
    "oblastOkrugName",
    "regionName",
    "supplierArticle",
    "nmId",
    "techSize",
    "totalPrice",
    "discountPercent",
    "spp",
    "priceWithDisc",
    "finishedPrice",
    "isCancel",
    "cancelDate",
    "sticker",
    "incomeID",
    "isSupply",
    "isRealization",
]


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


def _row_value_for_collector(row: dict[str, Any]) -> tuple[str, float]:
    """Mirror a1_sku_195764899_growth_forensic._agg_orders precedence."""
    for field in ("totalPrice", "finishedPrice", "priceWithDisc"):
        v = _read_float(row, field)
        if v > 0:
            return field, v
    return "none", 0.0


def _extract_raw_row(row: dict[str, Any], row_num: int) -> dict[str, Any]:
    out: dict[str, Any] = {"row_num": row_num}
    for c in RAW_COLS:
        if c == "row_num":
            continue
        out[c] = row.get(c, row.get(c.replace("ID", "Id"), ""))
    return out


def analyze(rows: list[dict[str, Any]]) -> dict[str, Any]:
    gaps: list[str] = []
    if not rows:
        gaps.append("no_matching_order_rows")

    srids = [str(r.get("srid") or "") for r in rows]
    gnums = [str(r.get("gNumber") or "") for r in rows if r.get("gNumber")]
    distinct_srid = len({s for s in srids if s})
    distinct_g = len(set(gnums)) if gnums else 0

    # Purchase groups: primary gNumber, fallback unique srid each
    group_key: list[str] = []
    for r in rows:
        g = str(r.get("gNumber") or "").strip()
        group_key.append(f"gNumber:{g}" if g else f"srid:{r.get('srid')}")
    distinct_groups = len(set(group_key))

    by_g: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for r in rows:
        g = str(r.get("gNumber") or "").strip() or f"srid:{r.get('srid')}"
        by_g[g].append(r)
    multi_unit_groups = sum(1 for members in by_g.values() if len(members) > 1)
    largest_group = max((len(v) for v in by_g.values()), default=0)

    dates = [_order_day(r) for r in rows]
    lcds = [_lcd(r) for r in rows]
    distinct_order_dates = len(set(dates))
    distinct_lcd_dates = len({x[:10] for x in lcds if x})
    date_vs_lcd_differs = any(
        _order_day(r) and _lcd(r) and _order_day(r) != _lcd(r)[:10] for r in rows
    )

    ts_order = [_parse_ts(_lcd(r)) or _parse_ts(str(r.get("date") or "")) for r in rows]
    ts_order = [t for t in ts_order if t]
    batch_arrival = "GAP"
    if len(ts_order) >= 2:
        span_sec = (max(ts_order) - min(ts_order)).total_seconds()
        if span_sec <= 60:
            batch_arrival = "YES"
        elif span_sec > 3600:
            batch_arrival = "NO"
        else:
            batch_arrival = "INCONCLUSIVE_SPAN"
    elif len(ts_order) == 1:
        batch_arrival = "YES"

    delayed = "GAP"
    if rows:
        if any(_order_day(r) != TARGET_DATE and _lcd(r)[:10] == TARGET_DATE for r in rows):
            delayed = "YES"
        elif all(_order_day(r) == TARGET_DATE for r in rows):
            delayed = "NO"
        else:
            delayed = "INCONCLUSIVE"

    # WB orders API: one row per unit; no quantity field
    has_qty_field = any("quantity" in r or "qty" in r for r in rows)
    if not has_qty_field:
        gaps.append("no_quantity_field_in_supplier_orders_api")

    # Classification
    if distinct_srid == len(rows) and distinct_groups == len(rows) and largest_group == 1:
        bulk_pattern = "NOT_SUPPORTED"
    elif largest_group >= 2 and distinct_groups < len(rows):
        if largest_group == len(rows) and distinct_groups == 1:
            bulk_pattern = "CONFIRMED"
        else:
            bulk_pattern = "LIKELY"
    elif distinct_groups == 1 and len(rows) > 1:
        bulk_pattern = "CONFIRMED"
    else:
        bulk_pattern = "INCONCLUSIVE"

    # Value semantics
    fields_used = [_row_value_for_collector(r) for r in rows]
    value_field = fields_used[0][0] if fields_used else "GAP"
    sum_values = round(sum(v for _, v in fields_used), 2)
    pwds = [_read_float(r, "priceWithDisc") for r in rows]
    avg_pwd = round(sum(pwds) / len(pwds), 2) if pwds else 0
    avg_row_val = round(sum_values / len(rows), 2) if rows else 0

    why_2656 = (
        f"Collector sums per-row value using first positive among "
        f"totalPrice→finishedPrice→priceWithDisc; for these rows primary field={value_field}. "
        f"avg per-row summed value={avg_row_val} (10×{avg_row_val}={sum_values}). "
        f"priceWithDisc={avg_pwd} is seller-discounted unit price before WB SPP/wallet; "
        f"totalPrice typically higher list price — forensic avg order value uses totalPrice when present."
    )

    client_hypothesis = (
        "Client wholesale hypothesis: if bulk, expect multiple units per gNumber group. "
    )
    if bulk_pattern in ("CONFIRMED", "LIKELY"):
        client_note = client_hypothesis + "Structure is consistent with multi-unit single checkout."
    elif bulk_pattern == "NOT_SUPPORTED":
        client_note = (
            client_hypothesis
            + f"Not supported: {distinct_srid} distinct srid / {distinct_groups} purchase groups for {len(rows)} rows."
        )
    else:
        client_note = client_hypothesis + "Inconclusive from available identifiers."

    interpretation = (
        f"{len(rows)} raw API rows, {distinct_srid} distinct srid, {distinct_groups} purchase group(s), "
        f"largest group size {largest_group}. "
    )
    if bulk_pattern == "NOT_SUPPORTED":
        interpretation += (
            "Each row is a separate WB order line (unique srid); API has no quantity>1 per row — "
            "consistent with 10 independent unit orders, not one multi-qty line."
        )
    elif bulk_pattern == "CONFIRMED":
        interpretation += "Multiple rows share purchase group identifier — consistent with one bulk checkout."
    else:
        interpretation += "Mixed or incomplete grouping evidence."

    return {
        "SKU": TARGET_SKU,
        "DATE": TARGET_DATE,
        "RAW_ORDER_ROWS": len(rows),
        "DISTINCT_SRID": distinct_srid,
        "DISTINCT_PURCHASE_GROUPS": distinct_groups,
        "MULTI_UNIT_GROUPS": multi_unit_groups,
        "LARGEST_GROUP_SIZE": largest_group,
        "BULK_PURCHASE_PATTERN": bulk_pattern,
        "FACTUAL_ORDER_VALUE_FIELD": value_field,
        "PRICE_WITH_DISC_FIELD": "priceWithDisc",
        "WHY_2656_VS_2284": why_2656,
        "VALUE_SEMANTICS": "ESTABLISHED" if rows else "GAP",
        "API_BATCH_ARRIVAL": batch_arrival,
        "ORDER_DATE_VS_CHANGE_DATE": {
            "all_order_date_eq_target": all(d == TARGET_DATE for d in dates) if rows else "GAP",
            "date_differs_from_lastChangeDate_day": date_vs_lcd_differs,
            "distinct_order_dates": distinct_order_dates,
            "distinct_lastChangeDate_days": distinct_lcd_dates,
            "sample_dates": dates,
            "sample_lastChangeDates": lcds,
        },
        "DELAYED_APPEARANCE_SUPPORTED": delayed,
        "CLIENT_WHOLESALE_HYPOTHESIS": client_note,
        "FINAL_INTERPRETATION": interpretation,
        "OPEN_GAPS": gaps,
        "raw_records": [_extract_raw_row(r, i + 1) for i, r in enumerate(rows)],
        "grouping_detail": {
            g: [str(m.get("srid")) for m in members] for g, members in by_g.items()
        },
        "timestamp_span_seconds": (
            round((max(ts_order) - min(ts_order)).total_seconds(), 1) if len(ts_order) >= 2 else 0
        ),
        "sum_factual_value_rub": sum_values,
        "avg_priceWithDisc": avg_pwd,
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
        budget = ApiCallBudget(max_seconds=600.0, max_api_calls=500)

        async def fetch(df: str) -> list[object]:
            if reports_manager is not None:
                return list(await reports_manager.get_supplier_orders(date_from=df, flag=0) or [])
            return list(await dm.get_supplier_orders(date_from=df, flag=0) or [])

        result = await _paginate_supplier_rows(
            fetch=fetch,
            initial_date_from=date_from,
            budget=budget,
            max_pages=500,
        )
        return result.rows
    finally:
        await httpx.shutdown()
        await redis_raw.aclose()


def _filter_target(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = []
    for row in rows:
        if _read_int(row, "nmId", "nm_id", "nmid") != TARGET_SKU:
            continue
        if _order_day(row) == TARGET_DATE:
            out.append(row)
    return out


async def run(date_from: str) -> dict[str, Any]:
    all_rows = await fetch_orders(date_from)
    matched = _filter_target(all_rows)
    return analyze(matched)


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--date-from", default="2026-08-30", help="orders API cursor start")
    ap.add_argument("--output-csv", default="")
    args = ap.parse_args(argv)
    out = asyncio.run(run(args.date_from))
    raw = out.pop("raw_records", [])
    grouping = out.pop("grouping_detail", {})
    out["GROUPING_DETAIL"] = grouping
    if args.output_csv:
        p = Path(args.output_csv)
        p.parent.mkdir(parents=True, exist_ok=True)
        with p.open("w", encoding="utf-8", newline="") as f:
            w = csv.DictWriter(f, fieldnames=RAW_COLS, extrasaction="ignore")
            w.writeheader()
            for row in raw:
                w.writerow(row)
        out["RAW_CSV_PATH"] = str(p.resolve())
    out["RAW_TABLE"] = raw
    print(json.dumps(out, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
