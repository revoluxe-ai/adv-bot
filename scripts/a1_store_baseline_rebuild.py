"""READ_ONLY: A1 store baseline rebuild — units + purchase events + value semantics.

Перестраивает store daily series с учётом bulk/multi-unit (gNumber grouping).
Без production mutations.
"""

from __future__ import annotations

import argparse
import asyncio
import csv
import json
import sys
from collections import defaultdict
from datetime import date, datetime
from pathlib import Path
from typing import Any
from zoneinfo import ZoneInfo

import dotenv

dotenv.load_dotenv()

from scripts.wb_a1_associated_conversions import _read_float, _read_int
from scripts.wb_api_readonly_ops.collect.ads import _flatten_fullstats
from scripts.wb_api_readonly_ops.collect.api_budget import ApiCallBudget
from scripts.wb_api_readonly_ops.collect.orders_sales import _paginate_supplier_rows

SHOP_ID = "5339e9ad-cbfe-50fc-8d77-b9f337a80417"
MSK = ZoneInfo("Europe/Moscow")
PACKAGE = "A1-STORE-BASELINE-REBUILD"
PERIOD_FROM = date(2026, 8, 27)
PERIOD_TO = date(2026, 9, 1)
CLOSED_THROUGH = date(2026, 8, 31)
OPEN_DAY = date(2026, 9, 1)

ALL_DAYS = (
    "2026-08-27",
    "2026-08-28",
    "2026-08-29",
    "2026-08-30",
    "2026-08-31",
    "2026-09-01",
)
FOCUS_SKUS = (837395782, 195764899)

HIST_SNAPSHOTS = {
    "2026-08-27": [{"label": "bulk_forensic_store", "value": 22}],
    "2026-08-28": [
        {"label": "early_snapshot", "value": 23},
        {"label": "bulk_forensic_store", "value": 24},
    ],
    "2026-08-29": [
        {"label": "early_snapshot", "value": 33},
        {"label": "bulk_forensic_store", "value": 34},
    ],
    "2026-08-30": [{"label": "bulk_forensic_store", "value": 29}],
}

SKU_RECON_837 = {
    "2026-08-29": {"units": 11, "purchase_events": 2, "largest_event": 10},
    "2026-08-30": {"units": 10, "purchase_events": 1, "largest_event": 10},
}
SKU_RECON_195 = {
    "2026-09-01": {"units": 10, "purchase_events": 1, "largest_event": 10},
}


def _day_state(d: str) -> str:
    try:
        dt = date.fromisoformat(d)
    except ValueError:
        return "UNKNOWN"
    if dt == OPEN_DAY:
        return "OPEN_PARTIAL"
    if PERIOD_FROM <= dt <= CLOSED_THROUGH:
        return "CLOSED"
    return "OUT_OF_SCOPE"


def _order_day(row: dict[str, Any]) -> str:
    return str(row.get("date") or "")[:10]


def _is_cancelled(row: dict[str, Any]) -> bool:
    return str(row.get("isCancel")).lower() in ("true", "1", "t")


def _g_key(row: dict[str, Any]) -> str:
    g = str(row.get("gNumber") or "").strip()
    return g if g else f"srid:{row.get('srid')}"


def _write_csv(path: Path, rows: list[dict[str, Any]], cols: list[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=cols, extrasaction="ignore")
        w.writeheader()
        for r in rows:
            w.writerow({c: r.get(c, "") for c in cols})


def _adv_nm_map(campaigns: list[dict[str, Any]]) -> dict[int, set[int]]:
    out: dict[int, set[int]] = defaultdict(set)
    for c in campaigns:
        adv_id = _read_int(c, "id", "advertId")
        if not adv_id:
            continue
        for nm in c.get("nm_settings") or c.get("nmSettings") or []:
            if isinstance(nm, dict):
                nid = _read_int(nm, "nm_id", "nmId", "nmID")
                if nid:
                    out[adv_id].add(nid)
    return out


def _nm_to_advs(adv_nm: dict[int, set[int]]) -> dict[int, set[int]]:
    out: dict[int, set[int]] = defaultdict(set)
    for adv_id, nms in adv_nm.items():
        for n in nms:
            out[n].add(adv_id)
    return out


def _aggregate_ad_daily(
    fullstats: list[dict[str, Any]], campaigns: list[dict[str, Any]]
) -> tuple[dict[str, dict[str, Any]], dict[tuple[int, str], dict[str, Any]]]:
    store: dict[str, dict[str, Any]] = {d: defaultdict(float) for d in ALL_DAYS}
    sku_day: dict[tuple[int, str], dict[str, Any]] = {}
    adv_nm = _adv_nm_map(campaigns)
    nm_advs = _nm_to_advs(adv_nm)

    for row in fullstats:
        adv_id = _read_int(row, "advertId", "advert_id")
        day = str(row.get("date") or "")[:10]
        if day not in ALL_DAYS:
            continue
        spend = _read_float(row, "sum", "spend")
        views = _read_int(row, "views")
        clicks = _read_int(row, "clicks")
        attr_o = _read_int(row, "orders")
        attr_gmv = _read_float(row, "sum_price")
        b = store[day]
        b["ad_spend_rub"] += spend
        b["views"] += views
        b["clicks"] += clicks
        b["attributed_orders"] += attr_o
        b["attributed_gmv_rub"] += attr_gmv
        if spend > 0:
            b.setdefault("_spend_advs", set()).add(adv_id)
        for nmid in adv_nm.get(adv_id, ()):
            key = (nmid, day)
            sb = sku_day.setdefault(
                key,
                {"ad_spend_rub": 0.0, "clicks": 0, "attributed_orders": 0},
            )
            sb["ad_spend_rub"] += spend
            sb["clicks"] += clicks
            sb["attributed_orders"] += attr_o

    out_store: dict[str, dict[str, Any]] = {}
    for d in ALL_DAYS:
        b = store[d]
        advs = b.pop("_spend_advs", set())
        out_store[d] = {
            "ad_spend_rub": round(float(b.get("ad_spend_rub", 0)), 2),
            "physical_campaigns_with_spend": len(advs),
            "views": int(b.get("views", 0)),
            "clicks": int(b.get("clicks", 0)),
            "attributed_orders": int(b.get("attributed_orders", 0)),
            "attributed_gmv_rub": round(float(b.get("attributed_gmv_rub", 0)), 2),
        }
    return out_store, sku_day


def _day_orders(orders: list[dict[str, Any]], day: str) -> list[dict[str, Any]]:
    return [r for r in orders if _order_day(r) == day]


def _active_rows(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    return [r for r in rows if not _is_cancelled(r)]


def _bulk_buckets(groups: dict[str, list[dict[str, Any]]]) -> dict[str, Any]:
    sizes = [len(v) for v in groups.values()]
    units = sum(sizes)
    multi_units = sum(s for s in sizes if s >= 2)
    bulk_events = sum(1 for s in sizes if s >= 2)
    b1 = sum(1 for s in sizes if s == 1)
    b2_4 = sum(1 for s in sizes if 2 <= s <= 4)
    b5_9 = sum(1 for s in sizes if 5 <= s <= 9)
    b10p = sum(1 for s in sizes if s >= 10)
    return {
        "BULK_EVENT_COUNT": bulk_events,
        "BULK_UNIT_SHARE": round(100 * multi_units / units, 2) if units else 0,
        "MAX_EVENT_SIZE": max(sizes) if sizes else 0,
        "events_1_unit": b1,
        "events_2_4_units": b2_4,
        "events_5_9_units": b5_9,
        "events_10plus_units": b10p,
        "units_from_multi_unit_events": multi_units,
    }


def _value_sums(rows: list[dict[str, Any]]) -> dict[str, float]:
    return {
        "SUM_TOTAL_PRICE": round(sum(_read_float(r, "totalPrice") for r in rows), 2),
        "SUM_PRICE_WITH_DISC": round(sum(_read_float(r, "priceWithDisc") for r in rows), 2),
        "SUM_FINISHED_PRICE": round(sum(_read_float(r, "finishedPrice") for r in rows), 2),
    }


def _concentration(groups: dict[str, list[dict[str, Any]]], units: int, vals: dict[str, float]) -> dict[str, Any]:
    ranked = sorted(groups.items(), key=lambda x: -len(x[1]))
    top1_u = len(ranked[0][1]) if ranked else 0
    top3_u = sum(len(v) for _, v in ranked[:3])
    top1_tp = round(sum(_read_float(r, "totalPrice") for r in ranked[0][1]), 2) if ranked else 0
    top3_tp = round(
        sum(_read_float(r, "totalPrice") for _, members in ranked[:3] for r in members), 2
    )
    stp = vals["SUM_TOTAL_PRICE"]
    return {
        "top1_event_units": top1_u,
        "top3_events_units": top3_u,
        "top1_share_of_daily_units_pct": round(100 * top1_u / units, 2) if units else 0,
        "top3_share_of_daily_units_pct": round(100 * top3_u / units, 2) if units else 0,
        "top1_share_of_SUM_TOTAL_PRICE_pct": round(100 * top1_tp / stp, 2) if stp else 0,
        "top3_share_of_SUM_TOTAL_PRICE_pct": round(100 * top3_tp / stp, 2) if stp else 0,
    }


def _sku_day_stats(rows: list[dict[str, Any]]) -> dict[int, dict[str, Any]]:
    by_sku: dict[int, list[dict[str, Any]]] = defaultdict(list)
    for r in rows:
        nmid = _read_int(r, "nmId", "nm_id", "nmid")
        if nmid:
            by_sku[nmid].append(r)
    out: dict[int, dict[str, Any]] = {}
    for nmid, rs in by_sku.items():
        groups: dict[str, list[dict[str, Any]]] = defaultdict(list)
        for r in rs:
            groups[_g_key(r)].append(r)
        events = len(groups)
        units = len(rs)
        vals = _value_sums(rs)
        out[nmid] = {
            "nmID": nmid,
            "units": units,
            "purchase_events": events,
            "units_per_event": round(units / events, 2) if events else 0,
            "bulk_max_event_size": max((len(v) for v in groups.values()), default=0),
            **vals,
        }
    return out


def build(orders: list[dict[str, Any]], ad_store: dict[str, dict[str, Any]], sku_ad: dict) -> dict[str, Any]:
    checked = datetime.now(MSK)
    gaps: list[str] = []

    store_daily: list[dict[str, Any]] = []
    value_daily: list[dict[str, Any]] = []
    bulk_daily: list[dict[str, Any]] = []
    sku_daily: list[dict[str, Any]] = []
    pe_groups: list[dict[str, Any]] = []
    ad_daily: list[dict[str, Any]] = []
    concentration: dict[str, Any] = {}

    series_units: dict[str, int] = {}
    series_events: dict[str, int] = {}
    series_upe: dict[str, float] = {}
    series_bulk_events: dict[str, int] = {}
    series_bulk_share: dict[str, float] = {}
    series_max: dict[str, int] = {}
    series_stp: dict[str, float] = {}
    series_spd: dict[str, float] = {}
    series_fp: dict[str, float] = {}
    series_ad: dict[str, float] = {}
    ratios: dict[str, dict[str, Any]] = {}

    for day in ALL_DAYS:
        all_rows = _day_orders(orders, day)
        active = _active_rows(all_rows)
        groups: dict[str, list[dict[str, Any]]] = defaultdict(list)
        for r in active:
            groups[_g_key(r)].append(r)

        units = len(active)
        events = len(groups)
        upe = round(units / events, 2) if events else 0
        sku_stats = _sku_day_stats(active)
        vals = _value_sums(active)
        bulk = _bulk_buckets(groups)
        conc = _concentration(groups, units, vals)
        concentration[day] = conc

        series_units[day] = units
        series_events[day] = events
        series_upe[day] = upe
        series_bulk_events[day] = bulk["BULK_EVENT_COUNT"]
        series_bulk_share[day] = bulk["BULK_UNIT_SHARE"]
        series_max[day] = bulk["MAX_EVENT_SIZE"]
        series_stp[day] = vals["SUM_TOTAL_PRICE"]
        series_spd[day] = vals["SUM_PRICE_WITH_DISC"]
        series_fp[day] = vals["SUM_FINISHED_PRICE"]
        ad = ad_store.get(day, {})
        spend = float(ad.get("ad_spend_rub") or 0)
        series_ad[day] = spend
        ratios[day] = {
            "AD_SPEND": spend,
            "AD_SPEND_over_SUM_TOTAL_PRICE": round(spend / vals["SUM_TOTAL_PRICE"], 6)
            if vals["SUM_TOTAL_PRICE"]
            else "GAP",
            "AD_SPEND_over_SUM_PRICE_WITH_DISC": round(spend / vals["SUM_PRICE_WITH_DISC"], 6)
            if vals["SUM_PRICE_WITH_DISC"]
            else "GAP",
            "AD_SPEND_over_SUM_FINISHED_PRICE": round(spend / vals["SUM_FINISHED_PRICE"], 6)
            if vals["SUM_FINISHED_PRICE"]
            else "GAP",
        }

        store_daily.append(
            {
                "date": day,
                "state": _day_state(day),
                "raw_order_rows_all": len(all_rows),
                "cancelled_rows": sum(1 for r in all_rows if _is_cancelled(r)),
                "units": units,
                "purchase_events": events,
                "units_per_event": upe,
                "distinct_srid": len({str(r.get("srid")) for r in active if r.get("srid")}),
                "distinct_SKU_with_units": len(sku_stats),
                "distinct_SKU_with_purchase_events": len(sku_stats),
            }
        )
        value_daily.append(
            {
                "date": day,
                "state": _day_state(day),
                **vals,
                "avg_totalPrice_per_unit": round(vals["SUM_TOTAL_PRICE"] / units, 2) if units else 0,
                "avg_priceWithDisc_per_unit": round(vals["SUM_PRICE_WITH_DISC"] / units, 2) if units else 0,
                "avg_finishedPrice_per_unit": round(vals["SUM_FINISHED_PRICE"] / units, 2) if units else 0,
                "avg_totalPrice_per_purchase_event": round(vals["SUM_TOTAL_PRICE"] / events, 2)
                if events
                else 0,
                "avg_finishedPrice_per_purchase_event": round(vals["SUM_FINISHED_PRICE"] / events, 2)
                if events
                else 0,
            }
        )
        bulk_daily.append({"date": day, "state": _day_state(day), **bulk})
        ad_daily.append({"date": day, "state": _day_state(day), **ad})

        for gnum, members in groups.items():
            gv = _value_sums(members)
            pe_groups.append(
                {
                    "date": day,
                    "gNumber": gnum,
                    "units": len(members),
                    "is_bulk": len(members) >= 2,
                    "first_date": min(str(m.get("date") or "") for m in members),
                    "region": members[0].get("regionName") or "",
                    "primary_nmId": _read_int(members[0], "nmId", "nm_id"),
                    **gv,
                }
            )

        for nmid, st in sku_stats.items():
            adk = sku_ad.get((nmid, day), {})
            sku_daily.append(
                {
                    "date": day,
                    "state": _day_state(day),
                    **st,
                    "ad_spend_rub": round(float(adk.get("ad_spend_rub") or 0), 2),
                    "ad_clicks": int(adk.get("clicks") or 0),
                    "attributed_orders": int(adk.get("attributed_orders") or 0),
                }
            )

    def _deltas() -> list[dict[str, Any]]:
        pairs = [
            ("2026-08-27", "2026-08-28"),
            ("2026-08-28", "2026-08-29"),
            ("2026-08-29", "2026-08-30"),
            ("2026-08-30", "2026-08-31"),
            ("2026-08-31", "2026-09-01"),
        ]
        out = []
        for a, b in pairs:
            out.append(
                {
                    "from": a,
                    "to": b,
                    "delta_units": series_units[b] - series_units[a],
                    "delta_purchase_events": series_events[b] - series_events[a],
                    "delta_SUM_TOTAL_PRICE": round(series_stp[b] - series_stp[a], 2),
                    "delta_ad_spend": round(series_ad[b] - series_ad[a], 2),
                }
            )
        return out

    def _top_skus(key: str, n: int = 10) -> dict[str, list[dict[str, Any]]]:
        out: dict[str, list[dict[str, Any]]] = {}
        for day in ALL_DAYS:
            day_rows = [r for r in sku_daily if r["date"] == day]
            ranked = sorted(day_rows, key=lambda x: -float(x.get(key) or 0))[:n]
            out[day] = ranked
        return out

    drift_rows: list[dict[str, Any]] = []
    for day, snaps in HIST_SNAPSHOTS.items():
        current = series_units[day]
        for snap in snaps:
            old = snap["value"]
            drift_rows.append(
                {
                    "date": day,
                    "snapshot_label": snap["label"],
                    "OLD_VALUE": old,
                    "OLD_VALUE_CLASS": "SNAPSHOT_AT_TIME",
                    "CURRENT_VALUE": current,
                    "CURRENT_VALUE_CLASS": "LATEST_REBUILT_STATE",
                    "delta": current - old,
                    "late_api_update_possible": "YES — supplier orders cursor uses lastChangeDate",
                }
            )

    def _sku_recon(nmid: int, expected: dict[str, dict[str, int]]) -> dict[str, Any]:
        result: dict[str, Any] = {"nmID": nmid, "days": {}}
        for day, exp in expected.items():
            row = next((r for r in sku_daily if r["date"] == day and r["nmID"] == nmid), None)
            if not row:
                result["days"][day] = {"status": "MISMATCH", "expected": exp, "observed": "MISSING"}
                continue
            obs = {
                "units": row["units"],
                "purchase_events": row["purchase_events"],
                "largest_event": row["bulk_max_event_size"],
            }
            ok = all(obs[k] == exp[k] for k in exp)
            result["days"][day] = {
                "status": "MATCH" if ok else "MISMATCH",
                "expected": exp,
                "observed": obs,
            }
        return result

    return {
        "CHECKED_AT_MSK": checked.strftime("%Y-%m-%d %H:%M:%S %Z"),
        "PERIOD": f"{PERIOD_FROM} → {PERIOD_TO}",
        "STORE_UNITS_SERIES": series_units,
        "STORE_PURCHASE_EVENT_SERIES": series_events,
        "UNITS_PER_EVENT_SERIES": series_upe,
        "BULK_EVENT_SERIES": series_bulk_events,
        "BULK_UNIT_SHARE_SERIES": series_bulk_share,
        "MAX_EVENT_SIZE_SERIES": series_max,
        "SUM_TOTAL_PRICE_SERIES": series_stp,
        "SUM_PRICE_WITH_DISC_SERIES": series_spd,
        "SUM_FINISHED_PRICE_SERIES": series_fp,
        "AD_SPEND_SERIES": series_ad,
        "THREE_DENOMINATOR_RATIOS": ratios,
        "DAILY_DELTAS": _deltas(),
        "HISTORICAL_ROW_COUNT_DRIFT": drift_rows,
        "TOP_SKU_BY_UNITS": _top_skus("units"),
        "TOP_SKU_BY_PURCHASE_EVENTS": _top_skus("purchase_events"),
        "TOP_SKU_BY_SUM_TOTAL_PRICE": _top_skus("SUM_TOTAL_PRICE"),
        "TOP_SKU_BY_SUM_FINISHED_PRICE": _top_skus("SUM_FINISHED_PRICE"),
        "PURCHASE_EVENT_CONCENTRATION": concentration,
        "837395782_RECONCILIATION": _sku_recon(837395782, SKU_RECON_837),
        "195764899_RECONCILIATION": _sku_recon(195764899, SKU_RECON_195),
        "KPI_DENOMINATOR_SELECTION": "OPEN",
        "ANALYTICAL_CONTRACT": {
            "UNITS": "non-cancelled supplier-order raw rows",
            "PURCHASE_EVENTS": "distinct gNumber among non-cancelled rows",
            "TOTAL_PRICE_VALUE": "sum totalPrice",
            "PRICE_WITH_DISC_VALUE": "sum priceWithDisc",
            "FINISHED_PRICE_VALUE": "sum finishedPrice",
            "ATTRIBUTED_ORDERS": "advertising attribution metric, separate from supplier-order metrics",
            "note": "Do not use 'orders' without qualifier",
        },
        "OPEN_GAPS": gaps,
        "_csv": {
            "STORE_DAILY_BASELINE": store_daily,
            "STORE_DAILY_VALUE_SEMANTICS": value_daily,
            "STORE_DAILY_BULK_STRUCTURE": bulk_daily,
            "SKU_DAILY_BASELINE": sku_daily,
            "PURCHASE_EVENT_GROUPS": pe_groups,
            "AD_DAILY_CONTEXT": ad_daily,
            "SNAPSHOT_DRIFT": drift_rows,
        },
    }


async def fetch_data() -> tuple[list[dict[str, Any]], list[dict[str, Any]], list[dict[str, Any]]]:
    import datetime as dt

    from app.configs.app_config import AppConfig
    from app.core.di.wb_manager_hub.wb_manager_hub_factory import WBManagerHubFactory
    from app.core.mp.wb.api.httpx_client_handler import HttpxClientHandler
    from app.core.redis_manager_v2.redis_client import RedisClient
    from app.modules.common_slaves.wildberries.super_cabinet_manager import (
        get_access_for_wb_cabinet,
    )
    from redis.asyncio import Redis
    from scripts.wb_api_readonly_ops.collect.jsonable import jsonable

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
        budget = ApiCallBudget(max_seconds=1200.0, max_api_calls=1200)

        reports_manager = getattr(dm, "reports_manager", None)

        async def fetch_orders(df: str) -> list[object]:
            if reports_manager is not None:
                return list(await reports_manager.get_supplier_orders(date_from=df, flag=0) or [])
            return list(await dm.get_supplier_orders(date_from=df, flag=0) or [])

        orders_result = await _paginate_supplier_rows(
            fetch=fetch_orders,
            initial_date_from=PERIOD_FROM.isoformat(),
            budget=budget,
            max_pages=1200,
        )

        budget.consume()
        adv_ids = list(await pm._client.promotion_count_adapter.get_cabinet_adv_ids() or [])
        budget.consume()
        campaigns_raw = list(await pm.get_adverts_v2_by_ids(adv_ids) or [])
        campaigns: list[dict[str, Any]] = []
        for item in campaigns_raw:
            row = jsonable(item)
            if isinstance(row, dict):
                campaigns.append(row)

        dates: list[dt.date] = []
        cur = PERIOD_FROM
        while cur <= PERIOD_TO:
            dates.append(cur)
            cur += dt.timedelta(days=1)
        budget.consume()
        stats_raw = await pm.get_full_adv_stat(adv_ids, dates)
        fullstats = _flatten_fullstats(list(stats_raw or []))

        return orders_result.rows, campaigns, fullstats
    finally:
        await httpx.shutdown()
        await redis_raw.aclose()


async def run(output_dir: Path) -> dict[str, Any]:
    orders, campaigns, fullstats = await fetch_data()
    ad_store, sku_ad = _aggregate_ad_daily(fullstats, campaigns)
    payload = build(orders, ad_store, sku_ad)

    pkg = output_dir / PACKAGE
    pkg.mkdir(parents=True, exist_ok=True)
    csv_map = payload.pop("_csv")
    for name, rows in csv_map.items():
        fname = f"{name}.csv"
        cols = list(rows[0].keys()) if rows else ["date"]
        _write_csv(pkg / fname, rows, cols)

    out_json = pkg / f"{PACKAGE}.json"
    out_json.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    payload["CSV_PACKAGE_DIR"] = str(pkg.resolve())
    return payload


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--output-dir", default=".tmp/a1_store_baseline_rebuild")
    args = ap.parse_args(argv)
    root = Path(args.output_dir).resolve()
    root.mkdir(parents=True, exist_ok=True)
    out = asyncio.run(run(root))
    print(json.dumps(out, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
