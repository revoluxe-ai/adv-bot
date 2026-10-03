"""READ_ONLY reissue: rebuild A1 daily spend package from saved collect_v2 zip.

Без нового production collect. Исправляет loader paths и false-zero semantics.
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import subprocess
import sys
import zipfile
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from zoneinfo import ZoneInfo

import dotenv

dotenv.load_dotenv()

from scripts.a1_daily_spend_control_reconciliation import (
    ACTIVE_STATUSES,
    ADS_FROM,
    ADS_TO,
    H1_AUTO,
    H1_SEARCH,
    PORTFOLIO_TARGETS,
    SHOP_ID,
    TARGET_DAYS,
    _aggregate_fullstats,
    _build_campaign_daily_spend,
    _build_code_trace_md,
    _build_control_matrix,
    _campaign_inventory,
    _feasibility_verdict,
    _h1_status,
    _int_limit,
    _pg_by_adv_id,
    _portfolio_cap_sum,
    _portfolio_simulation,
    _top_spend_29,
    _watchdog_on,
    _write_csv,
)
from scripts.wb_a1_associated_conversions import _read_float, _read_int
from scripts.wb_api_readonly_ops.collect_layout import (
    COLLECT_V2_CAMPAIGNS_JSONL,
    COLLECT_V2_FULLSTATS_JSONL,
    COLLECT_V2_FUNNEL_JSONL,
    COLLECT_V2_ORDERS_JSONL,
    LEGACY_FUNNEL_JSONL,
    LEGACY_ORDERS_JSONL,
    read_jsonl_from_zip,
)

MSK = ZoneInfo("Europe/Moscow")
SOURCE_JOB = "ops-script-a1-daily-spend-20260830-142500"
SOURCE_PACKAGE = "A1-DAILY-SPEND-CONTROL-AND-20260829-RECONCILIATION"
REISSUE_PACKAGE = "A1-DAILY-SPEND-CONTROL-AND-20260829-RECONCILIATION-AUTHORITATIVE-REISSUE"


def _order_day(row: dict[str, Any]) -> str:
    return str(row.get("date") or row.get("lastChangeDate") or "")[:10]


def _orders_store_daily(rows: list[dict[str, Any]]) -> tuple[dict[str, dict[str, Any]], dict[str, Any]]:
    """Factual supplier orders by day + loader metadata."""
    by_day: dict[str, dict[str, Any]] = defaultdict(
        lambda: {
            "factual_orders": 0,
            "factual_units": 0,
            "factual_order_value_rub": 0.0,
            "unique_nmids": set(),
            "last_change_dates": [],
        }
    )
    for row in rows:
        day = _order_day(row)
        if day not in TARGET_DAYS:
            continue
        nmid = _read_int(row, "nmId", "nm_id", "nmid")
        qty = _read_int(row, "quantity", "qty") or 1
        price = _read_float(row, "totalPrice", "finishedPrice", "priceWithDisc")
        bucket = by_day[day]
        bucket["factual_orders"] += 1
        bucket["factual_units"] += qty
        bucket["factual_order_value_rub"] += price
        if nmid:
            bucket["unique_nmids"].add(nmid)
        lcd = str(row.get("lastChangeDate") or "")
        if lcd:
            bucket["last_change_dates"].append(lcd)

    out: dict[str, dict[str, Any]] = {}
    for day in TARGET_DAYS:
        raw = by_day.get(day)
        if not raw:
            out[day] = {
                "factual_orders": None,
                "factual_units": None,
                "factual_order_value_rub": None,
                "unique_nmids_count": None,
                "orders_semantics": "GET /api/v1/supplier/orders — factual supplier order events",
                "orders_status": "MISSING",
                "last_change_date_min": None,
                "last_change_date_max": None,
            }
            continue
        lcds = raw["last_change_dates"]
        out[day] = {
            "factual_orders": raw["factual_orders"],
            "factual_units": raw["factual_units"],
            "factual_order_value_rub": round(raw["factual_order_value_rub"], 2),
            "unique_nmids_count": len(raw["unique_nmids"]),
            "orders_semantics": "GET /api/v1/supplier/orders — row count = order events; units from quantity",
            "orders_status": "AVAILABLE",
            "last_change_date_min": min(lcds) if lcds else None,
            "last_change_date_max": max(lcds) if lcds else None,
        }
    meta = {
        "orders_rows_total": len(rows),
        "loader_path": COLLECT_V2_ORDERS_JSONL,
        "layout": "collect_v2",
    }
    return out, meta


def _funnel_store_daily(rows: list[dict[str, Any]]) -> dict[str, dict[str, Any]]:
    """Sales Funnel nm×day flat rows (collect_v2) aggregated to store/day."""
    by_day: dict[str, dict[str, float]] = defaultdict(
        lambda: {
            "funnel_order_count": 0.0,
            "funnel_order_sum": 0.0,
            "funnel_add_to_cart": 0.0,
            "funnel_open_card": 0.0,
        }
    )
    days_seen: set[str] = set()
    for row in rows:
        day = str(row.get("day") or row.get("date") or row.get("dt") or "")[:10]
        if not day:
            continue
        if day in TARGET_DAYS:
            days_seen.add(day)
            by_day[day]["funnel_order_count"] += float(row.get("orders") or row.get("orderCount") or 0)
            by_day[day]["funnel_order_sum"] += float(
                row.get("orders_sum") or row.get("orderSum") or row.get("order_sum") or 0
            )
            by_day[day]["funnel_add_to_cart"] += float(
                row.get("add_to_cart") or row.get("addToCart") or 0
            )
            by_day[day]["funnel_open_card"] += float(
                row.get("open_card") or row.get("openCard") or 0
            )

    out: dict[str, dict[str, Any]] = {}
    for day in TARGET_DAYS:
        if day not in days_seen:
            out[day] = {
                "funnel_order_count": None,
                "funnel_order_sum": None,
                "funnel_add_to_cart": None,
                "funnel_open_card": None,
                "funnel_semantics": "POST /api/analytics/v3/sales-funnel/products/history — store sum over nm×day",
                "funnel_status": "GAP",
            }
            continue
        vals = by_day[day]
        status = "AVAILABLE"
        if vals["funnel_order_count"] == 0 and vals["funnel_order_sum"] == 0:
            status = "FACTUAL_ZERO"
        out[day] = {
            **{k: round(v, 2) if isinstance(v, float) else v for k, v in vals.items()},
            "funnel_semantics": "POST /api/analytics/v3/sales-funnel/products/history — store sum over nm×day",
            "funnel_status": status,
        }
    return out


def _orders_by_nm_day(rows: list[dict[str, Any]]) -> dict[tuple[int, str], dict[str, Any]]:
    agg: dict[tuple[int, str], dict[str, Any]] = {}
    for row in rows:
        day = _order_day(row)
        nmid = _read_int(row, "nmId", "nm_id", "nmid")
        if not day or not nmid:
            continue
        qty = _read_int(row, "quantity", "qty") or 1
        price = _read_float(row, "totalPrice", "finishedPrice", "priceWithDisc")
        key = (nmid, day)
        bucket = agg.setdefault(
            key,
            {"nm_id": nmid, "date": day, "factual_orders": 0, "factual_units": 0, "factual_order_value_rub": 0.0},
        )
        bucket["factual_orders"] += 1
        bucket["factual_units"] += qty
        bucket["factual_order_value_rub"] += price
    return agg


def _build_store_rows(
    orders_daily: dict[str, dict[str, Any]],
    funnel_daily: dict[str, dict[str, Any]],
    store_spend: dict[str, float],
    *,
    prior_store_csv: Path | None,
) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    prior: dict[str, dict[str, str]] = {}
    if prior_store_csv and prior_store_csv.exists():
        with prior_store_csv.open(encoding="utf-8", newline="") as handle:
            for row in csv.DictReader(handle):
                prior[row["date"]] = row

    for day in TARGET_DAYS:
        od = orders_daily.get(day, {})
        fd = funnel_daily.get(day, {})
        revision_note = ""
        if day in prior:
            old_orders = prior[day].get("factual_orders", "0")
            new_orders = od.get("factual_orders")
            if old_orders in ("0", "", "None") and new_orders not in (None, 0, "0"):
                revision_note = "LOADER_ERROR_REVISED"
            elif old_orders not in ("0", "", "None") and new_orders is not None:
                if str(old_orders) != str(new_orders):
                    revision_note = "HISTORICAL_ROW_REVISED_BY_LATER_API_STATE"

        rows.append(
            {
                "date": day,
                "day_state": "OPEN_PARTIAL" if day == "2026-08-30" else "CLOSED",
                "factual_orders": od.get("factual_orders"),
                "factual_units": od.get("factual_units"),
                "factual_order_value_rub": od.get("factual_order_value_rub"),
                "unique_nmids_count": od.get("unique_nmids_count"),
                "orders_status": od.get("orders_status"),
                "orders_semantics": od.get("orders_semantics"),
                "last_change_date_min": od.get("last_change_date_min"),
                "last_change_date_max": od.get("last_change_date_max"),
                "funnel_order_count": fd.get("funnel_order_count"),
                "funnel_order_sum": fd.get("funnel_order_sum"),
                "funnel_add_to_cart": fd.get("funnel_add_to_cart"),
                "funnel_open_card": fd.get("funnel_open_card"),
                "funnel_status": fd.get("funnel_status"),
                "funnel_semantics": fd.get("funnel_semantics"),
                "store_total_ad_spend_rub": round(float(store_spend.get(day, 0)), 2),
                "revision_note": revision_note,
            }
        )
    return rows


def _matrix_row_to_pg(row: dict[str, Any]) -> dict[str, str]:
    return {
        "adv_id": str(row.get("adv_id_auto") or ""),
        "_search_adv_id": str(row.get("adv_id_search") or ""),
        "auto_budget_watchdog_enabled": str(row.get("watchdog_enabled") or ""),
        "auto_budget_daily_limit": str(row.get("auto_budget_daily_limit") or "0"),
        "search_auto_budget_daily_limit": str(row.get("search_auto_budget_daily_limit") or "0"),
        "use_common_budget": str(row.get("use_common_budget") or ""),
        "common_budget_daily_limit": str(row.get("common_budget_daily_limit") or "0"),
        "bot_active": str(row.get("bot_linked") or ""),
        "active_status": str(row.get("active_status") or ""),
        "aggressiveness": str(row.get("aggressiveness") or ""),
        "strategy": str(row.get("strategy") or ""),
        "max_balance_adding_for_day": str(row.get("max_balance_adding_for_day") or ""),
    }


def _daily_cap_configurable(row: dict[str, str]) -> str:
    """Можно ли включить daily cap через существующий bot mechanism."""
    adv_type = str(row.get("type") or "")
    if adv_type and adv_type not in ("8", "9", "AUTO", "SEARCH"):
        return "GAP"
    return "YES"


def _classify_cap_row(
    pg_row: dict[str, str],
    spend_29: float,
    *,
    adv_id_auto: int,
) -> tuple[str, str]:
    """Вернуть (classification, daily_cap_configurable)."""
    watchdog = _watchdog_on(pg_row)
    if str(pg_row.get("use_common_budget")).lower() in ("true", "t", "1"):
        enforceable = _int_limit(pg_row.get("common_budget_daily_limit"))
    else:
        enforceable = _int_limit(pg_row.get("auto_budget_daily_limit")) + _int_limit(
            pg_row.get("search_auto_budget_daily_limit")
        )
    auto_lim = _int_limit(pg_row.get("auto_budget_daily_limit"))
    search_lim = _int_limit(pg_row.get("search_auto_budget_daily_limit"))

    if adv_id_auto in H1_AUTO and auto_lim == 0:
        return "ENFORCED_STOPPED_OR_NONSPENDING", "YES"

    if watchdog and enforceable > 0:
        return "ACTIVE_WITH_ENFORCEABLE_DAILY_CAP", _daily_cap_configurable(pg_row)

    if watchdog and auto_lim == 0 and search_lim == 0 and enforceable == 0:
        if spend_29 <= 0.01:
            return "ENFORCED_STOPPED_OR_NONSPENDING", "YES"
        return "ACTIVE_WITHOUT_CURRENT_DAILY_CAP", _daily_cap_configurable(pg_row)

    if spend_29 > 0:
        return "ACTIVE_WITHOUT_CURRENT_DAILY_CAP", _daily_cap_configurable(pg_row)

    return "ENFORCED_STOPPED_OR_NONSPENDING", _daily_cap_configurable(pg_row)


def _enhance_matrix(
    matrix: list[dict[str, Any]],
    pg_by_adv: dict[int, dict[str, str]],
) -> tuple[list[dict[str, Any]], dict[str, list[dict[str, Any]]]]:
    groups: dict[str, list[dict[str, Any]]] = {
        "ENFORCED_STOPPED_OR_NONSPENDING": [],
        "ACTIVE_WITH_ENFORCEABLE_DAILY_CAP": [],
        "ACTIVE_WITHOUT_CURRENT_DAILY_CAP": [],
    }
    enhanced: list[dict[str, Any]] = []
    for row in matrix:
        auto_id = int(row.get("adv_id_auto") or 0)
        pg_row = pg_by_adv.get(auto_id, _matrix_row_to_pg(row))
        spend_29 = float(row.get("spend_2026_08_29") or 0)
        classification, configurable = _classify_cap_row(pg_row, spend_29, adv_id_auto=auto_id)
        new_row = {
            **row,
            "daily_cap_classification": classification,
            "daily_cap_configurable": configurable,
        }
        enhanced.append(new_row)
        groups[classification].append(new_row)
    return enhanced, groups


def _enhanced_top_spend(top29: list[dict[str, Any]], orders_nm: dict[tuple[int, str], dict[str, Any]]) -> list[dict[str, Any]]:
    day = "2026-08-29"
    rows: list[dict[str, Any]] = []
    for row in top29:
        nmid = _read_int({"primary_nm_id": row.get("primary_nm_id")}, "primary_nm_id")
        nm = orders_nm.get((nmid, day), {}) if nmid else {}
        rows.append(
            {
                **row,
                "nmID": nmid,
                "factual_sku_orders": nm.get("factual_orders", 0),
                "factual_sku_units": nm.get("factual_units", 0),
                "factual_sku_order_value_rub": round(float(nm.get("factual_order_value_rub") or 0), 2),
                "factual_sku_source": COLLECT_V2_ORDERS_JSONL,
                "attributed_orders_note": "WB fullstats attributed — not causal vs factual SKU",
            }
        )
    return rows


def _integrity_gate(
    *,
    orders_rows: int,
    orders_path_used: str,
    store_rows: list[dict[str, Any]],
    top29: list[dict[str, Any]],
) -> tuple[str, list[str]]:
    errors: list[str] = []
    if orders_path_used != COLLECT_V2_ORDERS_JSONL:
        errors.append(f"orders_path_not_canonical: {orders_path_used}")
    if orders_rows <= 0:
        errors.append("orders_rows_zero")
    day29 = next((r for r in store_rows if r["date"] == "2026-08-29"), {})
    if day29.get("orders_status") != "AVAILABLE":
        errors.append("29_08_orders_not_available")
    elif not day29.get("factual_orders"):
        errors.append("29_08_factual_orders_zero_unexpected")
    if not top29:
        errors.append("top_spend_empty")
    for row in store_rows:
        if row.get("orders_status") == "AVAILABLE" and row.get("factual_orders") is None:
            errors.append(f"false_zero_orders_{row['date']}")
    status = "AUTHORITATIVE_REISSUE" if not errors else "BLOCKED"
    return status, errors


def _sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _write_archive(pkg_dir: Path, zip_path: Path) -> str:
    with zipfile.ZipFile(zip_path, "w", compression=zipfile.ZIP_DEFLATED) as zf:
        for path in sorted(pkg_dir.rglob("*")):
            if path.is_file():
                zf.write(path, arcname=path.relative_to(pkg_dir).as_posix())
    return _sha256_file(zip_path)


def build_reissue_package(
    *,
    collect_zip: Path,
    output_dir: Path,
    source_package_json: Path | None,
    collect_report: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Собрать authoritative reissue из collect_v2 zip."""
    checked_msk = datetime.now(timezone.utc).astimezone(MSK)
    prior_csv = None
    if source_package_json and source_package_json.exists():
        prior_dir = source_package_json.parent
        prior_csv = prior_dir / "STORE_DAILY_RESULT.csv"

    with zipfile.ZipFile(collect_zip) as zf:
        orders, orders_path = read_jsonl_from_zip(
            zf, COLLECT_V2_ORDERS_JSONL, legacy=LEGACY_ORDERS_JSONL
        )
        funnel, funnel_path = read_jsonl_from_zip(
            zf, COLLECT_V2_FUNNEL_JSONL, legacy=LEGACY_FUNNEL_JSONL
        )
        fullstats, _ = read_jsonl_from_zip(zf, COLLECT_V2_FULLSTATS_JSONL)
        campaigns, _ = read_jsonl_from_zip(zf, COLLECT_V2_CAMPAIGNS_JSONL)

    if source_package_json and source_package_json.exists():
        old = json.loads(source_package_json.read_text(encoding="utf-8"))
        pg_rows = [_matrix_row_to_pg(r) for r in old.get("CURRENT_DAILY_SPEND_CONTROL_MATRIX", [])]
    else:
        pg_rows = []

    pg_by_adv = _pg_by_adv_id(pg_rows)
    stats = _aggregate_fullstats(fullstats)
    inventory = _campaign_inventory(campaigns, pg_by_adv)
    active_adv_ids = sorted(
        adv_id for adv_id, inv in inventory.items() if inv.get("wb_status") in ACTIVE_STATUSES
    )

    store_spend: dict[str, float] = defaultdict(float)
    for (_adv, day), row in stats.items():
        if day in TARGET_DAYS:
            store_spend[day] += float(row.get("spend") or 0)

    orders_daily, orders_meta = _orders_store_daily(orders)
    funnel_daily = _funnel_store_daily(funnel)
    orders_nm = _orders_by_nm_day(orders)
    store_rows = _build_store_rows(
        orders_daily, funnel_daily, dict(store_spend), prior_store_csv=prior_csv
    )
    campaign_rows = _build_campaign_daily_spend(stats, inventory, pg_by_adv)
    top29 = _enhanced_top_spend(
        _top_spend_29(stats, inventory, orders_nm, float(store_spend.get("2026-08-29", 0))),
        orders_nm,
    )
    matrix = _build_control_matrix(pg_rows, inventory, stats, {})
    matrix, cap_groups = _enhance_matrix(matrix, pg_by_adv)
    portfolio = _portfolio_simulation(matrix, active_adv_ids)
    h1 = _h1_status(pg_by_adv, inventory)
    feasibility = _feasibility_verdict(matrix, len(active_adv_ids))

    active_without_cap = [
        {
            "adv_id": r.get("adv_id_auto"),
            "spend_27": r.get("spend_2026_08_27"),
            "spend_28": r.get("spend_2026_08_28"),
            "spend_29": r.get("spend_2026_08_29"),
            "watchdog_enabled": r.get("watchdog_enabled"),
            "auto_budget_daily_limit": r.get("auto_budget_daily_limit"),
            "search_auto_budget_daily_limit": r.get("search_auto_budget_daily_limit"),
            "daily_cap_configurable": r.get("daily_cap_configurable"),
        }
        for r in cap_groups["ACTIVE_WITHOUT_CURRENT_DAILY_CAP"]
    ]

    package_status, gate_errors = _integrity_gate(
        orders_rows=len(orders),
        orders_path_used=orders_path,
        store_rows=store_rows,
        top29=top29,
    )

    pkg_dir = output_dir / REISSUE_PACKAGE
    pkg_dir.mkdir(parents=True, exist_ok=True)

    store_cols = list(store_rows[0].keys()) if store_rows else ["date"]
    _write_csv(pkg_dir / "STORE_DAILY_RESULT.csv", store_rows, store_cols)
    _write_csv(
        pkg_dir / "CAMPAIGN_DAILY_SPEND.csv",
        campaign_rows,
        list(campaign_rows[0].keys()) if campaign_rows else ["date", "adv_id"],
    )
    _write_csv(
        pkg_dir / "TOP_SPEND_20260829.csv",
        top29,
        list(top29[0].keys()) if top29 else ["adv_id"],
    )
    _write_csv(
        pkg_dir / "CURRENT_DAILY_SPEND_CONTROL_MATRIX.csv",
        matrix,
        list(matrix[0].keys()) if matrix else ["adv_id_auto"],
    )
    (pkg_dir / "DAILY_LIMIT_CODE_TRACE.md").write_text(_build_code_trace_md(), encoding="utf-8")
    _write_csv(
        pkg_dir / "PORTFOLIO_CAP_SIMULATION.csv",
        portfolio,
        list(portfolio[0].keys()) if portfolio else ["total_daily_target_rub"],
    )

    day29 = next((r for r in store_rows if r["date"] == "2026-08-29"), {})
    payload: dict[str, Any] = {
        "package": REISSUE_PACKAGE,
        "PACKAGE_STATUS": package_status,
        "checked_at_msk": checked_msk.strftime("%Y-%m-%d %H:%M:%S %Z"),
        "shop_id": SHOP_ID,
        "mode": "STRICT_READ_ONLY_REISSUE",
        "provenance": {
            "source_job": SOURCE_JOB,
            "source_package": SOURCE_PACKAGE,
            "collect_zip": str(collect_zip.resolve()),
            "collect_layout": "collect_v2",
            "orders_member_path": orders_path,
            "funnel_member_path": funnel_path,
            "ads_date_from": ADS_FROM.isoformat(),
            "ads_date_to": ADS_TO.isoformat(),
            "collect_report": collect_report,
        },
        "coverage": {
            "fullstats_rows": len(fullstats),
            "orders_rows": len(orders),
            "funnel_rows": len(funnel),
            "active_campaigns_wb_status_9": len(active_adv_ids),
            "orders_loader": orders_meta,
        },
        "integrity_gate_errors": gate_errors,
        "STORE_DAILY_RESULT": store_rows,
        "STORE_TOTAL_AD_SPEND_BY_DAY": {d: round(store_spend.get(d, 0), 2) for d in TARGET_DAYS},
        "DAILY_CAP_CLASSIFICATION": {
            k: len(v) for k, v in cap_groups.items()
        },
        "ACTIVE_WITHOUT_CURRENT_DAILY_CAP": active_without_cap,
        "summary": {
            "29_08_STORE_RESULT": day29,
            "29_08_TOTAL_AD_SPEND": round(float(store_spend.get("2026-08-29", 0)), 2),
            "29_08_FACTUAL_ORDERS": day29.get("factual_orders"),
            "29_08_FACTUAL_ORDER_VALUE": day29.get("factual_order_value_rub"),
            "TOP_SPEND_CAMPAIGNS": top29[:10],
            "FULL_CONTOUR_DAILY_CAP_FEASIBILITY": feasibility,
            "H1_STATUS": h1,
            "sum_configured_enforceable_caps_rub": _portfolio_cap_sum(matrix),
        },
    }

    (pkg_dir / f"{REISSUE_PACKAGE}.json").write_text(
        json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8"
    )

    md = [
        f"# {REISSUE_PACKAGE}",
        "",
        f"**PACKAGE_STATUS:** {package_status}",
        f"**checked_at:** {payload['checked_at_msk']}",
        f"**source_job:** `{SOURCE_JOB}`",
        "",
        "## 29.08",
        "",
        f"- Factual orders: **{day29.get('factual_orders')}**",
        f"- Factual order value: **{day29.get('factual_order_value_rub')} ₽**",
        f"- Funnel orders/sum: **{day29.get('funnel_order_count')}** / **{day29.get('funnel_order_sum')} ₽**",
        f"- Ad spend: **{payload['summary']['29_08_TOTAL_AD_SPEND']} ₽**",
        "",
        "## Daily cap classification (active rows)",
        "",
    ]
    for key, count in payload["DAILY_CAP_CLASSIFICATION"].items():
        md.append(f"- **{key}**: {count}")
    md.extend(
        [
            "",
            f"## Portfolio feasibility: **{feasibility['CAN_FULL_ACTIVE_CONTOUR_BE_BOUNDED_TO_A_PREDICTABLE_DAILY_SPEND']}**",
            "",
            f"## H1: **{h1['status']}** ({h1['overall_gate']})",
        ]
    )
    (pkg_dir / "RECONCILIATION.md").write_text("\n".join(md), encoding="utf-8")

    provenance_md = [
        "# SOURCE_PROVENANCE",
        "",
        f"- source_job: `{SOURCE_JOB}`",
        f"- source_package: `{SOURCE_PACKAGE}`",
        f"- collect_zip: `{collect_zip.resolve()}`",
        f"- orders_path: `{orders_path}`",
        f"- funnel_path: `{funnel_path}`",
        f"- reissue_at: {payload['checked_at_msk']}",
        f"- no_production_collect: true",
        f"- no_production_mutations: true",
    ]
    (pkg_dir / "SOURCE_PROVENANCE.md").write_text("\n".join(provenance_md), encoding="utf-8")

    zip_path = output_dir / f"{REISSUE_PACKAGE}.zip"
    archive_sha = _write_archive(pkg_dir, zip_path)
    manifest = {
        "package": REISSUE_PACKAGE,
        "PACKAGE_STATUS": package_status,
        "archive": zip_path.name,
        "archive_sha256": archive_sha,
        "files": sorted(p.relative_to(pkg_dir).as_posix() for p in pkg_dir.rglob("*") if p.is_file()),
        "integrity_gate_errors": gate_errors,
    }
    (pkg_dir / "PACKAGE_MANIFEST.json").write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    _write_archive(pkg_dir, zip_path)

    payload["ARCHIVE_SHA256"] = archive_sha
    payload["ABSOLUTE_ARCHIVE_PATH"] = str(zip_path.resolve())
    payload["output_dir"] = str(pkg_dir.resolve())
    return payload


def _fetch_collect_zip(dest: Path, pod: str, namespace: str = "prod-adv-bot") -> Path:
    dest.parent.mkdir(parents=True, exist_ok=True)
    remote = "/tmp/a1_daily_spend_control/collect/wb_readonly_research.zip"
    data = subprocess.check_output(
        ["kubectl", "exec", "-n", namespace, pod, "--", "cat", remote]
    )
    dest.write_bytes(data)
    return dest


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Reissue A1 daily spend package from collect_v2 zip.")
    parser.add_argument("--output-dir", default=".tmp/a1_daily_spend_control")
    parser.add_argument("--collect-zip", type=Path, default=None)
    parser.add_argument("--source-pod", default="ops-script-a1-daily-spend-20260830-142500-sqgjr")
    parser.add_argument(
        "--source-package-json",
        type=Path,
        default=Path(
            ".tmp/a1_daily_spend_control/A1-DAILY-SPEND-CONTROL-AND-20260829-RECONCILIATION/"
            "A1-DAILY-SPEND-CONTROL-AND-20260829-RECONCILIATION.json"
        ),
    )
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    out = Path(args.output_dir).resolve()
    zip_path = args.collect_zip
    if zip_path is None:
        zip_path = out / "source" / "wb_readonly_research.zip"
        if not zip_path.exists():
            _fetch_collect_zip(zip_path, args.source_pod)
    else:
        zip_path = zip_path.resolve()

    result = build_reissue_package(
        collect_zip=zip_path,
        output_dir=out,
        source_package_json=args.source_package_json.resolve() if args.source_package_json else None,
    )
    sys.stdout.reconfigure(encoding="utf-8")
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0 if result.get("PACKAGE_STATUS") == "AUTHORITATIVE_REISSUE" else 1


if __name__ == "__main__":
    sys.exit(main())
