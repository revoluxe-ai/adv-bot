"""READ_ONLY: A1 current performance / DRR snapshot for Web analytical review.

Собирает store factual sales, gross ad spend по физическому контуру, promo pool,
окна CURRENT/PREVIOUS 3d/7d/14d, category/product dynamics, priority entry snapshot
и delta vs baseline ~2026-09-05. CASH_FLOW_ONLY promo semantics — без выдуманного
cash_drr. Без production mutations.
"""

from __future__ import annotations

import argparse
import asyncio
import csv
import json
import sys
import zipfile
from collections import defaultdict
from datetime import date, datetime, timedelta, timezone
from pathlib import Path
from typing import Any
from zoneinfo import ZoneInfo

import dotenv

dotenv.load_dotenv()

from scripts import ch_a1_evidence as evidence
from scripts.a1_daily_spend_control_reconciliation import (
    _campaign_inventory,
    _pg_by_adv_id,
    _write_csv,
)
from scripts.a1_glue_topology_web_review_collect import (
    CATEGORY_LABELS,
    _all_cards,
    _classify_category,
    _closed_dates,
    _direct_assoc_split,
    _iso_msk,
    _msk_now,
    _nm_to_contours,
    _promoted_set,
    _sales_window,
)
from scripts.a1_promo_adjusted_drr_collect import (
    _bootstrap_cluster_infra,
    _drr_pct,
    _is_cancelled,
    _load_topups,
    _load_wbcabinet,
    _normalize_topup,
    _order_day,
    _pg_database,
)
from scripts.a1_promotion_funding_snapshot import (
    SHOP_ID,
    _api_model_dict,
    _cashbacks_to_list,
    _load_adv_settings,
)
from scripts.wb_a1_associated_conversions import (
    _jsonable,
    _nm_rows,
    _read_float,
    _read_int,
)
from scripts.wb_api_readonly_ops.collect.jsonable import jsonable

MSK = ZoneInfo("Europe/Moscow")
PACKAGE = "A1-CURRENT-PERFORMANCE-DRR-SNAPSHOT"
COLLECT_FROM = date(2026, 8, 25)
BASELINE_DAY = date(2026, 9, 5)
PRIORITY_NMIDS = (14166423, 85970344, 14824677, 837395782, 7974113)
ADJACENT_NMIDS = (4491650, 7974106, 147281596)
ALL_PRIORITY_NMIDS = PRIORITY_NMIDS + ADJACENT_NMIDS
ACCOUNTING_STATUS = "CASH_FLOW_ONLY"
BASELINE_PROMO_ZIP = Path(
    ".tmp/opsx-scripts/20260907-012200/outputs/a1_promo_adjusted_drr.zip"
)
BASELINE_GLUE_ZIP = Path(
    ".tmp/opsx-scripts/20260906-151200/outputs/a1_glue_topology_web_review.zip"
)


def _closed_end_day(now: datetime | None = None) -> date:
    return (now or _msk_now()).date() - timedelta(days=1)


def _open_day(now: datetime | None = None) -> date:
    return (now or _msk_now()).date()


def _day_state(day: date, closed_end: date, open_d: date) -> str:
    if day == open_d:
        return "OPEN"
    if day <= closed_end:
        return "CLOSED"
    return "FUTURE"


def _orders_store_daily(
    orders: list[dict[str, Any]],
    closed_end: date,
    open_d: date,
) -> dict[str, dict[str, Any]]:
    by_day: dict[str, dict[str, Any]] = defaultdict(
        lambda: {"purchase_events": 0, "units": 0, "factual_order_value": 0.0, "cancelled_excluded": 0}
    )
    for row in orders:
        if _is_cancelled(row):
            day = _order_day(row)
            if day:
                by_day[day]["cancelled_excluded"] += 1
            continue
        day = _order_day(row)
        if not day:
            continue
        try:
            d = date.fromisoformat(day)
        except ValueError:
            continue
        if d < COLLECT_FROM or d > open_d:
            continue
        qty = _read_int(row, "quantity", "qty") or 1
        price = _read_float(row, "totalPrice", "priceWithDisc", "finishedPrice")
        bucket = by_day[day]
        bucket["purchase_events"] += 1
        bucket["units"] += qty
        bucket["factual_order_value"] += price * qty if price else price
    out: dict[str, dict[str, Any]] = {}
    d = COLLECT_FROM
    while d <= open_d:
        key = d.isoformat()
        raw = by_day.get(key)
        state = _day_state(d, closed_end, open_d)
        if raw:
            out[key] = {
                "date": key,
                "day_state": state,
                "purchase_events": raw["purchase_events"],
                "units": raw["units"],
                "factual_order_value": round(raw["factual_order_value"], 2),
                "freshness": _iso_msk(_msk_now()),
                "closed_or_open": state,
            }
        else:
            out[key] = {
                "date": key,
                "day_state": state,
                "purchase_events": 0,
                "units": 0,
                "factual_order_value": 0.0,
                "freshness": _iso_msk(_msk_now()),
                "closed_or_open": state,
            }
        d += timedelta(days=1)
    return out


def _gross_spend_daily(
    day_rows: list[dict[str, Any]], closed_end: date, open_d: date
) -> dict[str, dict[str, Any]]:
    by_day: dict[str, float] = defaultdict(float)
    for row in day_rows:
        day = row.get("date", "")
        if not day:
            continue
        try:
            d = date.fromisoformat(day)
        except ValueError:
            continue
        if d < COLLECT_FROM or d > open_d:
            continue
        by_day[day] += float(row.get("day_spend") or 0)
    out: dict[str, dict[str, Any]] = {}
    d = COLLECT_FROM
    while d <= open_d:
        key = d.isoformat()
        spend = round(by_day.get(key, 0.0), 2)
        views = clicks = orders = 0
        gmv = 0.0
        for row in day_rows:
            if row.get("date") != key:
                continue
            views += int(row.get("day_views") or 0)
            clicks += int(row.get("day_clicks") or 0)
            orders += int(row.get("day_orders") or 0)
            gmv += float(row.get("day_sum_price") or 0)
        ctr = round(clicks / views, 6) if views else "GAP"
        out[key] = {
            "date": key,
            "day_state": _day_state(d, closed_end, open_d),
            "gross_ad_spend": spend,
            "views": views,
            "clicks": clicks,
            "ctr": ctr,
            "carts": "GAP",
            "attributed_orders": orders,
            "attributed_gmv": round(gmv, 2),
            "source": "fullstats campaign-day totals (no nm re-sum)",
        }
        d += timedelta(days=1)
    return out


def _topup_daily(
    normalized: list[dict[str, Any]], closed_end: date, open_d: date
) -> dict[str, dict[str, Any]]:
    by_day: dict[str, dict[str, float | int]] = defaultdict(
        lambda: {"promo": 0.0, "ordinary": 0.0, "events": 0}
    )
    for row in normalized:
        if str(row.get("status")) != "success":
            continue
        day = str(row.get("date_msk") or "")[:10]
        if not day:
            continue
        bucket = by_day[day]
        bucket["promo"] += float(row.get("promo_bonus_rub") or 0)
        bucket["ordinary"] += float(row.get("ordinary_funds_rub") or 0)
        bucket["events"] += 1
    out: dict[str, dict[str, Any]] = {}
    d = COLLECT_FROM
    while d <= open_d:
        key = d.isoformat()
        raw = by_day.get(key, {"promo": 0.0, "ordinary": 0.0, "events": 0})
        out[key] = {
            "date": key,
            "promo_used_on_deposits": round(float(raw["promo"]), 2),
            "ordinary_funds_used_on_deposits": round(float(raw["ordinary"]), 2),
        }
        d += timedelta(days=1)
    return out


def _window_specs(closed_end: date) -> list[tuple[str, date, date]]:
    return [
        ("CURRENT_3D", closed_end - timedelta(days=2), closed_end),
        ("PREVIOUS_3D", closed_end - timedelta(days=5), closed_end - timedelta(days=3)),
        ("CURRENT_7D", closed_end - timedelta(days=6), closed_end),
        ("PREVIOUS_7D", closed_end - timedelta(days=13), closed_end - timedelta(days=7)),
        ("CURRENT_14D", closed_end - timedelta(days=13), closed_end),
    ]


def _aggregate_window(
    label: str,
    date_from: date,
    date_to: date,
    sales_daily: dict[str, dict[str, Any]],
    spend_daily: dict[str, dict[str, Any]],
    topup_daily: dict[str, dict[str, Any]],
    closed_end: date,
) -> dict[str, Any]:
    events = units = 0
    sales = spend = promo = ordinary = 0.0
    d = date_from
    while d <= date_to:
        if d > closed_end:
            d += timedelta(days=1)
            continue
        key = d.isoformat()
        sd = sales_daily.get(key, {})
        sp = spend_daily.get(key, {})
        tp = topup_daily.get(key, {})
        events += int(sd.get("purchase_events") or 0)
        units += int(sd.get("units") or 0)
        sales += float(sd.get("factual_order_value") or 0)
        spend += float(sp.get("gross_ad_spend") or 0)
        promo += float(tp.get("promo_used_on_deposits") or 0)
        ordinary += float(tp.get("ordinary_funds_used_on_deposits") or 0)
        d += timedelta(days=1)
    return {
        "window_label": label,
        "period_from": date_from.isoformat(),
        "period_to": date_to.isoformat(),
        "purchase_events": events,
        "units": units,
        "factual_order_value": round(sales, 2),
        "gross_ad_spend": round(spend, 2),
        "gross_drr": _drr_pct(spend, sales),
        "promo_used": round(promo, 2),
        "ordinary_funds_used": round(ordinary, 2),
        "cash_ad_cost": "GAP",
        "cash_drr": "GAP",
        "accounting_status": ACCOUNTING_STATUS,
    }


def _build_nmid_category(cards: list[dict[str, Any]]) -> dict[int, str]:
    out: dict[int, str] = {}
    for card in cards:
        nmid = _read_int(card, "nmID", "nmId", "nmid")
        if not nmid:
            continue
        cat = _classify_category(
            str(card.get("subjectName") or ""),
            str(card.get("title") or ""),
        )
        if cat:
            out[nmid] = cat
    return out


def _category_window_rows(
    orders: list[dict[str, Any]],
    nm_rows: list[dict[str, Any]],
    day_rows: list[dict[str, Any]],
    nm_contours: dict[int, list[dict[str, Any]]],
    nmid_category: dict[int, str],
    closed_end: date,
) -> list[dict[str, Any]]:
    windows = {
        "CURRENT_3D": _closed_dates(closed_end, 3),
        "CURRENT_7D": _closed_dates(closed_end, 7),
        "PREVIOUS_7D": _closed_dates(
            closed_end - timedelta(days=7), 7
        ),
        "CURRENT_14D": _closed_dates(closed_end, 14),
    }
    rows: list[dict[str, Any]] = []
    for cat_key, cat_label in CATEGORY_LABELS.items():
        cat_nmids = {n for n, c in nmid_category.items() if c == cat_key}
        if not cat_nmids:
            rows.append(
                {
                    "category": cat_key,
                    "category_label": cat_label,
                    "window": "ALL",
                    "events": "GAP",
                    "units": "GAP",
                    "factual_order_value": "GAP",
                    "gross_ad_spend": "GAP",
                    "direct_orders": "GAP",
                    "associated_orders": "GAP",
                    "attributed_gmv": "GAP",
                    "gross_ad_load_pct": "GAP",
                    "note": "NO_NMIDS_IN_CATEGORY",
                }
            )
            continue
        adv_ids: set[int] = set()
        for nmid in cat_nmids:
            for c in nm_contours.get(nmid, []):
                if c.get("auto_adv_id"):
                    adv_ids.add(int(c["auto_adv_id"]))
                if c.get("search_adv_id"):
                    adv_ids.add(int(c["search_adv_id"]))
        for win_label, dates in windows.items():
            ev = un = 0
            sales_val = 0.0
            for nmid in cat_nmids:
                sw = _sales_window(orders, nmid, dates)
                ev += sw["events"]
                un += sw["units"]
                sales_val += float(sw["value"])
            spend = 0.0
            direct_o = assoc_o = 0
            gmv = 0.0
            for adv_id in adv_ids:
                promoted = _promoted_set({"id": adv_id})
                for camp in nm_contours.get(next(iter(cat_nmids), 0), []):
                    if camp.get("auto_adv_id") == adv_id or camp.get("search_adv_id") == adv_id:
                        promoted = set()
                        for c in nm_contours.values():
                            for cc in c:
                                if cc.get("auto_adv_id") == adv_id:
                                    promoted |= set(_parse_nmids_json(str(cc.get("nmids_pg") or "[]")))
                subset_nm = [r for r in nm_rows if r["advert_id"] == adv_id and r["date"] in dates]
                split = _direct_assoc_split(subset_nm, promoted or cat_nmids, dates)
                direct_o += split["direct_orders"]
                assoc_o += split["associated_orders"]
                gmv += float(split["direct_gmv"]) + float(split["associated_gmv"])
                spend += sum(
                    r["day_spend"]
                    for r in day_rows
                    if r["advert_id"] == adv_id and r["date"] in dates
                )
            load = _drr_pct(spend, sales_val) if sales_val > 0 else "GAP"
            rows.append(
                {
                    "category": cat_key,
                    "category_label": cat_label,
                    "window": win_label,
                    "events": ev,
                    "units": un,
                    "factual_order_value": round(sales_val, 2),
                    "gross_ad_spend": round(spend, 2),
                    "direct_orders": direct_o,
                    "associated_orders": assoc_o,
                    "attributed_gmv": round(gmv, 2),
                    "gross_ad_load_pct": load,
                    "note": "ASSOCIATION != CAUSALITY",
                }
            )
    return rows


def _parse_nmids_json(raw: str) -> list[int]:
    if not raw:
        return []
    try:
        val = json.loads(raw.replace("'", '"'))
        if isinstance(val, list):
            return [int(x) for x in val if str(x).isdigit()]
    except json.JSONDecodeError:
        pass
    return []


def _product_window_rows(
    orders: list[dict[str, Any]],
    day_rows: list[dict[str, Any]],
    nm_contours: dict[int, list[dict[str, Any]]],
    nmid_category: dict[int, str],
    closed_end: date,
) -> list[dict[str, Any]]:
    windows = {
        "CURRENT_3D": _closed_dates(closed_end, 3),
        "CURRENT_7D": _closed_dates(closed_end, 7),
        "PREVIOUS_7D": _closed_dates(closed_end - timedelta(days=7), 7),
        "CURRENT_14D": _closed_dates(closed_end, 14),
    }
    scoped = sorted(set(nmid_category) | set(ALL_PRIORITY_NMIDS))
    rows: list[dict[str, Any]] = []
    for nmid in scoped:
        cat = nmid_category.get(nmid, "GAP")
        adv_ids = _unique_contour_adv_ids(nm_contours.get(nmid, []))
        for win_label, dates in windows.items():
            sw = _sales_window(orders, nmid, dates)
            spend = sum(
                r["day_spend"]
                for r in day_rows
                if r["advert_id"] in adv_ids and r["date"] in dates
            )
            rows.append(
                {
                    "nmID": nmid,
                    "category": cat,
                    "window": win_label,
                    "events": sw["events"],
                    "units": sw["units"],
                    "factual_order_value": sw["value"],
                    "gross_ad_spend": round(spend, 2),
                    "gross_ad_load_pct": _drr_pct(spend, float(sw["value"])),
                    "last_order_date": sw["last_order_date"],
                }
            )
    return rows


def _unique_contour_adv_ids(contours: list[dict[str, Any]]) -> set[int]:
    out: set[int] = set()
    for c in contours:
        for leg in ("auto_adv_id", "search_adv_id"):
            aid = c.get(leg)
            if aid:
                out.add(int(aid))
    return out


def _is_bot_active_true(value: Any) -> bool:
    """True для PG/WB bot_active в bool или строковом виде."""
    if value is True:
        return True
    if isinstance(value, str):
        return value.strip().lower() in ("true", "1", "yes")
    return False


def _contour_pg_mapped(
    contour: dict[str, Any],
    pg_by_adv: dict[int, dict[str, str]],
) -> bool:
    """Кontur PG-mapped если есть adv_setting_id или adv_id в pg_by_adv."""
    if contour.get("adv_setting_id"):
        return True
    for leg in ("auto_adv_id", "search_adv_id"):
        aid = contour.get(leg)
        if aid and int(aid) in pg_by_adv:
            return True
    return False


def _merge_pg_by_adv_into_contour(
    contour: dict[str, Any],
    pg_by_adv: dict[int, dict[str, str]],
) -> dict[str, Any]:
    """Подтянуть PG-поля по auto/search adv_id для WB-only контура."""
    for leg in ("auto_adv_id", "search_adv_id"):
        aid = contour.get(leg)
        if not aid:
            continue
        pg = pg_by_adv.get(int(aid))
        if not pg:
            continue
        return {
            **contour,
            "adv_setting_id": pg.get("id") or contour.get("adv_setting_id"),
            "bot_active": pg.get("bot_active", contour.get("bot_active")),
            "target_cpo": pg.get("target_price_for_order", contour.get("target_cpo")),
            "max_cpo": pg.get("max_price_for_order", contour.get("max_cpo")),
            "auto_daily_limit": pg.get("auto_budget_daily_limit", contour.get("auto_daily_limit")),
            "search_daily_limit": pg.get(
                "search_auto_budget_daily_limit", contour.get("search_daily_limit")
            ),
            "pg_active_status": pg.get("active_status", contour.get("pg_active_status")),
            "strategy": pg.get("strategy", contour.get("strategy")),
            "aggressiveness": pg.get("aggressiveness", contour.get("aggressiveness")),
            "_pg_row": pg,
        }
    return contour


def _resolve_contour_for_pick(
    contour: dict[str, Any],
    pg_by_adv: dict[int, dict[str, str]],
) -> dict[str, Any]:
    """Нормализовать контур перед ранжированием (PG row as-is, WB-only — merge)."""
    if contour.get("adv_setting_id"):
        return contour
    return _merge_pg_by_adv_into_contour(contour, pg_by_adv)


def _pick_pg_contour(
    contours: list[dict[str, Any]],
    pg_by_adv: dict[int, dict[str, str]],
) -> dict[str, Any]:
    """Выбрать PG-контур: bot_active=True > PG-mapped > WB-only fallback."""
    if not contours:
        return {}
    resolved = [_resolve_contour_for_pick(c, pg_by_adv) for c in contours]
    for c in resolved:
        if _contour_pg_mapped(c, pg_by_adv) and _is_bot_active_true(c.get("bot_active")):
            return c
    for c in resolved:
        if _contour_pg_mapped(c, pg_by_adv):
            return c
    return resolved[0]


def _pg_field(
    pg_info: dict[str, Any],
    pg_by_adv: dict[int, dict[str, str]],
    field: str,
    *,
    contour_key: str | None = None,
) -> Any:
    """Поле из PG-контура или pg_by_adv по auto/search adv_id."""
    if contour_key and pg_info.get(contour_key) not in (None, "", "GAP"):
        return pg_info[contour_key]
    pg_row = pg_info.get("_pg_row") or {}
    if pg_row.get(field) not in (None, ""):
        return pg_row[field]
    for leg in ("auto_adv_id", "search_adv_id"):
        aid = pg_info.get(leg)
        if aid and int(aid) in pg_by_adv:
            val = pg_by_adv[int(aid)].get(field)
            if val not in (None, ""):
                return val
    return "GAP"


def _delta_metric_row(
    metric: str,
    baseline_from: date,
    baseline_to: date,
    current_from: date,
    current_to: date,
    baseline_value: Any,
    current_value: Any,
    *,
    comparable: str = "YES",
    note: str = "",
) -> dict[str, Any]:
    row: dict[str, Any] = {
        "metric": metric,
        "baseline_period_from": baseline_from.isoformat(),
        "baseline_period_to": baseline_to.isoformat(),
        "current_period_from": current_from.isoformat(),
        "current_period_to": current_to.isoformat(),
        "baseline_value": baseline_value,
        "current_value": current_value,
        "delta_abs": "GAP",
        "delta_pct": "GAP",
        "comparable": comparable,
        "note": note,
    }
    try:
        b_val = float(baseline_value)
        c_val = float(current_value)
        row["delta_abs"] = round(c_val - b_val, 2)
        row["delta_pct"] = round(100 * (c_val - b_val) / b_val, 2) if b_val else "GAP"
    except (TypeError, ValueError):
        pass
    return row


def _load_baseline_store_windows() -> dict[str, dict[str, str]]:
    """Прочитать baseline store windows из prior promo pack (lineage only, optional)."""
    out: dict[str, dict[str, str]] = {}
    if not BASELINE_PROMO_ZIP.exists():
        return out
    try:
        with zipfile.ZipFile(BASELINE_PROMO_ZIP) as zf:
            candidates = [n for n in zf.namelist() if n.endswith("09_DRR_WINDOWS.csv")]
            if not candidates:
                return out
            with zf.open(candidates[0]) as handle:
                text = handle.read().decode("utf-8")
            for row in csv.DictReader(text.splitlines()):
                label = row.get("window_label", "")
                if label:
                    out[label] = row
    except (OSError, zipfile.BadZipFile, KeyError):
        pass
    return out


def _delta_rows(
    *,
    baseline_end: date,
    current_closed_end: date,
    sales_daily: dict[str, dict[str, Any]],
    spend_daily: dict[str, dict[str, Any]],
    topup_daily: dict[str, dict[str, Any]],
    current_windows: list[dict[str, Any]],
    orders: list[dict[str, Any]],
    day_rows: list[dict[str, Any]],
    nmid_category: dict[int, str],
    nm_contours: dict[int, list[dict[str, Any]]],
    inventory: dict[int, dict[str, Any]],
) -> list[dict[str, Any]]:
    """Delta vs baseline ending baseline_end from this run's daily rows (no external ZIP mount)."""
    rows: list[dict[str, Any]] = []
    base7_from = baseline_end - timedelta(days=6)
    base7_to = baseline_end
    cur7 = next((w for w in current_windows if w["window_label"] == "CURRENT_7D"), None)
    if not cur7:
        rows.append(
            {
                "metric": "baseline_compare",
                "baseline_period_from": base7_from.isoformat(),
                "baseline_period_to": base7_to.isoformat(),
                "current_period_from": "GAP",
                "current_period_to": "GAP",
                "baseline_value": "GAP",
                "current_value": "GAP",
                "delta_abs": "GAP",
                "delta_pct": "GAP",
                "comparable": "GAP",
                "note": "CURRENT_7D_MISSING",
            }
        )
        return rows

    cur7_from = date.fromisoformat(cur7["period_from"])
    cur7_to = date.fromisoformat(cur7["period_to"])
    roll_days = (cur7_to - base7_to).days
    roll_note = (
        f"Baseline 7d ends {base7_to.isoformat()}; current 7d ends {cur7_to.isoformat()} "
        f"({roll_days}d roll). Prior promo LAST_7 may end 2026-09-06 (+1d vs this baseline)."
        if roll_days
        else f"Baseline and current 7d both end {base7_to.isoformat()}."
    )

    base7 = _aggregate_window(
        "BASELINE_7D",
        base7_from,
        base7_to,
        sales_daily,
        spend_daily,
        topup_daily,
        baseline_end,
    )

    for metric, b_key, c_key in (
        ("store_7d_factual_order_value", "factual_order_value", "factual_order_value"),
        ("store_7d_gross_ad_spend", "gross_ad_spend", "gross_ad_spend"),
    ):
        rows.append(
            _delta_metric_row(
                metric,
                base7_from,
                base7_to,
                cur7_from,
                cur7_to,
                base7[b_key],
                cur7[c_key],
                comparable="PARTIAL" if roll_days else "YES",
                note=roll_note,
            )
        )

    rows.append(
        _delta_metric_row(
            "store_7d_gross_drr",
            base7_from,
            base7_to,
            cur7_from,
            cur7_to,
            base7["gross_drr"],
            cur7["gross_drr"],
            comparable="PARTIAL" if roll_days else "YES",
            note=f"{roll_note}; DRR delta descriptive only; low DRR != good",
        )
    )

    base_dates_7 = _closed_dates(baseline_end, 7)
    cur_dates_7 = _closed_dates(current_closed_end, 7)
    for cat_key, cat_label in CATEGORY_LABELS.items():
        cat_nmids = {n for n, c in nmid_category.items() if c == cat_key}
        if not cat_nmids:
            rows.append(
                {
                    "metric": f"category_{cat_key}_7d_sales",
                    "baseline_period_from": base7_from.isoformat(),
                    "baseline_period_to": base7_to.isoformat(),
                    "current_period_from": cur7_from.isoformat(),
                    "current_period_to": cur7_to.isoformat(),
                    "baseline_value": "GAP",
                    "current_value": "GAP",
                    "delta_abs": "GAP",
                    "delta_pct": "GAP",
                    "comparable": "GAP",
                    "note": f"{cat_label}: NO_NMIDS_IN_CATEGORY",
                }
            )
            continue
        b_sales = sum(_sales_window(orders, n, base_dates_7)["value"] for n in cat_nmids)
        c_sales = sum(_sales_window(orders, n, cur_dates_7)["value"] for n in cat_nmids)
        rows.append(
            _delta_metric_row(
                f"category_{cat_key}_7d_sales",
                base7_from,
                base7_to,
                cur7_from,
                cur7_to,
                round(b_sales, 2),
                round(c_sales, 2),
                comparable="PARTIAL" if roll_days else "YES",
                note=f"{cat_label}; category mover; no causality",
            )
        )

    campaign_deltas: list[tuple[int, float, float, float]] = []
    for adv_id in sorted(inventory):
        b_spend = sum(
            r["day_spend"]
            for r in day_rows
            if r["advert_id"] == adv_id and r["date"] in base_dates_7
        )
        c_spend = sum(
            r["day_spend"]
            for r in day_rows
            if r["advert_id"] == adv_id and r["date"] in cur_dates_7
        )
        if b_spend or c_spend:
            campaign_deltas.append((adv_id, b_spend, c_spend, c_spend - b_spend))
    campaign_deltas.sort(key=lambda x: abs(x[3]), reverse=True)
    for adv_id, b_spend, c_spend, _ in campaign_deltas[:10]:
        rows.append(
            _delta_metric_row(
                f"campaign_{adv_id}_7d_spend",
                base7_from,
                base7_to,
                cur7_from,
                cur7_to,
                round(b_spend, 2),
                round(c_spend, 2),
                comparable="PARTIAL" if roll_days else "YES",
                note="campaign spend change; no causality",
            )
        )

    lineage = _load_baseline_store_windows()
    prior = lineage.get("LAST_7_CLOSED")
    if prior:
        try:
            p_to = prior.get("period_to", "GAP")
            rows.append(
                {
                    "metric": "lineage_prior_promo_last_7_closed_sales",
                    "baseline_period_from": prior.get("period_from", "GAP"),
                    "baseline_period_to": p_to,
                    "current_period_from": cur7_from.isoformat(),
                    "current_period_to": cur7_to.isoformat(),
                    "baseline_value": prior.get("factual_order_value", "GAP"),
                    "current_value": cur7["factual_order_value"],
                    "delta_abs": "GAP",
                    "delta_pct": "GAP",
                    "comparable": "PARTIAL",
                    "note": (
                        "Optional lineage vs prior promo ZIP; "
                        f"period_to {p_to} may differ by 1d from this baseline"
                    ),
                }
            )
        except (TypeError, ValueError, KeyError):
            pass

    rows.append(
        {
            "metric": "campaign_status_limits_cpo",
            "baseline_period_from": base7_from.isoformat(),
            "baseline_period_to": base7_to.isoformat(),
            "current_period_from": cur7_from.isoformat(),
            "current_period_to": cur7_to.isoformat(),
            "baseline_value": "GAP",
            "current_value": "GAP",
            "delta_abs": "GAP",
            "delta_pct": "GAP",
            "comparable": "GAP",
            "note": "See 08_PRIORITY_ENTRY_SNAPSHOT; status/limits/CPO not time-series delta",
        }
    )
    return rows


def _master_qa_self_check(
    *,
    checked_at: datetime,
    closed_end: date,
    open_d: date,
    store_daily_rows: list[dict[str, Any]],
    window_rows: list[dict[str, Any]],
    delta_rows: list[dict[str, Any]],
    priority_rows: list[dict[str, Any]],
    campaign_current: list[dict[str, Any]],
    gaps: list[str],
) -> str:
    """Collector self-check draft for MASTER QA (not a one-line stub)."""
    lines = [
        "# Master QA Report (collector draft)",
        "",
        f"Package `{PACKAGE}` collected at {_iso_msk(checked_at)}.",
        f"LAST_FULLY_CLOSED_DAY={closed_end.isoformat()}; OPEN_DAY={open_d.isoformat()}.",
        "",
        "## Store daily vs windows",
        "",
    ]
    closed_rows = [r for r in store_daily_rows if r.get("day_state") == "CLOSED"]
    sum_sales = round(sum(float(r["factual_order_value"]) for r in closed_rows), 2)
    sum_spend = round(sum(float(r["gross_ad_spend"]) for r in closed_rows), 2)
    lines.append(f"- Closed daily rows: {len(closed_rows)} (from {COLLECT_FROM} through {closed_end}).")
    lines.append(f"- Sum factual_order_value (closed days): {sum_sales:,.2f}")
    lines.append(f"- Sum gross_ad_spend (closed days): {sum_spend:,.2f}")

    cur7 = next((w for w in window_rows if w["window_label"] == "CURRENT_7D"), {})
    cur7_dates = _closed_dates(closed_end, 7)
    cur7_sales_from_daily = round(
        sum(float(r["factual_order_value"]) for r in closed_rows if r["date"] in cur7_dates),
        2,
    )
    cur7_spend_from_daily = round(
        sum(float(r["gross_ad_spend"]) for r in closed_rows if r["date"] in cur7_dates),
        2,
    )
    lines.extend(
        [
            "",
            "## CURRENT_7D reconciliation",
            "",
            f"- Window aggregate sales: {cur7.get('factual_order_value', 'GAP')}",
            f"- Sum from 01_STORE_DAILY (7d): {cur7_sales_from_daily}",
            f"- Match: {'PASS' if cur7 and float(cur7.get('factual_order_value') or 0) == cur7_sales_from_daily else 'CHECK'}",
            f"- Window aggregate spend: {cur7.get('gross_ad_spend', 'GAP')}",
            f"- Sum from 01_STORE_DAILY (7d): {cur7_spend_from_daily}",
            f"- Match: {'PASS' if cur7 and float(cur7.get('gross_ad_spend') or 0) == cur7_spend_from_daily else 'CHECK'}",
        ]
    )

    open_in_windows = [r for r in store_daily_rows if r.get("day_state") == "OPEN"]
    lines.extend(
        [
            "",
            "## Open day exclusion",
            "",
            f"- Open-day rows in 01: {len(open_in_windows)} ({open_d.isoformat()})",
            f"- Open day excluded from closed windows: {'PASS' if not any(open_d.isoformat() == w.get('period_to') for w in window_rows if w.get('window_label', '').startswith('CURRENT')) or closed_end < open_d else 'CHECK'}",
        ]
    )

    real_delta = [r for r in delta_rows if r.get("metric", "").startswith(("store_", "category_", "campaign_"))]
    lines.extend(
        [
            "",
            "## Delta (09)",
            "",
            f"- Total delta rows: {len(delta_rows)}",
            f"- Comparable metric rows: {len(real_delta)}",
            f"- Stub-only (BASELINE_OR_CURRENT_7D_MISSING): {'FAIL' if any(r.get('note') == 'BASELINE_OR_CURRENT_7D_MISSING' for r in delta_rows) else 'PASS'}",
            f"- cash_drr in windows: GAP (expected CASH_FLOW_ONLY)",
        ]
    )

    pg_mapped = sum(
        1
        for r in priority_rows
        if r.get("bot_active") not in (None, "", "GAP")
        or r.get("auto_daily_limit") not in (None, "", "GAP")
    )
    lines.extend(
        [
            "",
            "## Priority entry (08)",
            "",
            f"- Priority+adjacent nmIDs: {len(priority_rows)} (expected {len(ALL_PRIORITY_NMIDS)})",
            f"- Rows with bot_active or auto_daily_limit populated: {pg_mapped}",
            f"- Campaign current rows (05): {len(campaign_current)}",
        ]
    )

    lines.extend(["", "## Declared gaps", ""] + [f"- {g}" for g in gaps])
    lines.extend(["", "MASTER should rewrite with independent verification."])
    return "\n".join(lines)


def _top_movers(
    product_rows: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    cur: dict[int, float] = {}
    prev: dict[int, float] = {}
    spend_cur: dict[int, float] = {}
    spend_prev: dict[int, float] = {}
    for row in product_rows:
        nmid = int(row["nmID"])
        val = float(row.get("factual_order_value") or 0)
        spend = float(row.get("gross_ad_spend") or 0)
        if row["window"] == "CURRENT_7D":
            cur[nmid] = val
            spend_cur[nmid] = spend
        elif row["window"] == "PREVIOUS_7D":
            prev[nmid] = val
            spend_prev[nmid] = spend
    deltas: list[tuple[int, float]] = []
    for nmid in set(cur) | set(prev):
        deltas.append((nmid, cur.get(nmid, 0) - prev.get(nmid, 0)))
    deltas.sort(key=lambda x: x[1], reverse=True)
    rows: list[dict[str, Any]] = []
    for nmid, delta in deltas[:5]:
        rows.append(
            {
                "flag": "TOP_GROWERS",
                "nmID": nmid,
                "metric": "factual_order_value_7d",
                "current_7d": cur.get(nmid, 0),
                "previous_7d": prev.get(nmid, 0),
                "delta": round(delta, 2),
            }
        )
    for nmid, delta in sorted(deltas, key=lambda x: x[1])[:5]:
        rows.append(
            {
                "flag": "TOP_DECLINERS",
                "nmID": nmid,
                "metric": "factual_order_value_7d",
                "current_7d": cur.get(nmid, 0),
                "previous_7d": prev.get(nmid, 0),
                "delta": round(delta, 2),
            }
        )
    for nmid in set(spend_cur):
        sc = spend_cur.get(nmid, 0)
        sv = cur.get(nmid, 0)
        if sc > 500 and sv < sc * 0.05:
            rows.append(
                {
                    "flag": "HIGH_SPEND_LOW_SALES",
                    "nmID": nmid,
                    "spend_7d": sc,
                    "sales_7d": sv,
                }
            )
        if sc < 100 and sv > 1000:
            rows.append(
                {
                    "flag": "LOW_SPEND_HIGH_SALES",
                    "nmID": nmid,
                    "spend_7d": sc,
                    "sales_7d": sv,
                }
            )
    return rows


async def _async_pipeline(closed_end: date, open_d: date) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    """Единый event loop для WB API + Content cards (избегаем loop mismatch)."""
    import scripts.a1_promo_adjusted_drr_collect as promo_mod

    promo_mod.COLLECT_FROM = COLLECT_FROM
    wb_payload = await promo_mod._async_collect_all(closed_end, open_d)
    cards = await _all_cards()
    return wb_payload, cards


def run_collect(output_dir: Path) -> dict[str, Any]:
    """Собрать evidence package и вернуть manifest summary."""
    checked_at = _msk_now()
    closed_end = _closed_end_day(checked_at)
    open_d = _open_day(checked_at)
    root = output_dir.resolve()
    root.mkdir(parents=True, exist_ok=True)
    raw_dir = root / "raw"
    raw_dir.mkdir(parents=True, exist_ok=True)
    sql_dir = root / "staging" / "sql"
    sql_dir.mkdir(parents=True, exist_ok=True)

    _bootstrap_cluster_infra()
    cabinet = _load_wbcabinet(root, sql_dir)
    wb_cabinet_id = cabinet["wb_cabinet_id"]
    gaps: list[str] = []
    if wb_cabinet_id != 401:
        gaps.append(f"WB_CABINET_ID_MISMATCH: expected 401 got {wb_cabinet_id}")

    settings_rows = _load_adv_settings(root)[1]
    pg_by_adv = _pg_by_adv_id(settings_rows)
    topup_raw = _load_topups(root, sql_dir, wb_cabinet_id, COLLECT_FROM)
    seen: set[str] = set()
    topup_deduped = []
    for row in topup_raw:
        key = row.get("idempotency_key") or row.get("id") or ""
        if key in seen:
            continue
        seen.add(key)
        topup_deduped.append(row)
    normalized = [_normalize_topup(r) for r in topup_deduped]

    import scripts.a1_promo_adjusted_drr_collect as promo_mod

    promo_mod.COLLECT_FROM = COLLECT_FROM
    wb_payload, cards = asyncio.run(_async_pipeline(closed_end, open_d))

    central = wb_payload["central"]
    campaigns = wb_payload["campaigns"]
    fullstats_raw = wb_payload["fullstats_raw"]
    orders_raw = wb_payload["orders_raw"]
    campaign_budgets = wb_payload["campaign_budgets"]

    for name, rows in (
        ("campaigns_v2.jsonl", campaigns),
        ("fullstats_v3_raw.jsonl", fullstats_raw),
        ("supplier_orders_raw.jsonl", orders_raw),
    ):
        with (raw_dir / name).open("w", encoding="utf-8") as handle:
            for row in rows:
                handle.write(json.dumps(_jsonable(row), ensure_ascii=False) + "\n")

    nm_rows, day_rows = _nm_rows(fullstats_raw)
    inventory = _campaign_inventory(campaigns, pg_by_adv)
    nm_contours = _nm_to_contours(settings_rows, campaigns)
    nmid_category = _build_nmid_category(cards)

    sales_daily = _orders_store_daily(orders_raw, closed_end, open_d)
    spend_daily = _gross_spend_daily(day_rows, closed_end, open_d)
    topup_daily = _topup_daily(normalized, closed_end, open_d)

    store_daily_rows: list[dict[str, Any]] = []
    d = COLLECT_FROM
    while d <= closed_end:
        key = d.isoformat()
        sd = sales_daily[key]
        sp = spend_daily[key]
        tp = topup_daily[key]
        sales_val = float(sd["factual_order_value"])
        spend_val = float(sp["gross_ad_spend"])
        store_daily_rows.append(
            {
                "date": key,
                "day_state": sd["day_state"],
                "purchase_events": sd["purchase_events"],
                "units": sd["units"],
                "factual_order_value": sales_val,
                "gross_ad_spend": spend_val,
                "gross_drr": _drr_pct(spend_val, sales_val),
                "promo_used_on_deposits": tp["promo_used_on_deposits"],
                "ordinary_funds_used_on_deposits": tp["ordinary_funds_used_on_deposits"],
                "views": sp["views"],
                "clicks": sp["clicks"],
                "ctr": sp["ctr"],
                "attributed_orders": sp["attributed_orders"],
                "attributed_gmv": sp["attributed_gmv"],
                "freshness_msk": _iso_msk(checked_at),
            }
        )
        d += timedelta(days=1)

    window_rows = [
        _aggregate_window(label, df, dt, sales_daily, spend_daily, topup_daily, closed_end)
        for label, df, dt in _window_specs(closed_end)
    ]

    promo_current = {
        "checked_at_msk": _iso_msk(checked_at),
        "shop_id": SHOP_ID,
        "wb_cabinet_id": wb_cabinet_id,
        "wb_cabinet_id_verified": wb_cabinet_id == 401,
        "balance": central.get("balance"),
        "net": central.get("net"),
        "bonus": central.get("bonus"),
        "cashbacks": _cashbacks_to_list(central.get("cashbacks")),
        "endpoint": "GET /adv/v1/balance",
        "accounting_status": ACCOUNTING_STATUS,
        "cash_drr_emitted": False,
    }
    (root / "10_PROMO_CURRENT.json").write_text(
        json.dumps(promo_current, ensure_ascii=False, indent=2), encoding="utf-8"
    )

    promo_acct_rows = [
        {
            "date": k,
            "promo_used_on_deposits": v["promo_used_on_deposits"],
            "ordinary_funds_used_on_deposits": v["ordinary_funds_used_on_deposits"],
            "cash_ad_cost": "GAP",
            "cash_drr": "GAP",
            "accounting_status": ACCOUNTING_STATUS,
        }
        for k, v in sorted(topup_daily.items())
        if date.fromisoformat(k) <= closed_end
    ]

    category_rows = _category_window_rows(
        orders_raw, nm_rows, day_rows, nm_contours, nmid_category, closed_end
    )
    product_rows = _product_window_rows(
        orders_raw, day_rows, nm_contours, nmid_category, closed_end
    )

    wb_by_id = {_read_int(c, "id", "advertId"): c for c in campaigns}
    campaign_current: list[dict[str, Any]] = []
    for adv_id, inv in sorted(inventory.items()):
        wb_c = wb_by_id.get(adv_id, {})
        pg_row = pg_by_adv.get(adv_id, {})
        campaign_current.append(
            {
                "adv_id": adv_id,
                "campaign_name": inv.get("name") or "GAP",
                "wb_status": wb_c.get("status", "GAP"),
                "pg_active": pg_row.get("active_status", "GAP"),
                "bot_active": pg_row.get("bot_active", "GAP"),
                "strategy": pg_row.get("strategy", "GAP"),
                "aggressiveness": pg_row.get("aggressiveness", "GAP"),
                "target_cpo": pg_row.get("target_price_for_order", "GAP"),
                "max_cpo": pg_row.get("max_price_for_order", "GAP"),
                "auto_daily_limit": pg_row.get("auto_budget_daily_limit", "GAP"),
                "search_daily_limit": pg_row.get("search_auto_budget_daily_limit", "GAP"),
                "budget_total": next(
                    (b.get("total") for b in campaign_budgets if b.get("adv_id") == adv_id),
                    "GAP",
                ),
                "nmids": ",".join(str(x) for x in (inv.get("nm_ids") or [])),
            }
        )

    campaign_window_rows: list[dict[str, Any]] = []
    for label, df, dt in _window_specs(closed_end):
        dates = { (df + timedelta(days=i)).isoformat() for i in range((dt - df).days + 1) if df + timedelta(days=i) <= closed_end }
        for adv_id in sorted(inventory):
            subset = [r for r in day_rows if r["advert_id"] == adv_id and r["date"] in dates]
            if not subset:
                continue
            spend = round(sum(r["day_spend"] for r in subset), 2)
            campaign_window_rows.append(
                {
                    "adv_id": adv_id,
                    "window": label,
                    "spend": spend,
                    "views": sum(r["day_views"] for r in subset),
                    "clicks": sum(r["day_clicks"] for r in subset),
                    "orders": sum(r["day_orders"] for r in subset),
                    "gmv": round(sum(r["day_sum_price"] for r in subset), 2),
                }
            )

    direct_assoc_rows: list[dict[str, Any]] = []
    for adv_id in sorted(inventory):
        promoted = set(inventory[adv_id].get("nm_ids") or [])
        camp = wb_by_id.get(adv_id, {})
        if camp:
            promoted |= _promoted_set(camp)
        subset_nm = [r for r in nm_rows if r["advert_id"] == adv_id]
        for label, df, dt in _window_specs(closed_end):
            dates = {
                (df + timedelta(days=i)).isoformat()
                for i in range((dt - df).days + 1)
                if df + timedelta(days=i) <= closed_end
            }
            split = _direct_assoc_split(subset_nm, promoted, dates)
            direct_assoc_rows.append(
                {
                    "adv_id": adv_id,
                    "window": label,
                    **split,
                    "note": "ASSOCIATION != CAUSALITY",
                }
            )

    dates_3 = _closed_dates(closed_end, 3)
    dates_7 = _closed_dates(closed_end, 7)
    dates_14 = _closed_dates(closed_end, 14)
    priority_rows: list[dict[str, Any]] = []
    for nmid in ALL_PRIORITY_NMIDS:
        contours = nm_contours.get(nmid, [])
        adv_ids = sorted(_unique_contour_adv_ids(contours))
        s3 = _sales_window(orders_raw, nmid, dates_3)
        s7 = _sales_window(orders_raw, nmid, dates_7)
        s14 = _sales_window(orders_raw, nmid, dates_14)
        spend3 = spend7 = spend14 = 0.0
        for aid in adv_ids:
            spend3 += sum(r["day_spend"] for r in day_rows if r["advert_id"] == aid and r["date"] in dates_3)
            spend7 += sum(r["day_spend"] for r in day_rows if r["advert_id"] == aid and r["date"] in dates_7)
            spend14 += sum(r["day_spend"] for r in day_rows if r["advert_id"] == aid and r["date"] in dates_14)
        promoted = {nmid}
        direct_o = assoc_o = 0
        gmv_d = gmv_a = 0.0
        for aid in adv_ids:
            split = _direct_assoc_split(
                [r for r in nm_rows if r["advert_id"] == aid], promoted, dates_7
            )
            direct_o += split["direct_orders"]
            assoc_o += split["associated_orders"]
            gmv_d += float(split["direct_gmv"])
            gmv_a += float(split["associated_gmv"])
        pg_info = _pick_pg_contour(contours, pg_by_adv)
        auto_id = int(pg_info.get("auto_adv_id") or 0)
        wb_c = wb_by_id.get(auto_id, {})
        cpo_direct = round(spend7 / direct_o, 2) if direct_o else "GAP"
        cpo_total = round(spend7 / (direct_o + assoc_o), 2) if (direct_o + assoc_o) else "GAP"
        priority_rows.append(
            {
                "nmID": nmid,
                "priority_tier": "CORE" if nmid in PRIORITY_NMIDS else "ADJACENT",
                "sales_3d_value": s3["value"],
                "sales_7d_value": s7["value"],
                "sales_14d_value": s14["value"],
                "campaign_ids": ",".join(str(x) for x in adv_ids) or "GAP",
                "wb_status": wb_c.get("status", "GAP"),
                "pg_active": pg_info.get("pg_active_status", "GAP"),
                "bot_active": _pg_field(pg_info, pg_by_adv, "bot_active", contour_key="bot_active"),
                "strategy": _pg_field(pg_info, pg_by_adv, "strategy"),
                "aggressiveness": _pg_field(pg_info, pg_by_adv, "aggressiveness"),
                "target_cpo": _pg_field(
                    pg_info, pg_by_adv, "target_price_for_order", contour_key="target_cpo"
                ),
                "max_cpo": _pg_field(
                    pg_info, pg_by_adv, "max_price_for_order", contour_key="max_cpo"
                ),
                "auto_daily_limit": _pg_field(
                    pg_info, pg_by_adv, "auto_budget_daily_limit", contour_key="auto_daily_limit"
                ),
                "search_daily_limit": _pg_field(
                    pg_info,
                    pg_by_adv,
                    "search_auto_budget_daily_limit",
                    contour_key="search_daily_limit",
                ),
                "spend_3d": round(spend3, 2),
                "spend_7d": round(spend7, 2),
                "spend_14d": round(spend14, 2),
                "direct_orders_7d": direct_o,
                "associated_orders_7d": assoc_o,
                "attributed_gmv_7d": round(gmv_d + gmv_a, 2),
                "cpo_direct_7d": cpo_direct,
                "cpo_total_attributed_7d": cpo_total,
                "last_meaningful_change": "GAP",
            }
        )

    delta_rows = _delta_rows(
        baseline_end=BASELINE_DAY,
        current_closed_end=closed_end,
        sales_daily=sales_daily,
        spend_daily=spend_daily,
        topup_daily=topup_daily,
        current_windows=window_rows,
        orders=orders_raw,
        day_rows=day_rows,
        nmid_category=nmid_category,
        nm_contours=nm_contours,
        inventory=inventory,
    )
    mover_rows = _top_movers(product_rows)

    _write_csv(root / "01_STORE_DAILY.csv", store_daily_rows, list(store_daily_rows[0].keys()) if store_daily_rows else ["date"])
    _write_csv(
        root / "02_STORE_WINDOWS.csv",
        window_rows,
        [
            "window_label", "period_from", "period_to", "purchase_events", "units",
            "factual_order_value", "gross_ad_spend", "gross_drr", "promo_used",
            "ordinary_funds_used", "cash_ad_cost", "cash_drr", "accounting_status",
        ],
    )
    _write_csv(root / "03_CATEGORY_WINDOWS.csv", category_rows, list(category_rows[0].keys()) if category_rows else ["category"])
    _write_csv(root / "04_PRODUCT_WINDOWS.csv", product_rows, list(product_rows[0].keys()) if product_rows else ["nmID"])
    _write_csv(root / "05_CAMPAIGN_CURRENT.csv", campaign_current, list(campaign_current[0].keys()) if campaign_current else ["adv_id"])
    _write_csv(root / "06_CAMPAIGN_WINDOWS.csv", campaign_window_rows, list(campaign_window_rows[0].keys()) if campaign_window_rows else ["adv_id"])
    _write_csv(root / "07_DIRECT_ASSOC_WINDOWS.csv", direct_assoc_rows, list(direct_assoc_rows[0].keys()) if direct_assoc_rows else ["adv_id"])
    _write_csv(root / "08_PRIORITY_ENTRY_SNAPSHOT.csv", priority_rows, list(priority_rows[0].keys()) if priority_rows else ["nmID"])
    _write_csv(
        root / "09_DELTA_SINCE_20260905.csv",
        delta_rows,
        [
            "metric",
            "baseline_period_from",
            "baseline_period_to",
            "current_period_from",
            "current_period_to",
            "baseline_value",
            "current_value",
            "delta_abs",
            "delta_pct",
            "comparable",
            "note",
        ],
    )
    _write_csv(root / "11_PROMO_ACCOUNTING.csv", promo_acct_rows, list(promo_acct_rows[0].keys()) if promo_acct_rows else ["date"])
    _write_csv(root / "12_TOP_GROWERS_DECLINERS.csv", mover_rows, list(mover_rows[0].keys()) if mover_rows else ["flag"])

    if not BASELINE_PROMO_ZIP.exists():
        gaps.append("BASELINE_PROMO_ZIP_MISSING_FOR_LINEAGE")
    gaps.extend(
        [
            "CASH_AD_COST_GAP (CASH_FLOW_ONLY)",
            "PROMO_ADJUSTED_DRR_NOT_EMITTED",
            "SPEND_SOURCE_ATTRIBUTION_UNAVAILABLE",
        ]
    )

    dq = "\n".join(
        [
            "# Data Quality and Gaps",
            "",
            f"- shop_id: `{SHOP_ID}`",
            f"- wb_cabinet_id: `{wb_cabinet_id}` (verified 401: {wb_cabinet_id == 401})",
            f"- last_fully_closed_day: `{closed_end.isoformat()}`",
            f"- open_day: `{open_d.isoformat()}`",
            f"- collect_from: `{COLLECT_FROM.isoformat()}`",
            f"- accounting_status: {ACCOUNTING_STATUS}",
            "",
            "## Critical gaps",
            "",
        ]
        + [f"- {g}" for g in gaps]
    )
    (root / "13_DATA_QUALITY_AND_GAPS.md").write_text(dq, encoding="utf-8")

    cur3 = next(w for w in window_rows if w["window_label"] == "CURRENT_3D")
    cur7 = next(w for w in window_rows if w["window_label"] == "CURRENT_7D")
    (root / "14_MASTER_QA_REPORT.md").write_text(
        _master_qa_self_check(
            checked_at=checked_at,
            closed_end=closed_end,
            open_d=open_d,
            store_daily_rows=store_daily_rows,
            window_rows=window_rows,
            delta_rows=delta_rows,
            priority_rows=priority_rows,
            campaign_current=campaign_current,
            gaps=gaps,
        ),
        encoding="utf-8",
    )

    (root / "15_HUMAN_SUMMARY.md").write_text(
        "\n".join(
            [
                "# Human Summary",
                "",
                "## SALES NOW",
                f"- CURRENT_3D: {cur3['factual_order_value']:,.0f} ₽ ({cur3['purchase_events']} events, {cur3['units']} units)",
                f"- CURRENT_7D: {cur7['factual_order_value']:,.0f} ₽",
                f"- LAST_FULLY_CLOSED_DAY: {closed_end.isoformat()}",
                "",
                "## AD LOAD",
                f"- CURRENT_3D gross DRR: {cur3['gross_drr']}% (spend {cur3['gross_ad_spend']:,.0f} ₽)",
                f"- CURRENT_7D gross DRR: {cur7['gross_drr']}% (spend {cur7['gross_ad_spend']:,.0f} ₽)",
                "- Low DRR ≠ good without sales scale context.",
                "",
                "## PROMO",
                f"- Pool cashbacks: {promo_current.get('cashbacks')}",
                f"- Accounting: {ACCOUNTING_STATUS}; cash_drr not emitted.",
                "",
                "## WHAT IS MOVING",
                "- See 12_TOP_GROWERS_DECLINERS.csv (7d vs prev 7d).",
                "",
                "## WHAT IS NOT WORKING",
                "- See HIGH_SPEND_LOW_SALES flags in 12_TOP_GROWERS_DECLINERS.csv.",
                "",
                "## PRIORITY CAMPAIGNS",
                "- See 08_PRIORITY_ENTRY_SNAPSHOT.csv.",
                "",
                "## FACTUAL OBSERVATIONS",
                "- Association edges != causality.",
                "- No business prescription in this pack.",
            ]
        ),
        encoding="utf-8",
    )

    manifest = {
        "package": PACKAGE,
        "artifact_class": "A1_CURRENT_PERFORMANCE_DRR_SNAPSHOT",
        "primary_zip_basename": f"{PACKAGE}.zip",
        "shop_id": SHOP_ID,
        "wb_cabinet_id": wb_cabinet_id,
        "created_at_msk": _iso_msk(checked_at),
        "last_fully_closed_day": closed_end.isoformat(),
        "open_day": open_d.isoformat(),
        "accounting_status": ACCOUNTING_STATUS,
        "windows": {w["window_label"]: w for w in window_rows},
        "critical_gaps": gaps,
    }
    (root / "00_MANIFEST.json").write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")

    findings = evidence.secret_scan(root)
    if findings:
        raise SystemExit(f"Secret scan failed: {findings[:3]}")

    archive, digest = evidence.archive_directory(root)
    return {
        "EXECUTION_STATUS": "COMPLETE",
        "PACKAGE": PACKAGE,
        "SHOP_ID": SHOP_ID,
        "WB_CABINET_ID": wb_cabinet_id,
        "LAST_FULLY_CLOSED_DAY": closed_end.isoformat(),
        "WINDOWS": {w["window_label"]: w for w in window_rows},
        "PROMO_CURRENT": promo_current,
        "ZIP_ABSOLUTE_PATH": str(archive.resolve()),
        "ZIP_SHA256": digest,
        "PRIMARY_ARTIFACT": archive.name,
        "CRITICAL_GAPS": gaps,
    }


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="A1 current performance / DRR snapshot READ_ONLY collector."
    )
    parser.add_argument(
        "--output-dir",
        default=".tmp/a1_current_performance_drr_snapshot",
        help="Output directory (will be zipped)",
    )
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    out = Path(args.output_dir).resolve()
    result = run_collect(out)
    print(json.dumps(result, ensure_ascii=False, indent=2))
    print(f"PRIMARY_SHA256={result['ZIP_SHA256']}")
    print("ops-script: success; holding for output copy")
    return 0


if __name__ == "__main__":
    sys.exit(main())
