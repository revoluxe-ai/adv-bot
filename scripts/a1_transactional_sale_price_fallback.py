"""READ_ONLY: A1 transactional sale price fallback for CPO normalization (10% of totalPrice).

Использует non-cancelled supplier-order rows (поле totalPrice) за последние 28
закрытых MSK-дней — та же метрика, что STORE DRR denominator. Без writes.
"""

from __future__ import annotations

import argparse
import asyncio
import json
import statistics
import sys
from datetime import date, datetime, time, timedelta, timezone
from pathlib import Path
from typing import Any
from zoneinfo import ZoneInfo

import dotenv

dotenv.load_dotenv()

from scripts import ch_a1_evidence as evidence
from scripts.a1_cpc_two_sku_safety_preflight import _fetch_cards
from scripts.wb_a1_associated_conversions import _read_float, _read_int
from scripts.wb_api_readonly_ops.collect.api_budget import ApiCallBudget
from scripts.wb_api_readonly_ops.collect.jsonable import jsonable
from scripts.wb_api_readonly_ops.collect.orders_sales import _paginate_supplier_rows

SHOP_ID = evidence.SHOP_ID
MSK = ZoneInfo("Europe/Moscow")

TARGET_NMIDS = (
    85970344,
    770642983,
    14166423,
    837395782,
    7974113,
    14824677,
    4491664,
    7974106,
    7839837,
    4491663,
    13713289,
    4491650,
    147281596,
)

HIGHLIGHT_NMIDS = {14824677, 837395782}


def _msk_now() -> datetime:
    return datetime.now(timezone.utc).astimezone(MSK)


def _iso_msk(dt: datetime) -> str:
    return dt.astimezone(MSK).isoformat()


def _closed_end_day(now: datetime | None = None) -> date:
    """Последний полностью закрытый MSK-календарный день (вчера)."""
    today = (now or _msk_now()).date()
    return today - timedelta(days=1)


def _is_cancelled(row: dict[str, Any]) -> bool:
    return str(row.get("isCancel")).lower() in ("true", "1", "t")


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


def _in_closed_window(row: dict[str, Any], closed_end: date, days: int) -> bool:
    start = closed_end - timedelta(days=days - 1)
    start_dt = datetime.combine(start, time.min, tzinfo=MSK)
    end_dt = datetime.combine(closed_end + timedelta(days=1), time.min, tzinfo=MSK)
    dt = _msk_dt(row)
    return bool(dt and start_dt <= dt < end_dt)


def _nmid_rows(all_orders: list[dict[str, Any]], nmid: int) -> list[dict[str, Any]]:
    return [
        r
        for r in all_orders
        if _read_int(r, "nmId", "nm_id", "nmid") == nmid and not _is_cancelled(r)
    ]


def _median_total_price(rows: list[dict[str, Any]]) -> float | None:
    prices = [_read_float(r, "totalPrice") for r in rows]
    prices = [p for p in prices if p > 0]
    if not prices:
        return None
    return round(float(statistics.median(prices)), 2)


def _last_sale(rows: list[dict[str, Any]]) -> tuple[str | None, float | None]:
    dated: list[tuple[datetime, float]] = []
    for row in rows:
        dt = _msk_dt(row)
        tp = _read_float(row, "totalPrice")
        if dt is not None and tp > 0:
            dated.append((dt, tp))
    if not dated:
        return None, None
    dated.sort(key=lambda x: x[0], reverse=True)
    last_dt, last_tp = dated[0]
    return last_dt.date().isoformat(), round(last_tp, 2)


def _vendor_from_orders(rows: list[dict[str, Any]]) -> str | None:
    for row in sorted(rows, key=lambda r: str(_msk_dt(r) or ""), reverse=True):
        vc = row.get("supplierArticle") or row.get("vendorCode")
        if vc:
            return str(vc)
    return None


def _build_row(
    nmid: int,
    all_orders: list[dict[str, Any]],
    closed_end: date,
    vendor_code: str | None,
) -> dict[str, Any]:
    base = _nmid_rows(all_orders, nmid)
    w7 = [r for r in base if _in_closed_window(r, closed_end, 7)]
    w14 = [r for r in base if _in_closed_window(r, closed_end, 14)]
    w28 = [r for r in base if _in_closed_window(r, closed_end, 28)]

    last_date, last_tp = _last_sale(w28)
    med7 = _median_total_price(w7)
    med14 = _median_total_price(w14)
    med28 = _median_total_price(w28)

    sale_ref: float | None = None
    status = "OK"
    ref_rule = ""

    if len(w7) >= 3 and med7 is not None:
        sale_ref = med7
        ref_rule = "MEDIAN_TOTAL_PRICE_7D (>=3 rows)"
    elif len(w14) >= 3 and med14 is not None:
        sale_ref = med14
        ref_rule = "MEDIAN_TOTAL_PRICE_14D (>=3 rows)"
    elif len(w28) >= 1 and last_tp is not None:
        sale_ref = last_tp
        ref_rule = "LAST_SALE_TOTAL_PRICE (>=1 row in 28d)"
    else:
        status = "GAP_NO_RECENT_SALE"
        ref_rule = "no qualifying non-cancelled supplier-order rows in 28 closed days"

    age_days: int | None = None
    if last_date:
        age_days = (closed_end - date.fromisoformat(last_date)).days

    return {
        "nmID": nmid,
        "vendorCode": vendor_code or _vendor_from_orders(w28),
        "LAST_SALE_DATE": last_date,
        "LAST_SALE_TOTAL_PRICE": last_tp,
        "MEDIAN_TOTAL_PRICE_7D": med7,
        "MEDIAN_TOTAL_PRICE_14D": med14,
        "MEDIAN_TOTAL_PRICE_28D": med28,
        "ROW_COUNT_7D": len(w7),
        "ROW_COUNT_14D": len(w14),
        "ROW_COUNT_28D": len(w28),
        "SALE_PRICE_REFERENCE": sale_ref,
        "CPO_10_PERCENT": round(sale_ref * 0.10) if sale_ref is not None else None,
        "PRICE_REFERENCE_AGE_DAYS": age_days,
        "sale_price_reference_rule": ref_rule,
        "STATUS": status,
        "price_field": "totalPrice",
        "note": "unit-level supplier-order rows; PURCHASE_EVENTS not used for price reference",
    }


async def _fetch_orders(
    closed_end: date,
) -> tuple[list[dict[str, Any]], dict[str, Any], dict[int, str | None]]:
    from app.core.di.app_container import AppContainer
    from app.core.di.di_manager import DIManager

    date_from = (closed_end - timedelta(days=35)).isoformat()
    budget = ApiCallBudget(max_seconds=900.0, max_api_calls=1200)
    meta: dict[str, Any] = {
        "route": "GET /api/v1/supplier/orders",
        "date_from": date_from,
        "flag": 0,
        "pagination": "cursor via lastChangeDate",
        "price_field_authoritative": "totalPrice",
    }

    async with await DIManager.create(AppContainer) as container:  # type: ignore[attr-defined]
        factory = (
            container.module_resources.wb_manager_hub_factory_container.wb_manager_hub_factory()
        )
        hub = factory.get_wb_manager_hub(SHOP_ID)
        dm = hub.wb_data_manager
        products = dm.products_manager
        reports_manager = getattr(dm, "reports_manager", None)

        async def fetch_orders(df: str) -> list[object]:
            if reports_manager is not None:
                return list(await reports_manager.get_supplier_orders(date_from=df, flag=0) or [])
            return list(await dm.get_supplier_orders(date_from=df, flag=0) or [])

        result = await _paginate_supplier_rows(
            fetch=fetch_orders,
            initial_date_from=date_from,
            budget=budget,
            max_pages=1200,
        )
        rows: list[dict[str, Any]] = []
        for item in result.rows:
            d = jsonable(item)
            if isinstance(d, dict):
                rows.append(d)
        meta.update(
            {
                "api_calls": result.api_calls,
                "pagination_pages": result.pagination_pages,
                "raw_rows": len(rows),
            }
        )

        cards = await _fetch_cards(products, set(TARGET_NMIDS))
        vendor_by_nmid = {
            n: (cards.get(n) or {}).get("vendorCode") for n in TARGET_NMIDS
        }

    return rows, meta, vendor_by_nmid


async def run_snapshot() -> dict[str, Any]:
    checked_at = _msk_now()
    closed_end = _closed_end_day(checked_at)
    all_orders, orders_meta, vendor_by_nmid = await _fetch_orders(closed_end)

    rows = [
        _build_row(nmid, all_orders, closed_end, vendor_by_nmid.get(nmid))
        for nmid in TARGET_NMIDS
    ]

    return {
        "checked_at_msk": _iso_msk(checked_at),
        "shop_id": SHOP_ID,
        "mode": "STRICT_READ_ONLY",
        "kpi_contract": {
            "store_drr_denominator": "TOTAL_PRICE_VALUE = sum(totalPrice) non-cancelled supplier-order rows",
            "cpo_reference": "totalPrice per unit row (not priceWithDisc/finishedPrice/public card)",
        },
        "closed_day_end": closed_end.isoformat(),
        "closed_days_window": 28,
        "orders_meta": orders_meta,
        "rows": rows,
        "highlight": {
            str(n): next((r for r in rows if r.get("nmID") == n), {}) for n in HIGHLIGHT_NMIDS
        },
        "READ_ONLY": "CONFIRMED",
        "WB_API_WRITES": 0,
        "DB_WRITES": 0,
    }


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--output", default="")
    args = ap.parse_args(argv)

    payload = asyncio.run(run_snapshot())

    if args.output:
        Path(args.output).write_text(
            json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8"
        )

    print(json.dumps(payload, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
