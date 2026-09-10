"""READ_ONLY: SKU factual GMV (supplier orders) + live WB campaign inventory и spend.

Переиспользует wb_api_readonly_ops orders pagination и A1 fullstats/PG patterns.
Для решений KEEP/REDUCE/PAUSE/SCALE по одному nmid. Без production writes.
"""

from __future__ import annotations

import argparse
import asyncio
import json
import os
import re
import sys
import tempfile
from collections import defaultdict
from datetime import date, datetime, timedelta, timezone
from pathlib import Path
from typing import Any
from zoneinfo import ZoneInfo

import dotenv

dotenv.load_dotenv()

from scripts.a1_daily_spend_control_reconciliation import _campaign_inventory, _pg_by_adv_id
from scripts.set_path import add_project_root_to_path

add_project_root_to_path()

from app.configs.app_config import AppConfig
from app.core.di.wb_manager_hub.wb_manager_hub_factory import WBManagerHubFactory
from app.core.mp.wb.api.httpx_client_handler import HttpxClientHandler
from app.core.redis_manager_v2.redis_client import RedisClient
from app.modules.common_slaves.wildberries.super_cabinet_manager import (
    get_access_for_wb_cabinet,
)
from scripts.wb_a1_associated_conversions import _read_float, _read_int
from scripts.wb_api_readonly_ops.collect.api_budget import ApiCallBudget
from scripts.wb_api_readonly_ops.collect.jsonable import jsonable
from scripts.wb_api_readonly_ops.collect.orders_sales import collect_orders_sales
from scripts.wb_api_readonly_ops.collect.raw_store import RawStore

MSK = ZoneInfo("Europe/Moscow")
WB_ACTIVE = {9, 11}
PG_OWNERSHIP_FIELDS = (
    "id",
    "adv_id",
    "_search_adv_id",
    "type",
    "name",
    "nmids",
    "active_status",
    "bot_active",
    "automatic_version",
    "strategy",
    "aggressiveness",
    "target_price_for_order",
    "max_price_for_order",
    "plan_for_sales_for_day",
    "bidder_active",
)


def _closed_end(explicit: date | None) -> date:
    if explicit is not None:
        return explicit
    return datetime.now(timezone.utc).astimezone(MSK).date() - timedelta(days=1)


def _parse_nmids(raw: Any) -> list[int]:
    return [int(x) for x in re.findall(r"\d+", str(raw or ""))]


def _is_cancel(row: dict[str, Any]) -> bool:
    return str(row.get("isCancel")).lower() in ("true", "1", "t")


def _order_day(row: dict[str, Any]) -> date | None:
    raw = str(row.get("date") or row.get("lastChangeDate") or "")[:10]
    try:
        return date.fromisoformat(raw)
    except ValueError:
        return None


def _gmv(row: dict[str, Any]) -> float:
    return float(_read_float(row, "finishedPrice", "priceWithDisc") or 0)


def _window_agg(
    rows: list[dict[str, Any]], nmid: int, start: date, end: date
) -> dict[str, Any]:
    orders = cancels = 0
    gmv = cancel_gmv = 0.0
    for row in rows:
        if _read_int(row, "nmId", "nmID", "nm_id") != nmid:
            continue
        d = _order_day(row)
        if d is None or d < start or d > end:
            continue
        if _is_cancel(row):
            cancels += 1
            cancel_gmv += _gmv(row)
        else:
            orders += 1
            gmv += _gmv(row)
    return {
        "orders": orders,
        "gmv_rub": round(gmv, 2),
        "cancellations": cancels,
        "cancel_gmv_rub": round(cancel_gmv, 2),
    }


def _drr(spend: float | None, gmv: float | None) -> str | float:
    if spend is None or gmv is None or gmv <= 0:
        return "N/A"
    return round(100.0 * spend / gmv, 2)


def _campaign_contains_nmid(campaign: dict[str, Any], nmid: int) -> bool:
    for ns in campaign.get("nm_settings") or campaign.get("nmSettings") or []:
        if isinstance(ns, dict) and _read_int(ns, "nm_id", "nmId", "nmID") == nmid:
            return True
    return nmid in _parse_nmids(
        (campaign.get("settings") or {}).get("nmids") if isinstance(campaign.get("settings"), dict) else ""
    )


async def _pg_adv_rows(shop_id: str, nmid: int) -> list[dict[str, Any]]:
    import asyncpg

    conn = await asyncpg.connect(
        host=os.environ["POSTGRES_MASTER_HOST"],
        port=int(os.environ.get("POSTGRES_PORT", 5432)),
        user=os.environ["POSTGRES_USER"],
        password=os.environ["POSTGRES_PASSWORD"],
        database=os.environ.get("POSTGRES_DBNAME", "adv_updater"),
        ssl=False,
    )
    cols = ", ".join(f"a.{c}" for c in PG_OWNERSHIP_FIELDS)
    rows = await conn.fetch(
        f"""
        SELECT {cols}
        FROM advsetting a
        JOIN wbcabinet c ON a.wb_cabinet_id = c.id
        WHERE c.shop_id = $1
          AND a.nmids::text LIKE $2
        """,
        shop_id,
        f"%{nmid}%",
    )
    await conn.close()
    return [dict(r) for r in rows]


def _stat_bucket(day_obj: Any) -> dict[str, float]:
    d = jsonable(day_obj) if not isinstance(day_obj, dict) else day_obj
    if not isinstance(d, dict):
        return {}
    spend = float(_read_float(d, "sum") or 0)
    views = float(_read_float(d, "views") or 0)
    clicks = float(_read_float(d, "clicks") or 0)
    orders = float(_read_float(d, "orders") or 0)
    atbs = float(_read_float(d, "atbs") or 0)
    gmv = float(_read_float(d, "sum_price") or 0)
    ctr = round(100 * clicks / views, 4) if views else None
    cpc = round(spend / clicks, 2) if clicks else None
    cpm = round(1000 * spend / views, 2) if views else None
    cpo = round(spend / orders, 2) if orders else None
    return {
        "spend": round(spend, 2),
        "views": int(views),
        "clicks": int(clicks),
        "atbs": int(atbs),
        "attributed_orders": int(orders),
        "attributed_gmv": round(gmv, 2),
        "ctr_pct": ctr,
        "cpc_rub": cpc,
        "cpm_rub": cpm,
        "cpo_rub": cpo,
    }


async def _collect(args: argparse.Namespace) -> dict[str, Any]:
    closed = _closed_end(args.closed_day)
    shop_id = args.shop_id
    nmid = args.nmid
    windows = {
        "1D": (closed, closed),
        "3D": (closed - timedelta(days=2), closed),
        "7D": (closed - timedelta(days=6), closed),
        "14D": (closed - timedelta(days=13), closed),
        "28D": (closed - timedelta(days=27), closed),
    }
    stat_dates = [
        closed - timedelta(days=i) for i in range((closed - windows["28D"][0]).days, -1, -1)
    ]

    app_config = AppConfig.create()
    redis_cfg = app_config.infrastructure.redis
    from redis.asyncio import Redis

    redis_raw: Redis[str] = Redis(
        host=redis_cfg.host,
        port=redis_cfg.port,
        db=redis_cfg.db,
        password=redis_cfg.password,
        decode_responses=True,
    )
    await redis_raw.ping()
    redis_wrap = RedisClient(redis_client=redis_raw)
    httpx_handler = HttpxClientHandler()
    await httpx_handler.init()
    factory = WBManagerHubFactory(
        httpx_client_handler=httpx_handler,
        redis_client_wrapper=redis_wrap,
    )
    gaps: list[str] = []

    try:
        await get_access_for_wb_cabinet(shop_id)
        hub = factory.get_wb_manager_hub(shop_id)
        dm = hub.wb_data_manager
        pm = dm.promotion_manager

        pg_rows = await _pg_adv_rows(shop_id, nmid)
        pg_by_adv = _pg_by_adv_id([{k: str(v) for k, v in r.items()} for r in pg_rows])
        adv_ids_pg = sorted({int(r["adv_id"]) for r in pg_rows if r.get("adv_id")})

        campaigns_live: list[dict[str, Any]] = []
        for chunk_start in range(0, len(adv_ids_pg), 50):
            chunk = adv_ids_pg[chunk_start : chunk_start + 50]
            try:
                items = await pm.get_adverts_v2_by_ids(chunk)
                for item in items or []:
                    campaigns_live.append(
                        item.to_dict() if hasattr(item, "to_dict") else jsonable(item)
                    )
            except Exception as exc:  # noqa: BLE001
                gaps.append(f"get_adverts_v2:{type(exc).__name__}")

        inventory = _campaign_inventory(campaigns_live, pg_by_adv)
        sku_campaigns = {
            aid: inv
            for aid, inv in inventory.items()
            if nmid in (inv.get("nm_ids") or [])
        }
        for aid in adv_ids_pg:
            sku_campaigns.setdefault(aid, {"adv_id": aid, "nm_ids": _parse_nmids(pg_by_adv.get(aid, {}).get("nmids"))})

        factual_rows: list[dict[str, Any]] = []
        reused_factual: dict[str, Any] | None = None
        if args.orders_artifact and Path(args.orders_artifact).is_file():
            raw = json.loads(Path(args.orders_artifact).read_text(encoding="utf-8"))
            if isinstance(raw, dict) and raw.get("factual_windows"):
                reused_factual = raw["factual_windows"]
                gaps.append("factual_gmv_reused_from_artifact")
            elif isinstance(raw, dict) and raw.get("factual"):
                reused_factual = raw["factual"]
                gaps.append("factual_gmv_reused_from_artifact")
            elif isinstance(raw, dict) and raw.get("WINDOWS_DETAIL"):
                reused_factual = raw["WINDOWS_DETAIL"]
                gaps.append("factual_gmv_reused_from_prior_snapshot")
            elif isinstance(raw, list):
                factual_rows = [r for r in raw if isinstance(r, dict)]
        if not factual_rows and not reused_factual and not args.skip_orders_fetch:
            staging = Path(tempfile.mkdtemp(prefix="sku_econ_orders_"))
            store = RawStore(output_dir=staging)
            budget = ApiCallBudget(max_seconds=600.0, max_api_calls=200)
            date_from = (closed - timedelta(days=35)).isoformat()
            orders_rows, _ = await collect_orders_sales(
                dm, store=store, budget=budget, orders_date_from=date_from, max_pages=30
            )
            factual_rows = [jsonable(r) for r in orders_rows]
            factual_rows = [r for r in factual_rows if isinstance(r, dict)]

        if reused_factual:
            factual_windows = {label: dict(reused_factual.get(label) or {}) for label in windows}
        else:
            sku_rows = [r for r in factual_rows if _read_int(r, "nmId", "nmID") == nmid]
            factual_windows = {
                label: _window_agg(sku_rows, nmid, start, end)
                for label, (start, end) in windows.items()
            }

        spend_by_adv_window: dict[str, dict[int, dict[str, Any]]] = {
            w: {} for w in windows
        }
        daily_series: list[dict[str, Any]] = []
        campaign_perf: dict[int, dict[str, Any]] = {}

        for aid in sorted(sku_campaigns):
            try:
                stats = list(await pm.get_full_adv_stat([aid], stat_dates) or [])
            except Exception as exc:  # noqa: BLE001
                gaps.append(f"fullstats_{aid}:{type(exc).__name__}")
                continue
            by_day: dict[str, dict[str, float]] = {}
            for st in stats:
                st_d = jsonable(st) if not isinstance(st, dict) else st
                for day_row in st_d.get("days") or []:
                    ds = str((jsonable(day_row) if not isinstance(day_row, dict) else day_row).get("date") or "")[:10]
                    if not ds:
                        continue
                    bucket = _stat_bucket(day_row)
                    by_day[ds] = bucket
                    daily_series.append(
                        {
                            "date": ds,
                            "adv_id": aid,
                            **{k: bucket.get(k) for k in ("spend", "views", "clicks", "attributed_orders", "attributed_gmv")},
                        }
                    )
            win_agg: dict[str, Any] = {}
            for label, (start, end) in windows.items():
                spend = views = clicks = orders = gmv = atbs = 0.0
                d = start
                while d <= end:
                    b = by_day.get(d.isoformat(), {})
                    spend += float(b.get("spend") or 0)
                    views += float(b.get("views") or 0)
                    clicks += float(b.get("clicks") or 0)
                    orders += float(b.get("attributed_orders") or 0)
                    gmv += float(b.get("attributed_gmv") or 0)
                    atbs += float(b.get("atbs") or 0)
                    d += timedelta(days=1)
                win_agg[label] = {
                    "spend": round(spend, 2),
                    "views": int(views),
                    "clicks": int(clicks),
                    "attributed_orders": int(orders),
                    "attributed_gmv": round(gmv, 2),
                    "atbs": int(atbs),
                    "ctr_pct": round(100 * clicks / views, 4) if views else None,
                    "cpc_rub": round(spend / clicks, 2) if clicks else None,
                    "cpm_rub": round(1000 * spend / views, 2) if views else None,
                    "cpo_rub": round(spend / orders, 2) if orders else None,
                }
                spend_by_adv_window[label][aid] = win_agg[label]
            campaign_perf[aid] = win_agg

        spend_labels = ("1D", "3D", "7D")
        total_spend = {
            label: round(
                sum(v.get("spend") or 0 for v in spend_by_adv_window[label].values()), 2
            )
            for label in spend_labels
        }

        campaigns_out: list[dict[str, Any]] = []
        for aid, inv in sorted(sku_campaigns.items()):
            pg = pg_by_adv.get(aid, {})
            wb_status = inv.get("wb_status")
            live_active = wb_status in WB_ACTIVE if wb_status is not None else None
            row: dict[str, Any] = {
                "adv_id": aid,
                "wb_status": wb_status,
                "active_live": live_active,
                "payment_type": inv.get("payment_type"),
                "bid_type": inv.get("bid_type"),
                "placements": inv.get("placements"),
                "nm_ids": inv.get("nm_ids"),
                "pg_id": pg.get("id"),
                "bot_active": pg.get("bot_active"),
                "automatic_version": pg.get("automatic_version"),
                "search_adv_id": pg.get("_search_adv_id"),
                "bidder_active": pg.get("bidder_active"),
                "strategy": pg.get("strategy"),
                "aggressiveness": pg.get("aggressiveness"),
                "target_cpo": pg.get("target_price_for_order"),
                "max_cpo": pg.get("max_price_for_order"),
                "ownership": "BOT_LINKED" if str(pg.get("bot_active")).lower() in ("true", "t", "1") else "MANUAL",
            }
            try:
                bal = await pm.get_campaign_budget(aid)
                row["budget_rub"] = getattr(bal, "total", None)
            except Exception:  # noqa: BLE001
                row["budget_rub"] = None
            ns = next(
                (
                    x
                    for c in campaigns_live
                    if _read_int(c, "id", "advertId") == aid
                    for x in (c.get("nm_settings") or [])
                    if isinstance(x, dict) and _read_int(x, "nm_id", "nmId") == nmid
                ),
                None,
            )
            if isinstance(ns, dict):
                bk = ns.get("bids_kopecks") or {}
                row["bids_rub"] = {
                    "search": round(int(bk.get("search") or 0) / 100, 2),
                    "recommendations": round(int(bk.get("recommendations") or 0) / 100, 2),
                }
            row["performance"] = campaign_perf.get(aid, {})
            campaigns_out.append(row)

        active_ids = [c["adv_id"] for c in campaigns_out if c.get("active_live")]
        primary_spend = max(
            ((aid, total_spend["7D"]) for aid in active_ids),
            key=lambda x: x[1],
            default=(None, 0),
        )

        report = {
            "shop_id": shop_id,
            "nmid": nmid,
            "last_fully_closed_day_msk": closed.isoformat(),
            "factual_windows": factual_windows,
            "total_ad_spend_rub": total_spend,
            "gross_sku_drr_pct": {
                label: _drr(total_spend[label], factual_windows[label]["gmv_rub"])
                for label in spend_labels
            },
            "campaigns": campaigns_out,
            "daily_series": sorted(daily_series, key=lambda r: (r["date"], r["adv_id"])),
            "active_campaign_ids": active_ids,
            "primary_current_spend_source": primary_spend[0],
            "gaps": gaps,
            "provenance": {
                "factual_gmv": "supplier orders finishedPrice",
                "spend": "adv/v3/fullstats campaign-level",
                "funnel_not_used_for_drr": True,
            },
        }
        return report
    finally:
        await httpx_handler.shutdown()
        await redis_raw.aclose()


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    p = argparse.ArgumentParser(description="SKU factual ad economics (READ_ONLY)")
    p.add_argument("--shop-id", required=True)
    p.add_argument("--nmid", type=int, required=True)
    p.add_argument("--closed-day", type=date.fromisoformat)
    p.add_argument("--output", type=Path, help="Primary JSON report path")
    p.add_argument(
        "--output-dir",
        type=Path,
        help="Job output directory (writes sku_factual_ad_economics.json + MANIFEST.json)",
    )
    p.add_argument(
        "--orders-artifact",
        type=Path,
        help="Reuse prior supplier-orders JSON snapshot; skips live orders fetch when set with --skip-orders-fetch",
    )
    p.add_argument(
        "--skip-orders-fetch",
        action="store_true",
        help="Do not call statistics-api; use --orders-artifact factual block only",
    )
    return p.parse_args(argv)


async def _main_async(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    if not args.output and not args.output_dir:
        raise SystemExit("Provide --output or --output-dir")
    report = await _collect(args)
    out_path = args.output
    if args.output_dir:
        args.output_dir.mkdir(parents=True, exist_ok=True)
        out_path = args.output_dir / "sku_factual_ad_economics.json"
        manifest = {
            "primary": out_path.name,
            "provenance": report.get("provenance"),
            "shop_id": report.get("shop_id"),
            "nmid": report.get("nmid"),
            "collector": "scripts/a1_sku_factual_ad_economics_collect.py",
        }
        (args.output_dir / "MANIFEST.json").write_text(
            json.dumps(manifest, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
    assert out_path is not None
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(report, ensure_ascii=False))
    return 0


def main() -> None:
    raise SystemExit(asyncio.run(_main_async()))


if __name__ == "__main__":
    main()
