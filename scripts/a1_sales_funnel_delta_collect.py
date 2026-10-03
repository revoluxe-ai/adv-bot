"""READ_ONLY Sales Funnel delta collector for WB shop ООО «А1».

Дополняет A1_BASELINE_V0 пакет business-level denominator из WB Sales Funnel:
orderCount / orderSum и funnel metrics по nmID и store (day grain).

Стратегия API (без второго collector pipeline):
- POST /api/analytics/v3/sales-funnel/products/history — daily nm×day, только last 7 days;
- POST /api/analytics/v3/sales-funnel/products — daily nm×day и store totals для дней
  старше 7-дневного history window (до 365d per swagger).

Режим STRICT_READ_ONLY: только read endpoints WB API + PG identity (nmIDs).
"""

from __future__ import annotations

import argparse
import ast
import asyncio
import csv
import hashlib
import json
import os
import sys
import zipfile
from collections import defaultdict
from datetime import date, datetime, timedelta
from pathlib import Path
from typing import Any, cast

import dotenv

dotenv.load_dotenv()

from scripts import ch_a1_evidence as evidence

SHOP_ID = evidence.SHOP_ID
TZ = "Europe/Moscow"
PRIMARY_FROM = date(2026, 8, 11)
PRIMARY_TO = date(2026, 8, 24)
CONTEXT_FROM = date(2026, 7, 29)
CONTEXT_TO = date(2026, 8, 10)
OPEN_DAY = date(2026, 8, 25)
COLLECT_FROM = CONTEXT_FROM
COLLECT_TO = OPEN_DAY
FUNNEL_HISTORY_MAX_DAYS = 7
NMID_BATCH_SIZE = 20
PRODUCTS_PAGE_LIMIT = 100
API_MIN_INTERVAL_SEC = 21.0
HISTORY_ENDPOINT = "/api/analytics/v3/sales-funnel/products/history"
PRODUCTS_ENDPOINT = "/api/analytics/v3/sales-funnel/products"

NM_DAILY_COLUMNS = [
    "date",
    "nm_id",
    "open_card",
    "add_to_cart",
    "order_count",
    "order_sum",
    "buyout_count",
    "buyout_sum",
    "cancel_count",
    "cancel_sum",
    "period_state",
    "source",
]
STORE_DAILY_COLUMNS = [
    "date",
    "open_card",
    "add_to_cart",
    "order_count",
    "order_sum",
    "buyout_count",
    "buyout_sum",
    "cancel_count",
    "cancel_sum",
    "period_state",
    "source",
]


def period_state(day: date) -> str:
    """Маркировка CONTEXT / PRIMARY_CLOSED / OPEN_DAY."""
    if day == OPEN_DAY:
        return "OPEN_DAY"
    if PRIMARY_FROM <= day <= PRIMARY_TO:
        return "PRIMARY_CLOSED"
    if CONTEXT_FROM <= day <= CONTEXT_TO:
        return "CONTEXT"
    return "OUT_OF_SCOPE"


def _date_range(start: date, end: date) -> list[date]:
    days: list[date] = []
    current = start
    while current <= end:
        days.append(current)
        current += timedelta(days=1)
    return days


def _chunks(items: list[int], size: int) -> list[list[int]]:
    return [items[i : i + size] for i in range(0, len(items), size)]


def _serialize(value: Any) -> str:
    if value is None:
        return ""
    if isinstance(value, (dict, list)):
        return json.dumps(value, ensure_ascii=False, default=str)
    return str(value)


def _write_csv(path: Path, rows: list[dict[str, Any]], columns: list[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=columns, extrasaction="ignore")
        writer.writeheader()
        for row in rows:
            writer.writerow({col: _serialize(row.get(col)) for col in columns})


def _pg_database() -> str:
    """Имя PG database из env кластера или adv_updater по умолчанию."""
    return os.environ.get("POSTGRES_DBNAME") or "adv_updater"


def _bootstrap_pg_credentials_from_env() -> bool:
    user = os.environ.get("POSTGRES_USER")
    password = os.environ.get("POSTGRES_PASSWORD")
    if not user or not password:
        return False
    evidence._PG_CREDENTIALS = user, password
    return True


def _bootstrap_cluster_infra() -> None:
    """Переключить PG/CH endpoints на in-cluster env из Job secrets."""
    _bootstrap_pg_credentials_from_env()
    pg_host = os.environ.get("POSTGRES_MASTER_HOST") or os.environ.get("POSTGRES_REPLICA_HOST")
    pg_port = os.environ.get("POSTGRES_PORT")
    if pg_host:
        evidence.PG_EXTERNAL_HOST = pg_host
    if pg_port:
        evidence.PG_EXTERNAL_PORT = int(pg_port)


def _load_nmids_from_pg(root: Path) -> tuple[int, list[int]]:
    """Загрузить nmIDs из advsetting по shop_id (как baseline V0)."""
    sql_dir = root / "sql"
    staging = root / "staging"
    staging.mkdir(parents=True, exist_ok=True)
    cabinet_path = staging / "wbcabinet.csv"
    status = evidence.run_pg_query(
        _pg_database(),
        (
            "SELECT id FROM public.wbcabinet WHERE shop_id = "
            f"'{SHOP_ID}'"
        ),
        cabinet_path,
        sql_dir / "pg_wbcabinet.sql",
        csv_output=True,
    )
    if not status["success"]:
        raise RuntimeError(f"wbcabinet query failed: {status['stderr']}")
    cabinet_ids: list[int] = []
    with cabinet_path.open(encoding="utf-8", newline="") as handle:
        for row in csv.DictReader(handle):
            if row.get("id"):
                cabinet_ids.append(int(row["id"]))
    if not cabinet_ids:
        raise RuntimeError(f"No wbcabinet for shop_id={SHOP_ID}")
    wb_cabinet_id = cabinet_ids[0]
    ids_sql = ", ".join(str(v) for v in sorted(cabinet_ids))
    setting_path = staging / "advsetting.csv"
    st = evidence.run_pg_query(
        _pg_database(),
        f"SELECT nmids FROM public.advsetting WHERE wb_cabinet_id IN ({ids_sql})",
        setting_path,
        sql_dir / "pg_advsetting_nmids.sql",
        csv_output=True,
    )
    if not st["success"]:
        raise RuntimeError(f"advsetting query failed: {st['stderr']}")
    nmids: set[int] = set()
    with setting_path.open(encoding="utf-8", newline="") as handle:
        for row in csv.DictReader(handle):
            try:
                parsed = ast.literal_eval(row.get("nmids") or "[]")
            except (ValueError, SyntaxError):
                parsed = []
            if isinstance(parsed, list):
                for v in parsed:
                    if str(v).isdigit():
                        nmids.add(int(v))
    return wb_cabinet_id, sorted(nmids)


def _history_window_end() -> date:
    return COLLECT_TO


def _history_window_start() -> date:
    end = _history_window_end()
    return end - timedelta(days=FUNNEL_HISTORY_MAX_DAYS - 1)


def _products_only_days() -> list[date]:
    hist_start = _history_window_start()
    return [d for d in _date_range(COLLECT_FROM, COLLECT_TO) if d < hist_start]


def _nm_row_from_history(
    nmid: int,
    day: date,
    hist: dict[str, Any],
) -> dict[str, Any]:
    return {
        "date": day.isoformat(),
        "nm_id": nmid,
        "open_card": hist.get("openCount", hist.get("open_count", 0)),
        "add_to_cart": hist.get("cartCount", hist.get("cart_count", 0)),
        "order_count": hist.get("orderCount", hist.get("order_count", 0)),
        "order_sum": hist.get("orderSum", hist.get("order_sum", 0)),
        "buyout_count": hist.get("buyoutCount", hist.get("buyout_count", 0)),
        "buyout_sum": hist.get("buyoutSum", hist.get("buyout_sum", 0)),
        "cancel_count": hist.get("cancelCount", hist.get("cancel_count", 0)),
        "cancel_sum": hist.get("cancelSum", hist.get("cancel_sum", 0)),
        "period_state": period_state(day),
        "source": HISTORY_ENDPOINT,
    }


def _nm_row_from_products_stat(
    nmid: int,
    day: date,
    selected: dict[str, Any],
) -> dict[str, Any]:
    return {
        "date": day.isoformat(),
        "nm_id": nmid,
        "open_card": selected.get("openCount", 0),
        "add_to_cart": selected.get("cartCount", 0),
        "order_count": selected.get("orderCount", 0),
        "order_sum": selected.get("orderSum", 0),
        "buyout_count": selected.get("buyoutCount", 0),
        "buyout_sum": selected.get("buyoutSum", 0),
        "cancel_count": selected.get("cancelCount", 0),
        "cancel_sum": selected.get("cancelSum", 0),
        "period_state": period_state(day),
        "source": PRODUCTS_ENDPOINT,
    }


def _aggregate_store(rows: list[dict[str, Any]], source: str) -> list[dict[str, Any]]:
    """Агрегировать nm daily в store daily (сумма promoted nmIDs)."""
    by_day: dict[str, dict[str, Any]] = defaultdict(
        lambda: {
            "open_card": 0,
            "add_to_cart": 0,
            "order_count": 0,
            "order_sum": 0,
            "buyout_count": 0,
            "buyout_sum": 0,
            "cancel_count": 0,
            "cancel_sum": 0,
        }
    )
    for row in rows:
        day = row["date"]
        bucket = by_day[day]
        bucket["open_card"] += int(row.get("open_card") or 0)
        bucket["add_to_cart"] += int(row.get("add_to_cart") or 0)
        bucket["order_count"] += int(row.get("order_count") or 0)
        bucket["order_sum"] += int(row.get("order_sum") or 0)
        bucket["buyout_count"] += int(row.get("buyout_count") or 0)
        bucket["buyout_sum"] += int(row.get("buyout_sum") or 0)
        bucket["cancel_count"] += int(row.get("cancel_count") or 0)
        bucket["cancel_sum"] += int(row.get("cancel_sum") or 0)
    store_rows: list[dict[str, Any]] = []
    for day_str in sorted(by_day):
        day = date.fromisoformat(day_str)
        bucket = by_day[day_str]
        store_rows.append(
            {
                "date": day_str,
                "open_card": bucket["open_card"],
                "add_to_cart": bucket["add_to_cart"],
                "order_count": bucket["order_count"],
                "order_sum": bucket["order_sum"],
                "buyout_count": bucket["buyout_count"],
                "buyout_sum": bucket["buyout_sum"],
                "cancel_count": bucket["cancel_count"],
                "cancel_sum": bucket["cancel_sum"],
                "period_state": period_state(day),
                "source": f"{source}:nm_sum",
            }
        )
    return store_rows


async def _throttle(last_call: float) -> float:
    elapsed = asyncio.get_event_loop().time() - last_call
    if elapsed < API_MIN_INTERVAL_SEC:
        await asyncio.sleep(API_MIN_INTERVAL_SEC - elapsed)
    return asyncio.get_event_loop().time()


async def _collect_sales_funnel(
    nmids: list[int],
    raw_dir: Path,
    coverage: dict[str, Any],
) -> list[dict[str, Any]]:
    """Собрать nm×day через history (last 7d) + products (older days)."""
    from app.core.di.app_container import AppContainer
    from app.core.di.di_manager import DIManager
    from app.core.mp.wb.api.adapter.raise_errors import with_raise_errors
    from app.core.mp.wb.api.generated.analitika_i_dannye_client.api.voronka_prodazh.post_sales_funnel_products import (
        asyncio_detailed as products_asyncio_detailed,
    )
    from app.core.mp.wb.api.generated.analitika_i_dannye_client.models import ProductsRequest
    from app.core.mp.wb.api.generated.analitika_i_dannye_client.models.products_request_selected_period import (
        ProductsRequestSelectedPeriod,
    )
    from app.core.mp.wb.api.generated.analitika_i_dannye_client.types import UNSET

    nm_daily: list[dict[str, Any]] = []
    store_all_seller: dict[str, dict[str, int]] = defaultdict(
        lambda: {
            "open_card": 0,
            "add_to_cart": 0,
            "order_count": 0,
            "order_sum": 0,
            "buyout_count": 0,
            "buyout_sum": 0,
            "cancel_count": 0,
            "cancel_sum": 0,
        }
    )
    api_calls = 0
    errors: list[str] = []
    last_ts = 0.0

    async with await DIManager.create(AppContainer) as container:  # type: ignore[attr-defined]
        factory = container.module_resources.wb_manager_hub_factory_container.wb_manager_hub_factory()
        hub = factory.get_wb_manager_hub(SHOP_ID)
        dm = hub.wb_data_manager
        analytics_mgr = dm._analytics_manager
        analytic_client = analytics_mgr._AnalyticsManager__wb_api_client
        funnel_adapter = analytic_client.sales_funnel_adapter
        auth_client = await funnel_adapter.auth_client_handler.get_proxy_client(funnel_adapter)

        products_days = _products_only_days()
        hist_start = _history_window_start()
        hist_end = _history_window_end()

        # --- products/history: last 7 days ---
        history_raw_path = raw_dir / "history_batches.jsonl"
        with history_raw_path.open("w", encoding="utf-8") as hist_handle:
            for batch in _chunks(nmids, NMID_BATCH_SIZE):
                last_ts = await _throttle(last_ts)
                api_calls += 1
                try:
                    batch_rows = await dm.get_sales_funnel_products_history(
                        nmids=batch,
                        start=hist_start,
                        end=hist_end,
                    )
                except Exception as exc:  # noqa: BLE001
                    errors.append(
                        f"history {hist_start}..{hist_end} batch={len(batch)}: "
                        f"{type(exc).__name__}: {exc}"
                    )
                    continue
                payload = {
                    "endpoint": HISTORY_ENDPOINT,
                    "start": hist_start.isoformat(),
                    "end": hist_end.isoformat(),
                    "nm_ids": batch,
                    "rows": [
                        {
                            "nmid": r.nmid,
                            "day": r.day.isoformat(),
                            "open_card": r.open_card,
                            "add_to_cart": r.add_to_cart,
                            "orders": r.orders,
                            "orders_sum": r.orders_sum,
                            "buy_outs": r.buy_outs,
                            "buyouts_sum_rub": r.buyouts_sum_rub,
                        }
                        for r in batch_rows or []
                    ],
                }
                hist_handle.write(json.dumps(payload, ensure_ascii=False) + "\n")
                for row in batch_rows or []:
                    nm_daily.append(
                        {
                            "date": row.day.isoformat(),
                            "nm_id": row.nmid,
                            "open_card": row.open_card,
                            "add_to_cart": row.add_to_cart,
                            "order_count": row.orders,
                            "order_sum": int(row.orders_sum),
                            "buyout_count": row.buy_outs,
                            "buyout_sum": int(row.buyouts_sum_rub),
                            "cancel_count": 0,
                            "cancel_sum": 0,
                            "period_state": period_state(row.day),
                            "source": HISTORY_ENDPOINT,
                        }
                    )

        # --- products: daily windows before history window ---
        products_raw_path = raw_dir / "products_batches.jsonl"
        with products_raw_path.open("w", encoding="utf-8") as prod_handle:
            for day in products_days:
                # promoted nmIDs batches
                for batch in _chunks(nmids, NMID_BATCH_SIZE):
                    last_ts = await _throttle(last_ts)
                    api_calls += 1
                    period = ProductsRequestSelectedPeriod(start=day, end=day)
                    body = ProductsRequest(
                        selected_period=period,
                        nm_ids=batch,
                        limit=PRODUCTS_PAGE_LIMIT,
                        offset=0,
                    )
                    try:
                        response = await with_raise_errors(
                            products_asyncio_detailed,
                            auth_client,
                            body=body,
                        )
                    except Exception as exc:  # noqa: BLE001
                        errors.append(
                            f"products nm {day} batch={len(batch)}: "
                            f"{type(exc).__name__}: {exc}"
                        )
                        continue
                    parsed = response.parsed
                    raw_products: list[dict[str, Any]] = []
                    if parsed is not None and parsed.data is not None:
                        for item in parsed.data.products:
                            raw_products.append(item.to_dict())
                            nmid = item.product.nm_id
                            selected = item.statistic.selected.to_dict()
                            nm_daily.append(
                                _nm_row_from_products_stat(nmid, day, selected)
                            )
                    prod_handle.write(
                        json.dumps(
                            {
                                "endpoint": PRODUCTS_ENDPOINT,
                                "day": day.isoformat(),
                                "scope": "nm_batch",
                                "nm_ids": batch,
                                "products": raw_products,
                            },
                            ensure_ascii=False,
                        )
                        + "\n"
                    )

                # full seller store totals (paginated, nm_ids unset)
                offset = 0
                day_store = defaultdict(int)
                pages = 0
                while True:
                    last_ts = await _throttle(last_ts)
                    api_calls += 1
                    pages += 1
                    period = ProductsRequestSelectedPeriod(start=day, end=day)
                    body = ProductsRequest(
                        selected_period=period,
                        nm_ids=UNSET,
                        limit=PRODUCTS_PAGE_LIMIT,
                        offset=offset,
                    )
                    try:
                        response = await with_raise_errors(
                            products_asyncio_detailed,
                            auth_client,
                            body=body,
                        )
                    except Exception as exc:  # noqa: BLE001
                        errors.append(
                            f"products store {day} offset={offset}: "
                            f"{type(exc).__name__}: {exc}"
                        )
                        break
                    parsed = response.parsed
                    if parsed is None or parsed.data is None:
                        break
                    batch_products = parsed.data.products
                    if not batch_products:
                        break
                    page_raw: list[dict[str, Any]] = []
                    for item in batch_products:
                        page_raw.append(item.to_dict())
                        sel = item.statistic.selected
                        day_store["open_card"] += sel.open_count
                        day_store["add_to_cart"] += sel.cart_count
                        day_store["order_count"] += sel.order_count
                        day_store["order_sum"] += sel.order_sum
                        day_store["buyout_count"] += sel.buyout_count
                        day_store["buyout_sum"] += sel.buyout_sum
                        day_store["cancel_count"] += sel.cancel_count
                        day_store["cancel_sum"] += sel.cancel_sum
                    prod_handle.write(
                        json.dumps(
                            {
                                "endpoint": PRODUCTS_ENDPOINT,
                                "day": day.isoformat(),
                                "scope": "store_all",
                                "offset": offset,
                                "products": page_raw,
                            },
                            ensure_ascii=False,
                        )
                        + "\n"
                    )
                    if len(batch_products) < PRODUCTS_PAGE_LIMIT:
                        break
                    offset += PRODUCTS_PAGE_LIMIT

                store_all_seller[day.isoformat()] = dict(day_store)

        # store totals for history window days: paginate all seller products per day
        history_days = _date_range(hist_start, hist_end)
        with products_raw_path.open("a", encoding="utf-8") as prod_handle:
            for day in history_days:
                offset = 0
                day_store = defaultdict(int)
                while True:
                    last_ts = await _throttle(last_ts)
                    api_calls += 1
                    period = ProductsRequestSelectedPeriod(start=day, end=day)
                    body = ProductsRequest(
                        selected_period=period,
                        nm_ids=UNSET,
                        limit=PRODUCTS_PAGE_LIMIT,
                        offset=offset,
                    )
                    try:
                        response = await with_raise_errors(
                            products_asyncio_detailed,
                            auth_client,
                            body=body,
                        )
                    except Exception as exc:  # noqa: BLE001
                        errors.append(
                            f"products store hist-window {day} offset={offset}: "
                            f"{type(exc).__name__}: {exc}"
                        )
                        break
                    parsed = response.parsed
                    if parsed is None or parsed.data is None:
                        break
                    batch_products = parsed.data.products
                    if not batch_products:
                        break
                    page_raw: list[dict[str, Any]] = []
                    for item in batch_products:
                        page_raw.append(item.to_dict())
                        sel = item.statistic.selected
                        day_store["open_card"] += sel.open_count
                        day_store["add_to_cart"] += sel.cart_count
                        day_store["order_count"] += sel.order_count
                        day_store["order_sum"] += sel.order_sum
                        day_store["buyout_count"] += sel.buyout_count
                        day_store["buyout_sum"] += sel.buyout_sum
                        day_store["cancel_count"] += sel.cancel_count
                        day_store["cancel_sum"] += sel.cancel_sum
                    prod_handle.write(
                        json.dumps(
                            {
                                "endpoint": PRODUCTS_ENDPOINT,
                                "day": day.isoformat(),
                                "scope": "store_all_hist_window",
                                "offset": offset,
                                "products": page_raw,
                            },
                            ensure_ascii=False,
                        )
                        + "\n"
                    )
                    if len(batch_products) < PRODUCTS_PAGE_LIMIT:
                        break
                    offset += PRODUCTS_PAGE_LIMIT
                store_all_seller[day.isoformat()] = dict(day_store)

    coverage["api_calls"] = api_calls
    coverage["errors"] = errors[:50]
    coverage["history_window"] = [hist_start.isoformat(), hist_end.isoformat()]
    coverage["products_days"] = [d.isoformat() for d in products_days]
    coverage["store_all_seller_days"] = sorted(store_all_seller.keys())
    coverage["nm_daily_rows"] = len(nm_daily)

    store_rows_from_api: list[dict[str, Any]] = []
    for day_str, bucket in sorted(store_all_seller.items()):
        day = date.fromisoformat(day_str)
        store_rows_from_api.append(
            {
                "date": day_str,
                "open_card": bucket.get("open_card", 0),
                "add_to_cart": bucket.get("add_to_cart", 0),
                "order_count": bucket.get("order_count", 0),
                "order_sum": bucket.get("order_sum", 0),
                "buyout_count": bucket.get("buyout_count", 0),
                "buyout_sum": bucket.get("buyout_sum", 0),
                "cancel_count": bucket.get("cancel_count", 0),
                "cancel_sum": bucket.get("cancel_sum", 0),
                "period_state": period_state(day),
                "source": f"{PRODUCTS_ENDPOINT}:store_all_paginated",
            }
        )

    coverage["store_rows_from_api"] = store_rows_from_api
    return nm_daily


def _reconcile(
    nm_daily: list[dict[str, Any]],
    store_nm_sum: list[dict[str, Any]],
    store_api: list[dict[str, Any]],
) -> dict[str, Any]:
    """Сравнить сумму promoted nmIDs с store API totals."""
    nm_by_day: dict[str, dict[str, int]] = defaultdict(
        lambda: {"order_count": 0, "order_sum": 0}
    )
    for row in nm_daily:
        nm_by_day[row["date"]]["order_count"] += int(row.get("order_count") or 0)
        nm_by_day[row["date"]]["order_sum"] += int(row.get("order_sum") or 0)

    api_by_day = {r["date"]: r for r in store_api}
    nm_sum_by_day = {r["date"]: r for r in store_nm_sum}
    mismatches: list[dict[str, Any]] = []
    for day in sorted(set(nm_by_day) | set(api_by_day)):
        nm_sum = nm_sum_by_day.get(day, {})
        api = api_by_day.get(day, {})
        promoted_orders = int(nm_sum.get("order_count") or nm_by_day[day]["order_count"])
        promoted_sum = int(nm_sum.get("order_sum") or nm_by_day[day]["order_sum"])
        store_orders = int(api.get("order_count") or 0)
        store_sum = int(api.get("order_sum") or 0)
        if store_orders and promoted_orders > store_orders:
            mismatches.append(
                {
                    "date": day,
                    "issue": "promoted_nm_sum_exceeds_store_api",
                    "promoted_order_count": promoted_orders,
                    "store_api_order_count": store_orders,
                }
            )
        if store_sum and promoted_sum > store_sum:
            mismatches.append(
                {
                    "date": day,
                    "issue": "promoted_nm_sum_exceeds_store_api_sum",
                    "promoted_order_sum": promoted_sum,
                    "store_api_order_sum": store_sum,
                }
            )
    return {
        "promoted_nm_vs_store_api_mismatches": mismatches,
        "status": "OK" if not mismatches else "WARN",
    }


def _coverage_quality_md(
    wb_cabinet_id: int,
    nmids: list[int],
    nm_daily: list[dict[str, Any]],
    store_nm_sum: list[dict[str, Any]],
    store_api: list[dict[str, Any]],
    coverage: dict[str, Any],
    reconcile: dict[str, Any],
) -> str:
    all_days = _date_range(COLLECT_FROM, COLLECT_TO)
    primary_days = _date_range(PRIMARY_FROM, PRIMARY_TO)
    nm_days_covered = {r["date"] for r in nm_daily}
    primary_covered = [d.isoformat() for d in primary_days if d.isoformat() in nm_days_covered]
    primary_missing = [
        d.isoformat() for d in primary_days if d.isoformat() not in nm_days_covered
    ]
    nm_with_data = {int(r["nm_id"]) for r in nm_daily}
    nm_missing = [n for n in nmids if n not in nm_with_data]

    primary_order_count = sum(
        int(r.get("order_count") or 0)
        for r in nm_daily
        if PRIMARY_FROM.isoformat() <= r["date"] <= PRIMARY_TO.isoformat()
    )
    primary_order_sum = sum(
        int(r.get("order_sum") or 0)
        for r in nm_daily
        if PRIMARY_FROM.isoformat() <= r["date"] <= PRIMARY_TO.isoformat()
    )

    lines = [
        "# Sales Funnel Coverage and Quality — A1",
        "",
        f"- shop_id: `{SHOP_ID}`",
        f"- wb_cabinet_id: `{wb_cabinet_id}`",
        f"- timezone: `{TZ}`",
        "",
        "## Endpoints",
        f"- nm daily (last 7d): `{HISTORY_ENDPOINT}`",
        f"- nm daily (older) + store all-seller: `{PRODUCTS_ENDPOINT}` (swagger max 365d)",
        "",
        "## Request windows",
        f"- collect range: `{COLLECT_FROM}` .. `{COLLECT_TO}`",
        f"- history API window: `{coverage.get('history_window')}`",
        f"- products-only days: `{len(coverage.get('products_days', []))}` days "
        f"({(coverage.get('products_days') or [])[:3]}…)",
        "",
        "## API limits",
        "- history: max last 7 days (swagger)",
        "- products: max 365 days; rate limit 3 req/min / 20s interval",
        f"- pacing: `{API_MIN_INTERVAL_SEC}s` between calls",
        f"- api_calls total: `{coverage.get('api_calls')}`",
        f"- nmID batch size: `{NMID_BATCH_SIZE}`",
        f"- products page limit: `{PRODUCTS_PAGE_LIMIT}`",
        "",
        "## Pagination",
        "- products store totals: offset/limit pagination until short page",
        "- products nm batches: single page per batch (≤100 nm per request)",
        "",
        "## Coverage",
        f"- nmIDs requested (advsetting): `{len(nmids)}`",
        f"- nmIDs with any funnel row: `{len(nm_with_data)}`",
        f"- nmIDs missing: `{nm_missing[:20]}{'…' if len(nm_missing) > 20 else ''}`",
        f"- calendar days in range: `{len(all_days)}`",
        f"- days with nm data: `{len(nm_days_covered)}`",
        f"- PRIMARY_BASELINE days covered: `{len(primary_covered)}/{len(primary_days)}`",
        f"- PRIMARY missing days: `{primary_missing}`",
        "",
        "## Period semantics",
        "- CONTEXT: 2026-07-29..2026-08-10",
        "- PRIMARY_CLOSED: 2026-08-11..2026-08-24",
        "- OPEN_DAY: 2026-08-25 (may still mature)",
        "",
        "## PRIMARY totals (promoted nm sum)",
        f"- orderCount 11–24.08: `{primary_order_count}`",
        f"- orderSum 11–24.08: `{primary_order_sum}`",
        "",
        "## Reconciliation",
        f"- status: `{reconcile.get('status')}`",
        f"- promoted nm sum vs store API paginated: "
        f"`{len(reconcile.get('promoted_nm_vs_store_api_mismatches', []))}` mismatches",
        "",
        "## Unavailable / GAP",
        "- history endpoint: no cancelCount/cancelSum in CH mapper; history rows carry cancel=0",
        "- organic split: NOT provided by endpoint (not emitted)",
        "- days before history window rely on products single-day periods (not history CSV/Jam)",
        "",
        "## Errors (sample)",
    ]
    for err in coverage.get("errors") or []:
        lines.append(f"- {err}")
    if not coverage.get("errors"):
        lines.append("- none")
    return "\n".join(lines) + "\n"


async def run_collect(
    output_dir: Path,
    wb_cabinet_id: int,
    nmids: list[int],
) -> dict[str, Any]:
    """Выполнить delta-collect и упаковать ZIP."""
    output_dir.mkdir(parents=True, exist_ok=True)
    raw_dir = output_dir / "raw"
    raw_dir.mkdir(parents=True, exist_ok=True)
    sql_dir = output_dir / "sql"
    sql_dir.mkdir(parents=True, exist_ok=True)

    coverage: dict[str, Any] = {
        "timezone": TZ,
        "nmids_requested": len(nmids),
    }

    nm_daily = await _collect_sales_funnel(nmids, raw_dir, coverage)
    store_nm_sum = _aggregate_store(nm_daily, "promoted_nm_sum")
    store_api = coverage.get("store_rows_from_api") or []

    _write_csv(output_dir / "01_SALES_FUNNEL_NM_DAILY.csv", nm_daily, NM_DAILY_COLUMNS)
    # store: prefer full-seller API totals when present, else nm sum
    store_out = store_api if store_api else store_nm_sum
    _write_csv(output_dir / "02_SALES_FUNNEL_STORE_DAILY.csv", store_out, STORE_DAILY_COLUMNS)

    reconcile = _reconcile(nm_daily, store_nm_sum, store_api)
    (output_dir / "03_COVERAGE_AND_QUALITY.md").write_text(
        _coverage_quality_md(
            wb_cabinet_id, nmids, nm_daily, store_nm_sum, store_api, coverage, reconcile
        ),
        encoding="utf-8",
    )

    primary_order_count = sum(
        int(r.get("order_count") or 0)
        for r in nm_daily
        if PRIMARY_FROM.isoformat() <= r["date"] <= PRIMARY_TO.isoformat()
    )
    primary_order_sum = sum(
        int(r.get("order_sum") or 0)
        for r in nm_daily
        if PRIMARY_FROM.isoformat() <= r["date"] <= PRIMARY_TO.isoformat()
    )

    manifest = {
        "artifact": "a1_sales_funnel_delta",
        "created_at": datetime.now().isoformat(),
        "shop_id": SHOP_ID,
        "wb_cabinet_id": wb_cabinet_id,
        "timezone": TZ,
        "baseline_reference": "A1_BASELINE_V0_20260825-181500.zip",
        "periods": {
            "collect": [COLLECT_FROM.isoformat(), COLLECT_TO.isoformat()],
            "context": [CONTEXT_FROM.isoformat(), CONTEXT_TO.isoformat()],
            "primary_closed": [PRIMARY_FROM.isoformat(), PRIMARY_TO.isoformat()],
            "open_day": OPEN_DAY.isoformat(),
        },
        "endpoints": {
            "history": HISTORY_ENDPOINT,
            "products": PRODUCTS_ENDPOINT,
        },
        "coverage": {
            "nmids_requested": len(nmids),
            "nmids_with_data": len({r["nm_id"] for r in nm_daily}),
            "nm_daily_rows": len(nm_daily),
            "api_calls": coverage.get("api_calls"),
            "history_window": coverage.get("history_window"),
            "products_days_count": len(coverage.get("products_days") or []),
        },
        "primary_baseline_totals_promoted_nm": {
            "order_count": primary_order_count,
            "order_sum": primary_order_sum,
        },
        "reconciliation": reconcile,
        "collector_reused": {
            "wb_api_readonly_ops_funnel": "patterns from scripts/wb_api_readonly_ops/collect/funnel.py",
            "history_adapter": "app.core.mp.wb.api get_sales_funnel_products_history",
            "products_client": "generated post_sales_funnel_products (365d surface)",
        },
    }
    (output_dir / "00_MANIFEST.json").write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8"
    )

    findings = evidence.secret_scan(output_dir)
    if findings:
        raise SystemExit(f"Secret scan failed: {findings[:5]}")

    stamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    archive_path = output_dir.parent / f"A1_SALES_FUNNEL_DELTA_{stamp}.zip"
    with zipfile.ZipFile(archive_path, "w", compression=zipfile.ZIP_DEFLATED) as handle:
        for path in sorted(output_dir.rglob("*")):
            if path.is_file():
                handle.write(path, path.relative_to(output_dir.parent))
    digest_builder = hashlib.sha256()
    with archive_path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest_builder.update(chunk)
    digest = digest_builder.hexdigest()
    # remove default sibling zip if evidence helper was not used
    stray = output_dir.with_suffix(".zip")
    if stray.exists() and stray != archive_path:
        stray.unlink()

    primary_days = _date_range(PRIMARY_FROM, PRIMARY_TO)
    nm_days = {r["date"] for r in nm_daily}
    primary_cov = sum(1 for d in primary_days if d.isoformat() in nm_days)

    return {
        "EXECUTION_STATUS": "COMPLETE",
        "SHOP_ID": SHOP_ID,
        "WB_CABINET_ID": wb_cabinet_id,
        "COLLECTOR_REUSED": "wb_api_readonly_ops/collect/funnel.py + generated products API",
        "CODE_CHANGES": True,
        "API_ENDPOINTS": [HISTORY_ENDPOINT, PRODUCTS_ENDPOINT],
        "DATE_COVERAGE": [COLLECT_FROM.isoformat(), COLLECT_TO.isoformat()],
        "NMIDS_COVERAGE": f"{len({r['nm_id'] for r in nm_daily})}/{len(nmids)}",
        "PRIMARY_BASELINE_COVERAGE": f"{primary_cov}/{len(primary_days)}",
        "PRIMARY_ORDER_COUNT_11_24": primary_order_count,
        "PRIMARY_ORDER_SUM_11_24": primary_order_sum,
        "RECONCILIATION_STATUS": reconcile.get("status"),
        "CRITICAL_GAPS": [
            "history API max 7 days; older days via products single-day periods",
            "cancel metrics absent on history adapter path",
            "OPEN_DAY may mature",
        ],
        "ZIP_ABSOLUTE_PATH": str(archive_path.resolve()),
        "ZIP_SHA256": digest,
    }


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="A1 Sales Funnel delta READ_ONLY collector.")
    parser.add_argument("--output-dir", default=".tmp/a1_sales_funnel_delta")
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    out = Path(args.output_dir).resolve()
    _bootstrap_cluster_infra()
    wb_cabinet_id, nmids = _load_nmids_from_pg(out)
    result = asyncio.run(run_collect(out, wb_cabinet_id, nmids))
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
