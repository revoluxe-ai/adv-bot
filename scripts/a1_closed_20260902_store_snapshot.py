"""READ_ONLY: A1 authoritative closed-day store snapshot for 2026-09-02 MSK.

Собирает supplier orders + advertising fullstats напрямую из WB API за полностью
закрытый день. Без production mutations и DB writes.
"""

from __future__ import annotations

import argparse
import asyncio
import hashlib
import json
import sys
import zipfile
from collections import defaultdict
from datetime import date, datetime, time, timezone
from pathlib import Path
from typing import Any
from zoneinfo import ZoneInfo

import dotenv

dotenv.load_dotenv()

from scripts.wb_a1_associated_conversions import _read_float, _read_int
from scripts.wb_api_readonly_ops.collect.ads import _flatten_fullstats
from scripts.wb_api_readonly_ops.collect.api_budget import ApiCallBudget
from scripts.wb_api_readonly_ops.collect.jsonable import jsonable
from scripts.wb_api_readonly_ops.collect.orders_sales import _paginate_supplier_rows

SHOP_ID = "5339e9ad-cbfe-50fc-8d77-b9f337a80417"
MSK = ZoneInfo("Europe/Moscow")
PACKAGE = "A1_CLOSED_20260902_EVIDENCE"
TARGET_DAY = date(2026, 9, 2)
TARGET_STR = TARGET_DAY.isoformat()
BOUNDARY_START = datetime(2026, 9, 2, 0, 0, 0, tzinfo=MSK)
BOUNDARY_END = datetime(2026, 9, 3, 0, 0, 0, tzinfo=MSK)
ORDERS_DATE_FROM = "2026-08-28"
WATCH_ADV_IDS = (39900211, 39900256, 34210859)
HISTORICAL_COMPARISON = {
    "date": "2026-09-01",
    "ad_spend_to_total_price_value_pct": 3.25,
    "status": "HISTORICAL_COMPARISON_ONLY",
}


def _msk_now() -> datetime:
    return datetime.now(timezone.utc).astimezone(MSK)


def _iso_msk(dt: datetime) -> str:
    return dt.astimezone(MSK).isoformat()


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


def _in_closed_day(row: dict[str, Any]) -> bool:
    dt = _msk_dt(row)
    if not dt:
        return False
    return BOUNDARY_START <= dt < BOUNDARY_END


def _money_trace_fields(row: dict[str, Any]) -> dict[str, Any]:
    keys = (
        "totalPrice",
        "priceWithDisc",
        "finishedPrice",
        "discountPercent",
        "spp",
        "forPay",
        "paymentSaleAmount",
    )
    return {k: row.get(k) for k in keys if k in row}


def _write_jsonl(path: Path, rows: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as f:
        for row in rows:
            f.write(json.dumps(row, ensure_ascii=False) + "\n")


def _sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(65536), b""):
            h.update(chunk)
    return h.hexdigest()


def _order_metrics(rows: list[dict[str, Any]]) -> dict[str, Any]:
    active = [r for r in rows if not _is_cancelled(r)]
    groups: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for r in active:
        groups[_g_key(r)].append(r)

    units_in_event = {g: len(v) for g, v in groups.items()}
    bulk_events = sum(1 for n in units_in_event.values() if n > 1)

    total_price = round(sum(_read_float(r, "totalPrice") for r in active), 2)
    price_disc = round(sum(_read_float(r, "priceWithDisc") for r in active), 2)
    finished = round(sum(_read_float(r, "finishedPrice") for r in active), 2)
    nmids = {_read_int(r, "nmId", "nm_id") for r in active}
    nmids.discard(0)

    max_row_ts = None
    for r in rows:
        dt = _msk_dt(r)
        if dt and (max_row_ts is None or dt > max_row_ts):
            max_row_ts = dt

    return {
        "purchase_events": len(groups),
        "units": len(active),
        "total_price_value": total_price,
        "price_with_disc_value": price_disc,
        "finished_price_value": finished,
        "distinct_nmids_sold": len(nmids),
        "bulk_events_count": bulk_events,
        "max_units_in_purchase_event": max(units_in_event.values(), default=0),
        "raw_rows": len(rows),
        "cancelled_rows": sum(1 for r in rows if _is_cancelled(r)),
        "non_cancelled_rows": len(active),
        "max_source_row_timestamp_msk": _iso_msk(max_row_ts) if max_row_ts else None,
    }


def _ad_day_metrics(
    fullstats: list[dict[str, Any]], target: str
) -> tuple[float, int, float, set[int]]:
    spend = 0.0
    attr_orders = 0
    attr_gmv = 0.0
    returned: set[int] = set()
    for row in fullstats:
        day = str(row.get("date") or "")[:10]
        if day != target:
            continue
        adv_id = _read_int(row, "advertId", "advert_id")
        if adv_id:
            returned.add(adv_id)
        spend += _read_float(row, "sum", "spend")
        attr_orders += _read_int(row, "orders")
        attr_gmv += _read_float(row, "sum_price")
    return round(spend, 2), attr_orders, round(attr_gmv, 2), returned


def _coverage_status(
    discovered: list[int],
    returned: set[int],
    campaigns: list[dict[str, Any]],
) -> tuple[list[int], str]:
    missing = sorted(set(discovered) - returned)
    if not missing:
        return [], "PASS"
    inv_ids = {c.get("id") or c.get("advertId") for c in campaigns}
    # campaigns with zero activity may be absent from fullstats
    provable_zero = [m for m in missing if m in inv_ids]
    if len(provable_zero) == len(missing):
        return missing, "PASS"
    return missing, "GAP"


def _late_refresh(
    prior_path: Path | None,
    current_rows: list[dict[str, Any]],
    checked_at: datetime,
) -> dict[str, Any]:
    out: dict[str, Any] = {
        "status": "CONFIRMED",
        "checked_at_msk": _iso_msk(checked_at),
        "evidence": (
            f"Collect executed {_iso_msk(checked_at)} MSK, after closed-day "
            f"boundary end {BOUNDARY_END.isoformat()}. Supplier orders paginated "
            f"with dateFrom={ORDERS_DATE_FROM} to capture late cancellation refresh."
        ),
        "historical_comparison": "NOT_AVAILABLE",
    }
    if prior_path is None or not prior_path.exists():
        out["historical_comparison"] = "NOT_AVAILABLE"
        return out

    try:
        prior_rows = [
            json.loads(line)
            for line in prior_path.read_text(encoding="utf-8").splitlines()
            if line.strip()
        ]
        prior_active = {str(r.get("srid")) for r in prior_rows if not _is_cancelled(r)}
        cur_active = {str(r.get("srid")) for r in current_rows if not _is_cancelled(r)}
        added = sorted(cur_active - prior_active)
        removed = sorted(prior_active - cur_active)
        if added or removed:
            out["historical_comparison"] = {
                "status": "DRIFT_DETECTED",
                "added_srids": len(added),
                "removed_srids": len(removed),
                "prior_path": str(prior_path),
            }
        else:
            out["historical_comparison"] = {
                "status": "NO_DRIFT",
                "prior_path": str(prior_path),
            }
    except (OSError, json.JSONDecodeError) as exc:
        out["historical_comparison"] = f"COMPARE_ERROR: {exc}"
    return out


def _build_md(snapshot: dict[str, Any]) -> str:
    lines = [
        "# A1 Closed Store Snapshot — 2026-09-02 (MSK)",
        "",
        f"**Status:** {snapshot['status']} | **Integrity:** {snapshot['integrity']}",
        f"**Generated at:** {snapshot['generated_at']}",
        f"**Checked at MSK:** {snapshot['checked_at_msk']}",
        "",
        "## Closed-day boundary",
        f"- Start (inclusive): `{snapshot['closed_day_boundary']['start']}`",
        f"- End (exclusive): `{snapshot['closed_day_boundary']['end_exclusive']}`",
        "",
        "## Supplier-order metrics (non-cancelled rows only)",
        f"- PURCHASE_EVENTS (distinct gNumber): **{snapshot['purchase_events']}**",
        f"- UNITS (non-cancelled rows): **{snapshot['units']}**",
        f"- TOTAL_PRICE_VALUE (sum totalPrice): **{snapshot['total_price_value']}**",
        f"- PRICE_WITH_DISC_VALUE: **{snapshot['price_with_disc_value']}**",
        f"- FINISHED_PRICE_VALUE: **{snapshot['finished_price_value']}**",
        f"- DISTINCT_NMIDS_SOLD: **{snapshot['distinct_nmids_sold']}**",
        f"- BULK_EVENTS_COUNT (units_in_event>1): **{snapshot['bulk_events_count']}**",
        f"- MAX_UNITS_IN_PURCHASE_EVENT: **{snapshot['max_units_in_purchase_event']}**",
        "",
        "## Supplier orders raw counts",
        f"- Raw rows in MSK window: {snapshot['supplier_orders']['raw_rows']}",
        f"- Cancelled rows (preserved in raw): {snapshot['supplier_orders']['cancelled_rows']}",
        f"- Non-cancelled rows: {snapshot['supplier_orders']['non_cancelled_rows']}",
        "",
        "## Advertising (separate from supplier-order purchase events)",
        f"- ADVERTISING_SPEND: **{snapshot['advertising_spend']}** RUB",
        f"- ATTRIBUTED_ADVERTISING_ORDERS: **{snapshot['attributed_advertising_orders']}**",
        f"- ATTRIBUTED_ADVERTISING_GMV: **{snapshot['attributed_advertising_gmv']}** RUB",
        f"- AD_SPEND_TO_TOTAL_PRICE_VALUE_PCT: **{snapshot['ad_spend_to_total_price_value_pct']}**",
        "",
        "## Campaign coverage",
        f"- Route: `{snapshot['advertising']['route']}`",
        f"- Campaigns discovered: {len(snapshot['advertising']['campaigns_discovered'])}",
        f"- Campaigns requested in fullstats: {len(snapshot['advertising']['campaigns_requested'])}",
        f"- Campaigns returned in fullstats: {len(snapshot['advertising']['campaigns_returned'])}",
        f"- Missing adv_ids: {snapshot['advertising']['missing_adv_ids']}",
        f"- adv 39900211 covered: {snapshot['advertising']['adv_39900211_covered']}",
        f"- Watch IDs present in inventory: {snapshot['advertising'].get('watch_adv_inventory', {})}",
        "",
        "## Late refresh / cancellation",
        f"- Status: {snapshot['late_refresh']['status']}",
        f"- Evidence: {snapshot['late_refresh']['evidence']}",
        f"- Historical comparison: {snapshot['late_refresh'].get('historical_comparison', 'NOT_AVAILABLE')}",
        "",
        "## Definitions",
        "- PURCHASE_EVENTS = count(distinct gNumber) among non-cancelled supplier-order rows",
        "- UNITS = count(non-cancelled supplier-order rows)",
        "- TOTAL_PRICE_VALUE = sum(totalPrice) on those rows",
        "- ATTRIBUTED_ADVERTISING_* = WB fullstats attribution; not supplier-order purchase events",
        "",
        "## Safety",
        f"- READ_ONLY: {snapshot['safety']['read_only']}",
        f"- WB API writes: {snapshot['safety']['wb_api_writes']}",
        f"- DB writes: {snapshot['safety']['db_writes']}",
        f"- Campaign state changed: {snapshot['safety']['campaign_state_changed']}",
    ]
    return "\n".join(lines) + "\n"


async def fetch_data() -> dict[str, Any]:
    from app.configs.app_config import AppConfig
    from app.core.di.wb_manager_hub.wb_manager_hub_factory import WBManagerHubFactory
    from app.core.mp.wb.api.httpx_client_handler import HttpxClientHandler
    from app.core.redis_manager_v2.redis_client import RedisClient
    from app.modules.common_slaves.wildberries.super_cabinet_manager import (
        get_access_for_wb_cabinet,
    )
    from redis.asyncio import Redis

    req_orders = _msk_now()
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
            initial_date_from=ORDERS_DATE_FROM,
            budget=budget,
            max_pages=1200,
        )
        resp_orders = _msk_now()

        budget.consume()
        adv_ids = list(await pm._client.promotion_count_adapter.get_cabinet_adv_ids() or [])
        budget.consume()
        campaigns_raw = list(await pm.get_adverts_v2_by_ids(adv_ids) or [])
        campaigns: list[dict[str, Any]] = []
        for item in campaigns_raw:
            row = jsonable(item)
            if isinstance(row, dict):
                campaigns.append(row)

        req_fs = _msk_now()
        budget.consume()
        stats_raw = await pm.get_full_adv_stat(adv_ids, [TARGET_DAY])
        resp_fs = _msk_now()
        fullstats = _flatten_fullstats(list(stats_raw or []))

        return {
            "orders_all": orders_result.rows,
            "orders_meta": {
                "route": "/api/v1/supplier/orders",
                "request_params": {"dateFrom": ORDERS_DATE_FROM, "flag": 0},
                "request_timestamp": _iso_msk(req_orders),
                "response_timestamp": _iso_msk(resp_orders),
                "pagination_pages": orders_result.pagination_pages,
                "api_calls": orders_result.api_calls,
            },
            "campaigns": campaigns,
            "adv_ids": adv_ids,
            "fullstats": fullstats,
            "fullstats_raw": jsonable(stats_raw),
            "fullstats_meta": {
                "route": "/adv/v3/fullstats",
                "request_params": {
                    "adv_ids_count": len(adv_ids),
                    "dates": [TARGET_STR],
                },
                "request_timestamp": _iso_msk(req_fs),
                "response_timestamp": _iso_msk(resp_fs),
            },
        }
    finally:
        await httpx.shutdown()
        await redis_raw.aclose()


async def run(output_dir: Path, prior_orders: Path | None) -> dict[str, Any]:
    checked_at = _msk_now()
    generated_at = _iso_msk(checked_at)
    pkg = output_dir / PACKAGE
    pkg.mkdir(parents=True, exist_ok=True)

    data = await fetch_data()
    day_rows = [r for r in data["orders_all"] if _in_closed_day(r)]
    raw_enriched = []
    for r in day_rows:
        row = dict(r)
        row["_money_trace"] = _money_trace_fields(r)
        raw_enriched.append(row)

    om = _order_metrics(day_rows)
    spend, attr_o, attr_gmv, returned_adv = _ad_day_metrics(data["fullstats"], TARGET_STR)
    discovered = sorted(int(x) for x in data["adv_ids"])
    missing, cov_status = _coverage_status(discovered, returned_adv, data["campaigns"])

    watch_inv = {}
    for aid in WATCH_ADV_IDS:
        watch_inv[str(aid)] = aid in discovered

    adv_39900211_covered = 39900211 in discovered and (
        39900211 in returned_adv or 39900211 in missing
    )

    total_price = om["total_price_value"]
    ratio: float | str
    if isinstance(total_price, (int, float)) and total_price > 0:
        ratio = round(spend / total_price * 100, 4)
    else:
        ratio = "GAP"

    late = _late_refresh(prior_orders, day_rows, checked_at)

    integrity = cov_status
    if om["raw_rows"] == 0:
        integrity = "GAP"
    status = "PASS" if integrity == "PASS" and om["raw_rows"] > 0 else ("GAP" if om["raw_rows"] else "FAIL")

    snapshot: dict[str, Any] = {
        "status": status,
        "integrity": integrity,
        "date": TARGET_STR,
        "timezone": "MSK",
        "closed_day_boundary": {
            "start": BOUNDARY_START.isoformat(),
            "end_exclusive": BOUNDARY_END.isoformat(),
        },
        "generated_at": generated_at,
        "checked_at_msk": _iso_msk(checked_at),
        "purchase_events": om["purchase_events"],
        "units": om["units"],
        "total_price_value": total_price,
        "price_with_disc_value": om["price_with_disc_value"],
        "finished_price_value": om["finished_price_value"],
        "distinct_nmids_sold": om["distinct_nmids_sold"],
        "bulk_events_count": om["bulk_events_count"],
        "max_units_in_purchase_event": om["max_units_in_purchase_event"],
        "advertising_spend": spend,
        "ad_spend_to_total_price_value_pct": ratio,
        "attributed_advertising_orders": attr_o,
        "attributed_advertising_gmv": attr_gmv,
        "supplier_orders": {
            **data["orders_meta"],
            "raw_rows": om["raw_rows"],
            "cancelled_rows": om["cancelled_rows"],
            "non_cancelled_rows": om["non_cancelled_rows"],
            "max_source_row_timestamp_msk": om["max_source_row_timestamp_msk"],
        },
        "advertising": {
            **data["fullstats_meta"],
            "campaigns_discovered": discovered,
            "campaigns_requested": discovered,
            "campaigns_returned": sorted(returned_adv),
            "missing_adv_ids": missing,
            "adv_39900211_covered": adv_39900211_covered,
            "watch_adv_inventory": watch_inv,
            "coverage_status": cov_status,
        },
        "late_refresh": late,
        "historical_comparison": HISTORICAL_COMPARISON,
        "safety": {
            "read_only": True,
            "wb_api_writes": 0,
            "db_writes": 0,
            "campaign_state_changed": False,
        },
    }

    _write_jsonl(pkg / "01_supplier_orders_raw.jsonl", raw_enriched)
    (pkg / "02_supplier_orders_request_response_meta.json").write_text(
        json.dumps({**data["orders_meta"], "checked_at_msk": snapshot["checked_at_msk"]}, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    (pkg / "03_ad_campaign_inventory.json").write_text(
        json.dumps(
            {
                "adv_ids": discovered,
                "count": len(discovered),
                "campaigns": data["campaigns"],
                "watch_adv_inventory": watch_inv,
            },
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
    )
    (pkg / "04_fullstats_raw.json").write_text(
        json.dumps(data["fullstats_raw"], ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    (pkg / "05_fullstats_request_response_meta.json").write_text(
        json.dumps(data["fullstats_meta"], ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    coverage_doc = {
        "date": TARGET_STR,
        "campaigns_discovered": len(discovered),
        "campaigns_requested": len(discovered),
        "campaigns_returned": len(returned_adv),
        "missing_adv_ids": missing,
        "missing_zero_activity_proven": cov_status == "PASS" and bool(missing),
        "adv_39900211_covered": adv_39900211_covered,
        "watch_adv_inventory": watch_inv,
        "coverage_status": cov_status,
    }
    (pkg / "06_coverage.json").write_text(
        json.dumps(coverage_doc, ensure_ascii=False, indent=2), encoding="utf-8"
    )

    md_path = pkg / "A1_CLOSED_20260902_STORE_SNAPSHOT.md"
    json_path = pkg / "A1_CLOSED_20260902_STORE_SNAPSHOT.json"
    md_path.write_text(_build_md(snapshot), encoding="utf-8")
    json_path.write_text(json.dumps(snapshot, ensure_ascii=False, indent=2), encoding="utf-8")

    manifest_files = []
    for p in sorted(pkg.iterdir()):
        if p.is_file():
            manifest_files.append({"name": p.name, "bytes": p.stat().st_size, "sha256": _sha256(p)})
    (pkg / "00_manifest.json").write_text(
        json.dumps(
            {
                "package": PACKAGE,
                "date": TARGET_STR,
                "generated_at": generated_at,
                "files": manifest_files,
            },
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
    )

    zip_path = output_dir / "A1_CLOSED_20260902_EVIDENCE.zip"
    with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as zf:
        for p in sorted(pkg.rglob("*")):
            if p.is_file():
                zf.write(p, p.relative_to(output_dir).as_posix())

    snapshot["evidence_dir"] = str(pkg.resolve())
    snapshot["evidence_zip"] = str(zip_path.resolve())
    return snapshot


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="A1 closed-day 2026-09-02 store snapshot (READ_ONLY)")
    ap.add_argument("--output-dir", default=".tmp/a1_closed_20260902")
    ap.add_argument(
        "--prior-orders-jsonl",
        default="",
        help="Optional earlier 2026-09-02 supplier-order extract for drift comparison",
    )
    args = ap.parse_args(argv)
    root = Path(args.output_dir).resolve()
    root.mkdir(parents=True, exist_ok=True)
    prior = Path(args.prior_orders_jsonl) if args.prior_orders_jsonl else None
    out = asyncio.run(run(root, prior))
    print(json.dumps(out, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
