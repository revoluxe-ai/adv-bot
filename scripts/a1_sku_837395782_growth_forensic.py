"""READ_ONLY: SKU 837395782 growth forensic package (A1).

Механический сбор factual/funnel/ad/price/stock/search facts для target SKU
и comparison secondary SKUs. Без causal verdicts.
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
PACKAGE_NAME = "A1-SKU-837395782-GROWTH-FORENSIC"
TARGET_SKU = 837395782
SECONDARY_SKUS = [180148471, 1465440975, 322490556, 85970344]
ALL_SKUS = [TARGET_SKU, *SECONDARY_SKUS]

CLOSED_DAYS = ("2026-08-27", "2026-08-28", "2026-08-29", "2026-08-30")
OPEN_DAY = "2026-08-31"
ALL_DAYS = CLOSED_DAYS + (OPEN_DAY,)
ACTIVE_WB = {9, 11}
ORDERS_DAY_FIELD = "date"


def _sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def _write_csv(path: Path, rows: list[dict[str, Any]], cols: list[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=cols, extrasaction="ignore")
        w.writeheader()
        for row in rows:
            w.writerow({c: row.get(c, "") for c in cols})


def _order_day(row: dict[str, Any]) -> str:
    return str(row.get(ORDERS_DAY_FIELD) or row.get("lastChangeDate") or "")[:10]


def _agg_orders(rows: list[dict[str, Any]], nmid: int) -> dict[str, dict[str, Any]]:
    out: dict[str, dict[str, Any]] = {}
    for row in rows:
        if _read_int(row, "nmId", "nm_id", "nmid") != nmid:
            continue
        day = _order_day(row)
        if day not in ALL_DAYS:
            continue
        b = out.setdefault(
            day,
            {
                "factual_orders": 0,
                "factual_units": 0,
                "factual_order_value_rub": 0.0,
                "price_with_disc": [],
                "total_price": [],
                "finished_price": [],
                "last_change_dates": [],
                "supplier_article": row.get("supplierArticle") or "",
            },
        )
        qty = _read_int(row, "quantity", "qty") or 1
        b["factual_orders"] += 1
        b["factual_units"] += qty
        b["factual_order_value_rub"] += _read_float(
            row, "totalPrice", "finishedPrice", "priceWithDisc"
        )
        pwd = _read_float(row, "priceWithDisc")
        tp = _read_float(row, "totalPrice")
        fp = _read_float(row, "finishedPrice")
        if pwd > 0:
            b["price_with_disc"].append(pwd)
        if tp > 0:
            b["total_price"].append(tp)
        if fp > 0:
            b["finished_price"].append(fp)
        lcd = str(row.get("lastChangeDate") or "")
        if lcd:
            b["last_change_dates"].append(lcd)
    for day, b in out.items():
        pwds = b.pop("price_with_disc")
        tps = b.pop("total_price")
        fps = b.pop("finished_price")
        lcds = b.pop("last_change_dates")
        b["avg_priceWithDisc"] = round(sum(pwds) / len(pwds), 2) if pwds else 0
        b["min_priceWithDisc"] = round(min(pwds), 2) if pwds else 0
        b["max_priceWithDisc"] = round(max(pwds), 2) if pwds else 0
        b["avg_totalPrice"] = round(sum(tps) / len(tps), 2) if tps else "GAP"
        b["avg_finishedPrice"] = round(sum(fps) / len(fps), 2) if fps else "GAP"
        b["lastChangeDate_min"] = min(lcds) if lcds else "GAP"
        b["lastChangeDate_max"] = max(lcds) if lcds else "GAP"
        b["factual_order_value_rub"] = round(b["factual_order_value_rub"], 2)
    return out


def _funnel_by_day(rows: list[dict[str, Any]], nmid: int) -> dict[str, dict[str, Any]]:
    out: dict[str, dict[str, Any]] = {}
    for row in rows:
        if _read_int(row, "nmid", "nmId", "nm_id") != nmid:
            continue
        day = str(row.get("day") or row.get("date") or "")[:10]
        if day not in ALL_DAYS:
            continue
        out[day] = {
            "openCardCount": _read_float(row, "open_card", "openCard"),
            "addToCartCount": _read_float(row, "add_to_cart", "addToCart", "cartCount"),
            "ordersCount": _read_float(row, "orders", "orderCount"),
            "orderSum": _read_float(row, "orders_sum", "orderSum"),
            "buyoutCount": _read_float(row, "buy_outs", "buyoutCount"),
            "buyoutSum": _read_float(row, "buyouts_sum_rub", "buyoutSum"),
            "cancelCount": _read_float(row, "cancel_count", "cancelCount"),
            "cancelSum": _read_float(row, "cancel_sum", "cancelSum"),
            "coverage": "AVAILABLE",
        }
    return out


def _adv_ids_for_nmid(campaigns: list[dict[str, Any]], nmid: int) -> list[int]:
    ids: list[int] = []
    for c in campaigns:
        adv_id = _read_int(c, "id", "advertId")
        nm_settings = c.get("nm_settings") or c.get("nmSettings") or []
        nm_ids = []
        if isinstance(nm_settings, list):
            for nm in nm_settings:
                if isinstance(nm, dict):
                    nid = _read_int(nm, "nm_id", "nmId", "nmID")
                    if nid:
                        nm_ids.append(nid)
        if nmid in nm_ids and adv_id:
            ids.append(adv_id)
    return ids


def _campaign_meta(campaigns: list[dict[str, Any]], adv_id: int) -> dict[str, Any]:
    for c in campaigns:
        if _read_int(c, "id", "advertId") == adv_id:
            settings = c.get("settings") if isinstance(c.get("settings"), dict) else {}
            placements = settings.get("placements") if isinstance(settings.get("placements"), dict) else {}
            return {
                "wb_status": c.get("status"),
                "bid_type": c.get("bid_type"),
                "payment_type": settings.get("payment_type"),
                "placements": json.dumps(placements, ensure_ascii=False),
                "name": settings.get("name"),
            }
    return {}


def _fullstats_by_adv_day(
    rows: list[dict[str, Any]], adv_ids: list[int]
) -> dict[tuple[int, str], dict[str, Any]]:
    out: dict[tuple[int, str], dict[str, Any]] = {}
    for row in rows:
        adv_id = _read_int(row, "advertId", "advert_id")
        if adv_id not in adv_ids:
            continue
        day = str(row.get("date") or "")[:10]
        if day not in ALL_DAYS:
            continue
        views = _read_int(row, "views")
        clicks = _read_int(row, "clicks")
        spend = _read_float(row, "sum", "spend")
        ctr = round(100 * clicks / views, 4) if views else _read_float(row, "ctr")
        cpc = round(spend / clicks, 4) if clicks else _read_float(row, "cpc")
        out[(adv_id, day)] = {
            "ad_spend_rub": round(spend, 2),
            "views": views,
            "clicks": clicks,
            "ctr": ctr,
            "cpc": cpc,
            "attributed_orders": _read_int(row, "orders"),
            "attributed_gmv_rub": round(_read_float(row, "sum_price"), 2),
        }
    return out


def _normquery_aggregate(rows: list[dict[str, Any]], nmid: int) -> dict[str, Any]:
    """Normquery stats are period-aggregate in collect (not daily)."""
    for row in rows:
        if _read_int(row, "nmid", "nmId", "nm_id") != nmid:
            continue
        stats = row.get("stats") or []
        if not isinstance(stats, list):
            continue
        total_views = sum(_read_int(s, "views") for s in stats if isinstance(s, dict))
        total_clicks = sum(_read_int(s, "clicks") for s in stats if isinstance(s, dict))
        total_spend = sum(_read_float(s, "spend") for s in stats if isinstance(s, dict))
        positions = [
            _read_float(s, "avr_pos", "avg_pos")
            for s in stats
            if isinstance(s, dict) and _read_float(s, "avr_pos", "avg_pos") > 0
        ]
        return {
            "normquery_rows": len(stats),
            "views_total": total_views,
            "clicks_total": total_clicks,
            "spend_total": round(total_spend, 2),
            "avg_position_weighted": round(sum(positions) / len(positions), 2) if positions else "GAP",
            "granularity": "PERIOD_AGGREGATE_NOT_DAILY",
            "coverage": "AVAILABLE",
        }
    return {"coverage": "GAP", "granularity": "PERIOD_AGGREGATE_NOT_DAILY"}


def _card_snapshot(cards: list[dict[str, Any]], nmid: int) -> dict[str, Any]:
    for card in cards:
        if _read_int(card, "nmID", "nmId", "nmid") != nmid:
            continue
        sizes = card.get("sizes") or []
        return {
            "vendorCode": card.get("vendorCode"),
            "title": card.get("title"),
            "sizes_count": len(sizes) if isinstance(sizes, list) else 0,
            "current_snapshot_at": "collect_time",
            "historical_price_series": "HISTORICAL_GAP",
            "promotions": "HISTORICAL_GAP",
            "spp_wallet_discount": "HISTORICAL_GAP",
        }
    return {"coverage": "GAP"}


def _timeline_events(
    factual: dict[str, dict[str, Any]],
    funnel: dict[str, dict[str, Any]],
    ad_daily: list[dict[str, Any]],
    price_rows: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    events: list[dict[str, Any]] = []
    days = list(CLOSED_DAYS)
    for i, day in enumerate(days):
        fd = factual.get(day, {})
        fn = funnel.get(day, {})
        if fd.get("factual_orders"):
            events.append(
                {
                    "date": day,
                    "event_type": "factual_orders",
                    "value": fd.get("factual_orders"),
                    "detail": f"value_rub={fd.get('factual_order_value_rub')}",
                }
            )
        if i > 0:
            prev = days[i - 1]
            prev_o = factual.get(prev, {}).get("factual_orders", 0)
            cur_o = fd.get("factual_orders", 0)
            if cur_o != prev_o:
                events.append(
                    {
                        "date": day,
                        "event_type": "factual_orders_change",
                        "value": f"{prev_o} -> {cur_o}",
                        "detail": f"delta={cur_o - prev_o}",
                    }
                )
            prev_p = factual.get(prev, {}).get("avg_priceWithDisc", 0)
            cur_p = fd.get("avg_priceWithDisc", 0)
            if cur_p and prev_p and cur_p != prev_p:
                events.append(
                    {
                        "date": day,
                        "event_type": "priceWithDisc_change",
                        "value": f"{prev_p} -> {cur_p}",
                        "detail": "observed from supplier orders",
                    }
                )
            prev_c = funnel.get(prev, {}).get("addToCartCount", "GAP")
            cur_c = fn.get("addToCartCount", "GAP")
            if prev_c != "GAP" and cur_c != "GAP" and cur_c != prev_c:
                events.append(
                    {
                        "date": day,
                        "event_type": "funnel_addToCart_change",
                        "value": f"{prev_c} -> {cur_c}",
                        "detail": "",
                    }
                )
        ad = next((r for r in ad_daily if r["date"] == day), {})
        if ad.get("ad_spend_rub") is not None:
            events.append(
                {
                    "date": day,
                    "event_type": "ad_spend",
                    "value": ad.get("ad_spend_rub"),
                    "detail": f"views={ad.get('views')} clicks={ad.get('clicks')}",
                }
            )
    return sorted(events, key=lambda e: (e["date"], e["event_type"]))


def _delta_row(
    metric: str,
    d28: Any,
    d29: Any,
    d30: Any,
    field_28_29: str,
    field_29_30: str,
) -> dict[str, Any]:
    def _num(v: Any) -> float:
        try:
            return float(v)
        except (TypeError, ValueError):
            return 0.0

    v28, v29, v30 = _num(d28), _num(d29), _num(d30)
    return {
        "metric": metric,
        "value_28": d28,
        "value_29": d29,
        "value_30": d30,
        field_28_29: round(v29 - v28, 4) if d28 != "GAP" and d29 != "GAP" else "GAP",
        field_29_30: round(v30 - v29, 4) if d29 != "GAP" and d30 != "GAP" else "GAP",
    }


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
        await httpx.shutdown()
        await redis_raw.aclose()


def _find_zip(collect_dir: Path) -> Path:
    for name in ("wb_readonly_research.zip",):
        p = collect_dir / name
        if p.exists():
            return p
    zips = sorted(collect_dir.glob("*.zip"), key=lambda p: p.stat().st_mtime, reverse=True)
    if zips:
        return zips[0]
    raise FileNotFoundError(str(collect_dir))


def build_package(root: Path, zip_path: Path, *, collect_report: dict[str, Any] | None = None) -> dict[str, Any]:
    checked = datetime.now(MSK)
    pkg = root / PACKAGE_NAME
    pkg.mkdir(parents=True, exist_ok=True)
    gaps: list[str] = []

    with zipfile.ZipFile(zip_path) as zf:
        orders, om = read_jsonl_from_zip(zf, COLLECT_V2_ORDERS_JSONL)
        funnel, fm = read_jsonl_from_zip(zf, COLLECT_V2_FUNNEL_JSONL)
        fullstats, _ = read_jsonl_from_zip(zf, COLLECT_V2_FULLSTATS_JSONL)
        campaigns, _ = read_jsonl_from_zip(zf, COLLECT_V2_CAMPAIGNS_JSONL)
        try:
            cards = [
                json.loads(l)
                for l in zf.read("raw/cards/cards.jsonl").decode().splitlines()
                if l.strip()
            ]
        except KeyError:
            cards = []
            gaps.append("cards.jsonl missing")
        try:
            nq_rows = [
                json.loads(l)
                for l in zf.read("raw/normqueries/normqueries.jsonl").decode().splitlines()
                if l.strip()
            ]
        except KeyError:
            nq_rows = []
            gaps.append("normqueries.jsonl missing")

    target_adv_ids = _adv_ids_for_nmid(campaigns, TARGET_SKU)
    fs_map = _fullstats_by_adv_day(fullstats, target_adv_ids)
    factual_t = _agg_orders(orders, TARGET_SKU)
    funnel_t = _funnel_by_day(funnel, TARGET_SKU)
    card_t = _card_snapshot(cards, TARGET_SKU)
    nq_t = _normquery_aggregate(nq_rows, TARGET_SKU)

    # 1 factual daily target
    factual_rows = []
    for day in ALL_DAYS:
        b = factual_t.get(day)
        if b:
            factual_rows.append({"date": day, "nmID": TARGET_SKU, **b})
        elif day in CLOSED_DAYS:
            factual_rows.append(
                {
                    "date": day,
                    "nmID": TARGET_SKU,
                    "factual_orders": 0,
                    "factual_units": 0,
                    "factual_order_value_rub": 0,
                    "avg_priceWithDisc": 0,
                    "min_priceWithDisc": 0,
                    "max_priceWithDisc": 0,
                    "lastChangeDate_min": "GAP",
                    "lastChangeDate_max": "GAP",
                }
            )

    # 2 funnel
    funnel_rows = []
    for day in ALL_DAYS:
        fn = funnel_t.get(day)
        if fn:
            funnel_rows.append({"date": day, "nmID": TARGET_SKU, **fn})
        else:
            funnel_rows.append(
                {
                    "date": day,
                    "nmID": TARGET_SKU,
                    "openCardCount": "GAP",
                    "addToCartCount": "GAP",
                    "ordersCount": "GAP",
                    "orderSum": "GAP",
                    "buyoutCount": "GAP",
                    "buyoutSum": "GAP",
                    "cancelCount": "GAP",
                    "cancelSum": "GAP",
                    "coverage": "GAP",
                }
            )

    # 3 ad daily
    ad_rows = []
    promo_change = False
    stock_change = False
    ad_state_change = False
    prev_status = None
    for day in ALL_DAYS:
        day_spend = 0.0
        day_views = 0
        day_clicks = 0
        day_attr_o = 0
        day_attr_gmv = 0.0
        statuses: list[Any] = []
        for adv_id in target_adv_ids:
            meta = _campaign_meta(campaigns, adv_id)
            st = meta.get("wb_status")
            statuses.append(st)
            if prev_status is not None and st != prev_status:
                ad_state_change = True
            prev_status = st
            fs = fs_map.get((adv_id, day), {})
            day_spend += float(fs.get("ad_spend_rub") or 0)
            day_views += int(fs.get("views") or 0)
            day_clicks += int(fs.get("clicks") or 0)
            day_attr_o += int(fs.get("attributed_orders") or 0)
            day_attr_gmv += float(fs.get("attributed_gmv_rub") or 0)
        ad_rows.append(
            {
                "date": day,
                "nmID": TARGET_SKU,
                "active_adv_ids": ";".join(str(x) for x in target_adv_ids),
                "wb_status": ";".join(str(s) for s in statuses),
                "HAS_ACTIVE_AD": any(s in ACTIVE_WB for s in statuses),
                "ad_spend_rub": round(day_spend, 2),
                "views": day_views,
                "clicks": day_clicks,
                "ctr": round(100 * day_clicks / day_views, 4) if day_views else 0,
                "cpc": round(day_spend / day_clicks, 4) if day_clicks else 0,
                "attributed_orders": day_attr_o,
                "attributed_gmv_rub": round(day_attr_gmv, 2),
                "placements": _campaign_meta(campaigns, target_adv_ids[0]).get("placements", "")
                if target_adv_ids
                else "GAP",
                "not_causal": "FORBIDDEN",
            }
        )

    # 4 price/promo
    price_rows = []
    prev_pwd = None
    for day in ALL_DAYS:
        b = factual_t.get(day, {})
        pwd = b.get("avg_priceWithDisc", "GAP")
        if prev_pwd is not None and pwd not in (0, "GAP") and prev_pwd not in (0, "GAP") and pwd != prev_pwd:
            promo_change = True
        prev_pwd = pwd if pwd not in (0, "GAP") else prev_pwd
        price_rows.append(
            {
                "date": day,
                "nmID": TARGET_SKU,
                "priceWithDisc_avg": pwd,
                "priceWithDisc_min": b.get("min_priceWithDisc", "GAP"),
                "priceWithDisc_max": b.get("max_priceWithDisc", "GAP"),
                "totalPrice_avg": b.get("avg_totalPrice", "GAP"),
                "finishedPrice_avg": b.get("avg_finishedPrice", "GAP"),
                "seller_price": "HISTORICAL_GAP",
                "wb_price": "HISTORICAL_GAP",
                "discount_pct": "HISTORICAL_GAP",
                "spp_wallet_discount": "HISTORICAL_GAP",
                "promotions": "HISTORICAL_GAP",
                "promo_id": "HISTORICAL_GAP",
                "card_vendorCode_current": card_t.get("vendorCode", "GAP"),
            }
        )

    # 5 stock
    stock_rows = [
        {
            "date": day,
            "nmID": TARGET_SKU,
            "stock_quantity": "GAP",
            "warehouse_distribution": "GAP",
            "in_stock_state": "GAP",
            "size_availability": "GAP",
            "note": "stocks not in collect_v2 (MISSING_COLLECTOR_CAPABILITIES)",
        }
        for day in ALL_DAYS
    ]
    gaps.append("historical_stocks_not_in_collect")

    # 6 search traffic (target only, period aggregate)
    search_rows = [
        {
            "date": "PERIOD_AGGREGATE",
            "nmID": TARGET_SKU,
            **nq_t,
            "search_impressions_daily": "GAP",
            "search_clicks_daily": "GAP",
            "organic_traffic_daily": "GAP",
            "note": "normquery stats in collect are period-aggregate, not daily",
        }
    ]
    if nq_t.get("coverage") == "GAP":
        gaps.append("normquery_stats_missing_for_target_sku")

    # 7 deltas
    f28, f29, f30 = factual_t.get("2026-08-28", {}), factual_t.get("2026-08-29", {}), factual_t.get("2026-08-30", {})
    fn28, fn29, fn30 = funnel_t.get("2026-08-28", {}), funnel_t.get("2026-08-29", {}), funnel_t.get("2026-08-30", {})
    ad28 = next((r for r in ad_rows if r["date"] == "2026-08-28"), {})
    ad29 = next((r for r in ad_rows if r["date"] == "2026-08-29"), {})
    ad30 = next((r for r in ad_rows if r["date"] == "2026-08-30"), {})
    delta_rows = [
        _delta_row("factual_orders", f28.get("factual_orders", 0), f29.get("factual_orders", 0), f30.get("factual_orders", 0), "delta_28_to_29", "delta_29_to_30"),
        _delta_row("factual_value_rub", f28.get("factual_order_value_rub", 0), f29.get("factual_order_value_rub", 0), f30.get("factual_order_value_rub", 0), "delta_28_to_29", "delta_29_to_30"),
        _delta_row("openCardCount", fn28.get("openCardCount", "GAP"), fn29.get("openCardCount", "GAP"), fn30.get("openCardCount", "GAP"), "delta_28_to_29", "delta_29_to_30"),
        _delta_row("addToCartCount", fn28.get("addToCartCount", "GAP"), fn29.get("addToCartCount", "GAP"), fn30.get("addToCartCount", "GAP"), "delta_28_to_29", "delta_29_to_30"),
        _delta_row("funnel_ordersCount", fn28.get("ordersCount", "GAP"), fn29.get("ordersCount", "GAP"), fn30.get("ordersCount", "GAP"), "delta_28_to_29", "delta_29_to_30"),
        _delta_row("ad_spend_rub", ad28.get("ad_spend_rub", 0), ad29.get("ad_spend_rub", 0), ad30.get("ad_spend_rub", 0), "delta_28_to_29", "delta_29_to_30"),
        _delta_row("views", ad28.get("views", 0), ad29.get("views", 0), ad30.get("views", 0), "delta_28_to_29", "delta_29_to_30"),
        _delta_row("clicks", ad28.get("clicks", 0), ad29.get("clicks", 0), ad30.get("clicks", 0), "delta_28_to_29", "delta_29_to_30"),
        _delta_row("attributed_orders", ad28.get("attributed_orders", 0), ad29.get("attributed_orders", 0), ad30.get("attributed_orders", 0), "delta_28_to_29", "delta_29_to_30"),
        _delta_row("avg_priceWithDisc", f28.get("avg_priceWithDisc", 0), f29.get("avg_priceWithDisc", 0), f30.get("avg_priceWithDisc", 0), "delta_28_to_29", "delta_29_to_30"),
        _delta_row("stock_quantity", "GAP", "GAP", "GAP", "delta_28_to_29", "delta_29_to_30"),
    ]

    timeline = _timeline_events(factual_t, funnel_t, ad_rows, price_rows)

    # 9 secondary comparison
    secondary_rows = []
    for nmid in SECONDARY_SKUS:
        fo = _agg_orders(orders, nmid)
        fu = _funnel_by_day(funnel, nmid)
        aids = _adv_ids_for_nmid(campaigns, nmid)
        fs_s = _fullstats_by_adv_day(fullstats, aids)
        for day in CLOSED_DAYS:
            spend = sum(float(fs_s.get((a, day), {}).get("ad_spend_rub") or 0) for a in aids)
            secondary_rows.append(
                {
                    "date": day,
                    "nmID": nmid,
                    "factual_orders": fo.get(day, {}).get("factual_orders", 0),
                    "factual_order_value_rub": fo.get(day, {}).get("factual_order_value_rub", 0),
                    "avg_priceWithDisc": fo.get(day, {}).get("avg_priceWithDisc", 0),
                    "funnel_addToCart": fu.get(day, {}).get("addToCartCount", "GAP"),
                    "funnel_orders": fu.get(day, {}).get("ordersCount", "GAP"),
                    "ad_spend_rub": round(spend, 2),
                    "HAS_ACTIVE_AD": bool(aids),
                }
            )

    _write_csv(pkg / "837395782_FACTUAL_DAILY.csv", factual_rows, list(factual_rows[0].keys()) if factual_rows else ["date"])
    _write_csv(pkg / "837395782_FUNNEL_DAILY.csv", funnel_rows, list(funnel_rows[0].keys()) if funnel_rows else ["date"])
    _write_csv(pkg / "837395782_AD_DAILY.csv", ad_rows, list(ad_rows[0].keys()) if ad_rows else ["date"])
    _write_csv(pkg / "837395782_PRICE_PROMO_DAILY.csv", price_rows, list(price_rows[0].keys()) if price_rows else ["date"])
    _write_csv(pkg / "837395782_STOCK_DAILY.csv", stock_rows, list(stock_rows[0].keys()))
    _write_csv(pkg / "837395782_SEARCH_TRAFFIC_DAILY.csv", search_rows, list(search_rows[0].keys()))
    _write_csv(pkg / "837395782_DELTA.csv", delta_rows, list(delta_rows[0].keys()))
    _write_csv(pkg / "837395782_EVENT_TIMELINE.csv", timeline, ["date", "event_type", "value", "detail"])
    _write_csv(pkg / "SECONDARY_SKU_COMPARISON.csv", secondary_rows, list(secondary_rows[0].keys()) if secondary_rows else ["date"])

    provenance = [
        "# SOURCE_PROVENANCE",
        "",
        f"- package: `{PACKAGE_NAME}`",
        f"- target_sku: `{TARGET_SKU}`",
        f"- shop_id: `{SHOP_ID}`",
        f"- checked_at_msk: {checked.strftime('%Y-%m-%d %H:%M:%S %Z')}",
        f"- collect_zip: `{zip_path.resolve()}`",
        f"- orders_member: `{om}`",
        f"- funnel_member: `{fm}`",
        f"- orders_day_field: `{ORDERS_DAY_FIELD}`",
        f"- target_adv_ids: `{target_adv_ids}`",
        "- causal_verdict: FORBIDDEN",
        "- promotions_historical: HISTORICAL_GAP (not in collect_v2)",
        "- stocks_historical: GAP",
        "",
        f"- GAPS: {gaps}",
        "",
    ]
    (pkg / "SOURCE_PROVENANCE.md").write_text("\n".join(provenance), encoding="utf-8")

    payload: dict[str, Any] = {
        "package": PACKAGE_NAME,
        "PACKAGE_STATUS": "AUTHORITATIVE",
        "837395782_ORDERS_27": factual_t.get("2026-08-27", {}).get("factual_orders", 0),
        "837395782_ORDERS_28": factual_t.get("2026-08-28", {}).get("factual_orders", 0),
        "837395782_ORDERS_29": factual_t.get("2026-08-29", {}).get("factual_orders", 0),
        "837395782_ORDERS_30": factual_t.get("2026-08-30", {}).get("factual_orders", 0),
        "837395782_VALUE_29": factual_t.get("2026-08-29", {}).get("factual_order_value_rub", 0),
        "837395782_AD_SPEND_28": ad28.get("ad_spend_rub", 0),
        "837395782_AD_SPEND_29": ad29.get("ad_spend_rub", 0),
        "837395782_AD_SPEND_30": ad30.get("ad_spend_rub", 0),
        "837395782_FUNNEL_CARTS_28": fn28.get("addToCartCount", "GAP"),
        "837395782_FUNNEL_CARTS_29": fn29.get("addToCartCount", "GAP"),
        "837395782_FUNNEL_CARTS_30": fn30.get("addToCartCount", "GAP"),
        "837395782_PRICEWITHDISC_28": f28.get("avg_priceWithDisc", 0),
        "837395782_PRICEWITHDISC_29": f29.get("avg_priceWithDisc", 0),
        "837395782_PRICEWITHDISC_30": f30.get("avg_priceWithDisc", 0),
        "837395782_PROMO_CHANGE_FOUND": promo_change,
        "837395782_STOCK_CHANGE_FOUND": stock_change,
        "837395782_AD_STATE_CHANGE_FOUND": ad_state_change,
        "GAPS": gaps,
        "collect_report": collect_report,
    }
    jp = pkg / f"{PACKAGE_NAME}.json"
    jp.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")

    names = [
        "837395782_FACTUAL_DAILY.csv",
        "837395782_FUNNEL_DAILY.csv",
        "837395782_AD_DAILY.csv",
        "837395782_PRICE_PROMO_DAILY.csv",
        "837395782_STOCK_DAILY.csv",
        "837395782_SEARCH_TRAFFIC_DAILY.csv",
        "837395782_DELTA.csv",
        "837395782_EVENT_TIMELINE.csv",
        "SECONDARY_SKU_COMPARISON.csv",
        "SOURCE_PROVENANCE.md",
        f"{PACKAGE_NAME}.json",
    ]
    hashes = {n: _sha256_file(pkg / n) for n in names}
    (pkg / "PACKAGE_MANIFEST.json").write_text(
        json.dumps({"package": PACKAGE_NAME, "PACKAGE_STATUS": "AUTHORITATIVE", "file_sha256": hashes}, indent=2),
        encoding="utf-8",
    )
    zout = root / f"{PACKAGE_NAME}.zip"
    with zipfile.ZipFile(zout, "w", zipfile.ZIP_DEFLATED) as zf:
        for n in names + ["PACKAGE_MANIFEST.json"]:
            zf.write(pkg / n, arcname=n)
    sha = _sha256_file(zout)
    payload["FINAL_ARCHIVE_SHA256"] = sha
    payload["ABSOLUTE_ARCHIVE_PATH"] = str(zout.resolve())
    jp.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")

    return {
        "PACKAGE_STATUS": "AUTHORITATIVE",
        **{k: payload[k] for k in payload if k not in ("collect_report",)},
        "FINAL_ARCHIVE_SHA256": sha,
        "ABSOLUTE_ARCHIVE_PATH": str(zout.resolve()),
    }


async def run(root: Path, *, collect_zip: Path | None, skip_collect: bool) -> dict[str, Any]:
    cd = root / "collect"
    cd.mkdir(parents=True, exist_ok=True)
    cr = None
    if skip_collect and collect_zip and collect_zip.exists():
        zp = collect_zip
    else:
        cr = await _run_collect(cd)
        zp = _find_zip(cd)
    return build_package(root, zp, collect_report=cr)


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--output-dir", default=".tmp/a1_sku_837395782_forensic")
    ap.add_argument("--collect-zip", default="")
    ap.add_argument("--skip-collect", action="store_true")
    args = ap.parse_args(argv)
    root = Path(args.output_dir).resolve()
    root.mkdir(parents=True, exist_ok=True)
    cz = Path(args.collect_zip).resolve() if args.collect_zip else None
    out = asyncio.run(run(root, collect_zip=cz, skip_collect=args.skip_collect or bool(args.collect_zip)))
    print(json.dumps(out, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
