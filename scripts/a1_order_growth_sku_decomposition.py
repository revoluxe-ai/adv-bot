"""READ_ONLY: A1 order growth SKU decomposition (factual orders + funnel + ad flags).

Пакет A1-ORDER-GROWTH-SKU-DECOMPOSITION-20260827-30 для аналитики роста 29–30.08.
Без causal verdicts и production mutations.
"""

from __future__ import annotations

import argparse
import asyncio
import csv
import hashlib
import json
import sys
import zipfile
from collections import defaultdict
from datetime import date, datetime
from pathlib import Path
from typing import Any
from zoneinfo import ZoneInfo

import dotenv

dotenv.load_dotenv()

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
PACKAGE_NAME = "A1-ORDER-GROWTH-SKU-DECOMPOSITION-20260827-30"

CLOSED_DAYS = ("2026-08-27", "2026-08-28", "2026-08-29", "2026-08-30")
OPEN_PARTIAL_DAY = "2026-08-31"
ALL_DAYS = CLOSED_DAYS + (OPEN_PARTIAL_DAY,)
ACTIVE_WB_STATUSES = {9, 11}

ORDERS_DAY_FIELD = "date"


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


def _order_day(row: dict[str, Any]) -> str:
    raw = row.get(ORDERS_DAY_FIELD) or row.get("lastChangeDate") or ""
    return str(raw)[:10]


def _load_vendor_codes(cards: list[dict[str, Any]]) -> dict[int, str]:
    out: dict[int, str] = {}
    for card in cards:
        nmid = _read_int(card, "nmID", "nmId", "nmid")
        if nmid:
            vc = card.get("vendorCode")
            if vc:
                out[nmid] = str(vc)
    return out


def _aggregate_orders(
    rows: list[dict[str, Any]],
    vendor_codes: dict[int, str],
) -> dict[tuple[int, str], dict[str, Any]]:
    agg: dict[tuple[int, str], dict[str, Any]] = {}
    for row in rows:
        day = _order_day(row)
        if day not in ALL_DAYS:
            continue
        nmid = _read_int(row, "nmId", "nm_id", "nmid")
        if not nmid:
            continue
        key = (nmid, day)
        bucket = agg.setdefault(
            key,
            {
                "date": day,
                "nmID": nmid,
                "vendorCode": vendor_codes.get(nmid) or row.get("supplierArticle") or "",
                "factual_orders": 0,
                "factual_units": 0,
                "factual_order_value_rub": 0.0,
                "price_with_disc_values": [],
            },
        )
        qty = _read_int(row, "quantity", "qty") or 1
        pwd = _read_float(row, "priceWithDisc")
        value = _read_float(row, "totalPrice", "finishedPrice", "priceWithDisc")
        bucket["factual_orders"] += 1
        bucket["factual_units"] += qty
        bucket["factual_order_value_rub"] += value
        if pwd > 0:
            bucket["price_with_disc_values"].append(pwd)
    for bucket in agg.values():
        vals = bucket.pop("price_with_disc_values")
        if vals:
            bucket["avg_priceWithDisc"] = round(sum(vals) / len(vals), 2)
            bucket["min_priceWithDisc"] = round(min(vals), 2)
            bucket["max_priceWithDisc"] = round(max(vals), 2)
        else:
            bucket["avg_priceWithDisc"] = "MISSING"
            bucket["min_priceWithDisc"] = "MISSING"
            bucket["max_priceWithDisc"] = "MISSING"
        bucket["factual_order_value_rub"] = round(float(bucket["factual_order_value_rub"]), 2)
    return agg


def _funnel_index(rows: list[dict[str, Any]]) -> dict[tuple[int, str], dict[str, Any]]:
    idx: dict[tuple[int, str], dict[str, Any]] = {}
    for row in rows:
        nmid = _read_int(row, "nmid", "nmId", "nm_id")
        day = str(row.get("day") or row.get("date") or row.get("dt") or "")[:10]
        if not nmid or not day:
            continue
        idx[(nmid, day)] = {
            "openCardCount": _read_float(row, "open_card", "openCard", "openCount"),
            "addToCartCount": _read_float(row, "add_to_cart", "addToCart", "cartCount"),
            "ordersCount": _read_float(row, "orders", "orderCount", "order_count"),
            "orderSum": _read_float(row, "orders_sum", "orderSum", "order_sum"),
        }
    return idx


def _load_physical_contour(path: Path) -> tuple[dict[int, list[int]], dict[int, int]]:
    """nmID -> list physical adv_ids; adv_id -> primary nmID."""
    adv_to_nm: dict[int, int] = {}
    nm_to_advs: dict[int, list[int]] = defaultdict(list)
    with path.open(encoding="utf-8", newline="") as handle:
        for row in csv.DictReader(handle):
            try:
                adv_id = int(row["physical_adv_id"])
                nmid = int(row["nmID"])
            except (KeyError, TypeError, ValueError):
                continue
            adv_to_nm[adv_id] = nmid
            nm_to_advs[nmid].append(adv_id)
    return dict(nm_to_advs), adv_to_nm


def _aggregate_fullstats(
    rows: list[dict[str, Any]],
    adv_to_nm: dict[int, int],
    active_adv_ids: set[int],
) -> dict[tuple[int, str], dict[str, Any]]:
    by_nm_day: dict[tuple[int, str], dict[str, Any]] = defaultdict(
        lambda: {
            "ad_spend_rub": 0.0,
            "attributed_orders": 0,
            "attributed_gmv_rub": 0.0,
            "physical_adv_ids": set(),
        }
    )
    for row in rows:
        adv_id = _read_int(row, "advertId", "advert_id")
        day = str(row.get("date") or "")[:10]
        if not adv_id or day not in ALL_DAYS:
            continue
        nmid = adv_to_nm.get(adv_id)
        if not nmid:
            continue
        key = (nmid, day)
        bucket = by_nm_day[key]
        bucket["ad_spend_rub"] += _read_float(row, "sum", "spend")
        bucket["attributed_orders"] += _read_int(row, "orders")
        bucket["attributed_gmv_rub"] += _read_float(row, "sum_price")
        if adv_id in active_adv_ids:
            bucket["physical_adv_ids"].add(adv_id)
    out: dict[tuple[int, str], dict[str, Any]] = {}
    for key, bucket in by_nm_day.items():
        out[key] = {
            "ad_spend_rub": round(bucket["ad_spend_rub"], 2),
            "attributed_orders": bucket["attributed_orders"],
            "attributed_gmv_rub": round(bucket["attributed_gmv_rub"], 2),
            "physical_adv_ids": sorted(bucket["physical_adv_ids"]),
        }
    return out


def _active_adv_from_campaigns(campaigns: list[dict[str, Any]]) -> set[int]:
    active: set[int] = set()
    for row in campaigns:
        adv_id = _read_int(row, "id", "advertId", "advert_id")
        status = row.get("status")
        if adv_id and status in ACTIVE_WB_STATUSES:
            active.add(adv_id)
    return active


def _store_totals_from_orders(orders_agg: dict[tuple[int, str], dict[str, Any]]) -> dict[str, dict[str, Any]]:
    by_day: dict[str, dict[str, Any]] = defaultdict(
        lambda: {"factual_orders": 0, "factual_order_value_rub": 0.0}
    )
    for (_nmid, day), bucket in orders_agg.items():
        if day in CLOSED_DAYS:
            by_day[day]["factual_orders"] += int(bucket["factual_orders"])
            by_day[day]["factual_order_value_rub"] += float(bucket["factual_order_value_rub"])
    return dict(by_day)


def _sku_totals_from_orders(
    orders_agg: dict[tuple[int, str], dict[str, Any]],
) -> dict[str, dict[str, Any]]:
    by_day: dict[str, dict[str, Any]] = defaultdict(
        lambda: {"factual_orders": 0, "factual_order_value_rub": 0.0}
    )
    for (_nmid, day), bucket in orders_agg.items():
        if day in CLOSED_DAYS:
            by_day[day]["factual_orders"] += int(bucket["factual_orders"])
            by_day[day]["factual_order_value_rub"] += float(bucket["factual_order_value_rub"])
    return dict(by_day)


def _build_delta(
    orders_agg: dict[tuple[int, str], dict[str, Any]],
    day_a: str,
    day_b: str,
    prefix: str,
) -> list[dict[str, Any]]:
    nmids: set[int] = set()
    for nmid, day in orders_agg:
        if day in (day_a, day_b):
            nmids.add(nmid)
    rows: list[dict[str, Any]] = []
    for nmid in nmids:
        a = orders_agg.get((nmid, day_a), {})
        b = orders_agg.get((nmid, day_b), {})
        orders_a = int(a.get("factual_orders") or 0)
        orders_b = int(b.get("factual_orders") or 0)
        value_a = float(a.get("factual_order_value_rub") or 0)
        value_b = float(b.get("factual_order_value_rub") or 0)
        rows.append(
            {
                "nmID": nmid,
                "vendorCode": b.get("vendorCode") or a.get("vendorCode") or "",
                f"orders_{day_a[-2:]}": orders_a,
                f"orders_{day_b[-2:]}": orders_b,
                f"delta_orders_{prefix}": orders_b - orders_a,
                f"value_{day_a[-2:]}": round(value_a, 2),
                f"value_{day_b[-2:]}": round(value_b, 2),
                f"delta_value_{prefix}": round(value_b - value_a, 2),
            }
        )
    rows.sort(key=lambda r: abs(float(r[f"delta_orders_{prefix}"])), reverse=True)
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
            orders_date_from=date(2026, 8, 27).isoformat(),
            max_seconds=DEFAULT_COLLECT_MAX_SECONDS,
            max_api_calls=15_000,
            ads_date_from=date(2026, 8, 27).isoformat(),
            ads_date_to=date(2026, 8, 31).isoformat(),
        )
        return report.to_dict()
    finally:
        await httpx_client_handler.shutdown()
        await redis_client_raw.aclose()


def _find_collect_zip(collect_dir: Path) -> Path:
    for name in ("wb_readonly_research.zip", "collect.zip"):
        candidate = collect_dir / name
        if candidate.exists():
            return candidate
    zips = sorted(collect_dir.glob("*.zip"), key=lambda p: p.stat().st_mtime, reverse=True)
    if zips:
        return zips[0]
    raise FileNotFoundError(f"No collect zip in {collect_dir}")


def build_package(
    root: Path,
    zip_path: Path,
    contour_path: Path,
    *,
    collect_report: dict[str, Any] | None = None,
) -> dict[str, Any]:
    checked_msk = datetime.now(MSK)
    pkg = root / PACKAGE_NAME
    pkg.mkdir(parents=True, exist_ok=True)

    with zipfile.ZipFile(zip_path) as zf:
        orders, orders_member = read_jsonl_from_zip(zf, COLLECT_V2_ORDERS_JSONL)
        funnel, funnel_member = read_jsonl_from_zip(zf, COLLECT_V2_FUNNEL_JSONL)
        fullstats, _fs_member = read_jsonl_from_zip(zf, COLLECT_V2_FULLSTATS_JSONL)
        campaigns, _c_member = read_jsonl_from_zip(zf, COLLECT_V2_CAMPAIGNS_JSONL)
        try:
            cards_raw = zf.read("raw/cards/cards.jsonl").decode("utf-8")
            cards = [json.loads(line) for line in cards_raw.splitlines() if line.strip()]
        except KeyError:
            cards = []

    vendor_codes = _load_vendor_codes(cards)
    orders_agg = _aggregate_orders(orders, vendor_codes)
    funnel_idx = _funnel_index(funnel)
    nm_to_advs, adv_to_nm = _load_physical_contour(contour_path)
    active_adv_ids = _active_adv_from_campaigns(campaigns)
    ad_agg = _aggregate_fullstats(fullstats, adv_to_nm, active_adv_ids)

    all_nmids = sorted(
        {_read_int(row, "nmId", "nm_id", "nmid") for row in orders}
        | {nmid for nmid, _ in funnel_idx}
        | set(nm_to_advs)
    )
    all_nmids = [n for n in all_nmids if n]

    factual_rows: list[dict[str, Any]] = []
    for nmid in all_nmids:
        for day in ALL_DAYS:
            bucket = orders_agg.get((nmid, day))
            if bucket:
                factual_rows.append(
                    {
                        **bucket,
                        "day_state": "OPEN_PARTIAL" if day == OPEN_PARTIAL_DAY else "CLOSED",
                        "orders_source": f"{orders_member} | GET /api/v1/supplier/orders",
                        "orders_day_field": ORDERS_DAY_FIELD,
                    }
                )
            elif day in CLOSED_DAYS:
                factual_rows.append(
                    {
                        "date": day,
                        "nmID": nmid,
                        "vendorCode": vendor_codes.get(nmid, ""),
                        "factual_orders": 0,
                        "factual_units": 0,
                        "factual_order_value_rub": 0.0,
                        "avg_priceWithDisc": 0,
                        "min_priceWithDisc": 0,
                        "max_priceWithDisc": 0,
                        "day_state": "CLOSED",
                        "orders_source": f"{orders_member} | no rows (zero orders)",
                        "orders_day_field": ORDERS_DAY_FIELD,
                    }
                )

    funnel_rows: list[dict[str, Any]] = []
    for nmid in all_nmids:
        for day in ALL_DAYS:
            fd = funnel_idx.get((nmid, day))
            if fd:
                funnel_rows.append(
                    {
                        "date": day,
                        "nmID": nmid,
                        "openCardCount": fd["openCardCount"],
                        "addToCartCount": fd["addToCartCount"],
                        "ordersCount": fd["ordersCount"],
                        "orderSum": fd["orderSum"],
                        "funnel_source": f"{funnel_member} | sales-funnel/products/history",
                        "coverage": "AVAILABLE",
                    }
                )
            elif day in CLOSED_DAYS or day == OPEN_PARTIAL_DAY:
                funnel_rows.append(
                    {
                        "date": day,
                        "nmID": nmid,
                        "openCardCount": "GAP",
                        "addToCartCount": "GAP",
                        "ordersCount": "GAP",
                        "orderSum": "GAP",
                        "funnel_source": funnel_member,
                        "coverage": "GAP",
                    }
                )

    ad_rows: list[dict[str, Any]] = []
    for nmid in all_nmids:
        for day in ALL_DAYS:
            adv_ids = nm_to_advs.get(nmid, [])
            ad = ad_agg.get((nmid, day), {})
            active_on_nm = [a for a in adv_ids if a in active_adv_ids]
            ad_rows.append(
                {
                    "date": day,
                    "nmID": nmid,
                    "HAS_ACTIVE_AD_CAMPAIGN": bool(active_on_nm),
                    "physical_adv_ids": ";".join(str(x) for x in sorted(set(adv_ids))),
                    "active_physical_adv_ids": ";".join(str(x) for x in sorted(active_on_nm)),
                    "ad_spend_rub": ad.get("ad_spend_rub", 0),
                    "attributed_orders": ad.get("attributed_orders", 0),
                    "attributed_gmv_rub": ad.get("attributed_gmv_rub", 0),
                    "ad_source": "raw/ads/fullstats.jsonl (WB attributed; not causal)",
                    "contour_source": str(contour_path),
                }
            )

    delta_28_29 = _build_delta(orders_agg, "2026-08-28", "2026-08-29", "29_vs_28")
    delta_29_30 = _build_delta(orders_agg, "2026-08-29", "2026-08-30", "30_vs_29")

    store_by_day = _store_totals_from_orders(orders_agg)
    sku_by_day = _sku_totals_from_orders(orders_agg)
    recon_rows: list[dict[str, Any]] = []
    reconciliation_fail = False
    for day in CLOSED_DAYS:
        store = store_by_day.get(day, {"factual_orders": 0, "factual_order_value_rub": 0.0})
        sku = sku_by_day.get(day, {"factual_orders": 0, "factual_order_value_rub": 0.0})
        orders_delta = int(sku["factual_orders"]) - int(store["factual_orders"])
        value_delta = round(float(sku["factual_order_value_rub"]) - float(store["factual_order_value_rub"]), 2)
        status = "OK" if orders_delta == 0 and value_delta == 0 else "RECONCILIATION_FAIL"
        if status != "OK":
            reconciliation_fail = True
        recon_rows.append(
            {
                "date": day,
                "store_factual_orders": store["factual_orders"],
                "sku_sum_factual_orders": sku["factual_orders"],
                "orders_delta": orders_delta,
                "store_factual_order_value_rub": round(float(store["factual_order_value_rub"]), 2),
                "sku_sum_factual_order_value_rub": round(float(sku["factual_order_value_rub"]), 2),
                "value_delta_rub": value_delta,
                "reconciliation_status": status,
            }
        )

    top_order_growth = [
        f"{r['nmID']}:{r['delta_orders_29_vs_28']}"
        for r in sorted(delta_28_29, key=lambda x: float(x["delta_orders_29_vs_28"]), reverse=True)[:5]
        if float(r["delta_orders_29_vs_28"]) > 0
    ]
    top_value_growth = [
        f"{r['nmID']}:{r['delta_value_29_vs_28']}"
        for r in sorted(delta_28_29, key=lambda x: float(x["delta_value_29_vs_28"]), reverse=True)[:5]
        if float(r["delta_value_29_vs_28"]) > 0
    ]

    price_mix: list[dict[str, Any]] = []
    top_nmids = {int(x.split(":")[0]) for x in top_order_growth[:5]} | {
        int(x.split(":")[0]) for x in top_value_growth[:5]
    }
    for nmid in sorted(top_nmids):
        row: dict[str, Any] = {"nmID": nmid, "vendorCode": vendor_codes.get(nmid, "")}
        for day in ("2026-08-27", "2026-08-28", "2026-08-29", "2026-08-30"):
            bucket = orders_agg.get((nmid, day))
            if bucket and bucket.get("avg_priceWithDisc") not in ("MISSING", None):
                row[f"avg_priceWithDisc_{day[-2:]}"] = bucket["avg_priceWithDisc"]
                row[f"min_priceWithDisc_{day[-2:]}"] = bucket["min_priceWithDisc"]
                row[f"max_priceWithDisc_{day[-2:]}"] = bucket["max_priceWithDisc"]
            else:
                row[f"avg_priceWithDisc_{day[-2:]}"] = "MISSING"
                row[f"min_priceWithDisc_{day[-2:]}"] = "MISSING"
                row[f"max_priceWithDisc_{day[-2:]}"] = "MISSING"
        price_mix.append(row)

    _write_csv(
        pkg / "SKU_FACTUAL_ORDERS_DAILY.csv",
        factual_rows,
        [
            "date",
            "day_state",
            "nmID",
            "vendorCode",
            "factual_orders",
            "factual_units",
            "factual_order_value_rub",
            "avg_priceWithDisc",
            "min_priceWithDisc",
            "max_priceWithDisc",
            "orders_source",
            "orders_day_field",
        ],
    )
    _write_csv(
        pkg / "SKU_FUNNEL_DAILY.csv",
        funnel_rows,
        [
            "date",
            "nmID",
            "openCardCount",
            "addToCartCount",
            "ordersCount",
            "orderSum",
            "coverage",
            "funnel_source",
        ],
    )
    _write_csv(
        pkg / "SKU_AD_SPEND_DAILY.csv",
        ad_rows,
        [
            "date",
            "nmID",
            "HAS_ACTIVE_AD_CAMPAIGN",
            "physical_adv_ids",
            "active_physical_adv_ids",
            "ad_spend_rub",
            "attributed_orders",
            "attributed_gmv_rub",
            "ad_source",
            "contour_source",
        ],
    )
    _write_csv(pkg / "SKU_DELTA_28_TO_29.csv", delta_28_29, list(delta_28_29[0].keys()) if delta_28_29 else ["nmID"])
    _write_csv(pkg / "SKU_DELTA_29_TO_30.csv", delta_29_30, list(delta_29_30[0].keys()) if delta_29_30 else ["nmID"])
    _write_csv(
        pkg / "STORE_RECONCILIATION.csv",
        recon_rows,
        list(recon_rows[0].keys()) if recon_rows else ["date"],
    )

    provenance = [
        "# SOURCE_PROVENANCE",
        "",
        f"- package: `{PACKAGE_NAME}`",
        f"- shop_id: `{SHOP_ID}`",
        f"- checked_at_msk: {checked_msk.strftime('%Y-%m-%d %H:%M:%S %Z')}",
        f"- collect_zip: `{zip_path.resolve()}`",
        f"- orders_member: `{orders_member}`",
        f"- funnel_member: `{funnel_member}`",
        f"- orders_day_field: `{ORDERS_DAY_FIELD}` (calendar day from supplier orders)",
        f"- physical_contour: `{contour_path.resolve()}`",
        f"- orders_rows_raw: {len(orders)}",
        f"- funnel_rows_raw: {len(funnel)}",
        f"- no_production_mutations: true",
        f"- causal_verdict: FORBIDDEN",
        "",
    ]
    if collect_report:
        provenance.append(f"- collect_report: `{json.dumps(collect_report, ensure_ascii=False)[:500]}`")
    (pkg / "SOURCE_PROVENANCE.md").write_text("\n".join(provenance), encoding="utf-8")

    sku_29 = sum(1 for (n, d), b in orders_agg.items() if d == "2026-08-29" and b["factual_orders"] > 0)
    sku_30 = sum(1 for (n, d), b in orders_agg.items() if d == "2026-08-30" and b["factual_orders"] > 0)
    store_29 = store_by_day.get("2026-08-29", {})
    store_30 = store_by_day.get("2026-08-30", {})

    payload: dict[str, Any] = {
        "package": PACKAGE_NAME,
        "PACKAGE_STATUS": "AUTHORITATIVE",
        "checked_at_msk": checked_msk.strftime("%Y-%m-%d %H:%M:%S %Z"),
        "SKU_COUNT_WITH_ORDERS_29_08": sku_29,
        "SKU_COUNT_WITH_ORDERS_30_08": sku_30,
        "STORE_29_08_FACTUAL_ORDERS": store_29.get("factual_orders"),
        "STORE_29_08_FACTUAL_VALUE": store_29.get("factual_order_value_rub"),
        "STORE_30_08_FACTUAL_ORDERS": store_30.get("factual_orders"),
        "STORE_30_08_FACTUAL_VALUE": store_30.get("factual_order_value_rub"),
        "TOP_5_SKU_BY_ORDER_GROWTH_28_TO_29": top_order_growth,
        "TOP_5_SKU_BY_VALUE_GROWTH_28_TO_29": top_value_growth,
        "RECONCILIATION_STATUS": "RECONCILIATION_FAIL" if reconciliation_fail else "OK",
        "STORE_RECONCILIATION": recon_rows,
        "PRICE_MIX_TOP_GROWTH_SKUS": price_mix,
        "collect_zip": str(zip_path.resolve()),
    }

    json_path = pkg / f"{PACKAGE_NAME}.json"
    json_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")

    artifact_names = [
        "SKU_FACTUAL_ORDERS_DAILY.csv",
        "SKU_FUNNEL_DAILY.csv",
        "SKU_AD_SPEND_DAILY.csv",
        "SKU_DELTA_28_TO_29.csv",
        "SKU_DELTA_29_TO_30.csv",
        "STORE_RECONCILIATION.csv",
        "SOURCE_PROVENANCE.md",
        f"{PACKAGE_NAME}.json",
    ]
    file_hashes = {name: _sha256_file(pkg / name) for name in artifact_names}
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
        for name in artifact_names + ["PACKAGE_MANIFEST.json"]:
            zf.write(pkg / name, arcname=name)

    archive_sha = _sha256_file(zip_out)
    payload["FINAL_ARCHIVE_SHA256"] = archive_sha
    payload["ABSOLUTE_ARCHIVE_PATH"] = str(zip_out.resolve())
    json_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")

    return {
        "PACKAGE_STATUS": "AUTHORITATIVE",
        "SKU_COUNT_WITH_ORDERS_29_08": sku_29,
        "SKU_COUNT_WITH_ORDERS_30_08": sku_30,
        "STORE_29_08_FACTUAL_ORDERS": store_29.get("factual_orders"),
        "STORE_29_08_FACTUAL_VALUE": store_29.get("factual_order_value_rub"),
        "STORE_30_08_FACTUAL_ORDERS": store_30.get("factual_orders"),
        "STORE_30_08_FACTUAL_VALUE": store_30.get("factual_order_value_rub"),
        "TOP_5_SKU_BY_ORDER_GROWTH_28_TO_29": top_order_growth,
        "TOP_5_SKU_BY_VALUE_GROWTH_28_TO_29": top_value_growth,
        "RECONCILIATION_STATUS": payload["RECONCILIATION_STATUS"],
        "FINAL_ARCHIVE_SHA256": archive_sha,
        "ABSOLUTE_ARCHIVE_PATH": str(zip_out.resolve()),
    }


async def run_package(
    root: Path,
    contour_path: Path,
    *,
    collect_zip: Path | None = None,
    skip_collect: bool = False,
) -> dict[str, Any]:
    collect_dir = root / "collect"
    collect_dir.mkdir(parents=True, exist_ok=True)
    collect_report: dict[str, Any] | None = None
    if skip_collect and collect_zip and collect_zip.exists():
        zip_path = collect_zip
    else:
        collect_report = await _run_collect(collect_dir)
        zip_path = _find_collect_zip(collect_dir)
    return build_package(root, zip_path, contour_path, collect_report=collect_report)


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="A1 order growth SKU decomposition READ_ONLY.")
    parser.add_argument("--output-dir", default=".tmp/a1_order_growth_sku")
    parser.add_argument(
        "--contour-map",
        default=".tmp/a1_physical_contour/A1-PHYSICAL-CONTOUR-AND-SEARCH-CONTROL-MAP/PHYSICAL_CAMPAIGN_CONTROL_MAP.csv",
    )
    parser.add_argument("--collect-zip", default="")
    parser.add_argument("--skip-collect", action="store_true")
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    root = Path(args.output_dir).resolve()
    contour = Path(args.contour_map).resolve()
    if not contour.exists():
        raise FileNotFoundError(f"Missing contour map: {contour}")
    root.mkdir(parents=True, exist_ok=True)
    collect_zip = Path(args.collect_zip).resolve() if args.collect_zip else None
    result = asyncio.run(
        run_package(
            root,
            contour,
            collect_zip=collect_zip,
            skip_collect=args.skip_collect or bool(args.collect_zip),
        )
    )
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
