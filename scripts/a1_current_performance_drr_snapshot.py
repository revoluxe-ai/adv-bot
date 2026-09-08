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


def _load_baseline_store_windows() -> dict[str, dict[str, str]]:
    """Прочитать baseline store windows из prior promo pack (lineage only)."""
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
    current_windows: list[dict[str, Any]],
    baseline_day: date,
) -> list[dict[str, Any]]:
    baseline = _load_baseline_store_windows()
    rows: list[dict[str, Any]] = []
    cur7 = next((w for w in current_windows if w["window_label"] == "CURRENT_7D"), None)
    base_fixed = baseline.get("LAST_7_CLOSED") or baseline.get("FIXED_20260830_20260905")
    if cur7 and base_fixed:
        try:
            b_sales = float(base_fixed.get("factual_order_value") or 0)
            b_spend = float(base_fixed.get("gross_ad_spend") or 0)
            b_drr = base_fixed.get("gross_drr", "GAP")
            c_sales = float(cur7["factual_order_value"])
            c_spend = float(cur7["gross_ad_spend"])
            rows.append(
                {
                    "metric": "store_7d_factual_order_value",
                    "baseline_ref": f"promo_pack_{baseline_day.isoformat()}",
                    "baseline_value": b_sales,
                    "current_value": c_sales,
                    "delta_abs": round(c_sales - b_sales, 2),
                    "delta_pct": round(100 * (c_sales - b_sales) / b_sales, 2) if b_sales else "GAP",
                    "comparable": "PARTIAL",
                    "note": "Baseline LAST_7_CLOSED ending ~2026-09-05 vs CURRENT_7D ending last closed",
                }
            )
            rows.append(
                {
                    "metric": "store_7d_gross_ad_spend",
                    "baseline_ref": f"promo_pack_{baseline_day.isoformat()}",
                    "baseline_value": b_spend,
                    "current_value": c_spend,
                    "delta_abs": round(c_spend - b_spend, 2),
                    "delta_pct": round(100 * (c_spend - b_spend) / b_spend, 2) if b_spend else "GAP",
                    "comparable": "PARTIAL",
                    "note": "Same window-length caveat as sales",
                }
            )
            rows.append(
                {
                    "metric": "store_7d_gross_drr",
                    "baseline_ref": f"promo_pack_{baseline_day.isoformat()}",
                    "baseline_value": b_drr,
                    "current_value": cur7["gross_drr"],
                    "delta_abs": "GAP",
                    "delta_pct": "GAP",
                    "comparable": "PARTIAL",
                    "note": "DRR delta descriptive only; low DRR != good",
                }
            )
        except (TypeError, ValueError):
            rows.append({"metric": "baseline_parse", "baseline_ref": str(BASELINE_PROMO_ZIP), "note": "PARSE_GAP"})
    else:
        rows.append(
            {
                "metric": "baseline_compare",
                "baseline_ref": str(BASELINE_PROMO_ZIP),
                "current_value": "GAP",
                "note": "BASELINE_OR_CURRENT_7D_MISSING",
            }
        )
    rows.append(
        {
            "metric": "campaign_status_limits_cpo",
            "baseline_ref": f"glue_pack_{baseline_day.isoformat()}",
            "note": "See 08_PRIORITY_ENTRY_SNAPSHOT vs glue 07_CAMPAIGN_CONTOUR; no causal claims",
        }
    )
    return rows


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
        pg_info = contours[0] if contours else {}
        wb_c = wb_by_id.get(int(pg_info.get("auto_adv_id") or 0), {})
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
                "bot_active": pg_info.get("bot_active", "GAP"),
                "strategy": pg_by_adv.get(int(pg_info.get("auto_adv_id") or 0), {}).get("strategy", "GAP"),
                "aggressiveness": pg_by_adv.get(int(pg_info.get("auto_adv_id") or 0), {}).get("aggressiveness", "GAP"),
                "target_cpo": pg_info.get("target_cpo", "GAP"),
                "max_cpo": pg_info.get("max_cpo", "GAP"),
                "auto_daily_limit": pg_info.get("auto_daily_limit", "GAP"),
                "search_daily_limit": pg_info.get("search_daily_limit", "GAP"),
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

    delta_rows = _delta_rows(window_rows, BASELINE_DAY)
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
    _write_csv(root / "09_DELTA_SINCE_20260905.csv", delta_rows, list(delta_rows[0].keys()) if delta_rows else ["metric"])
    _write_csv(root / "11_PROMO_ACCOUNTING.csv", promo_acct_rows, list(promo_acct_rows[0].keys()) if promo_acct_rows else ["date"])
    _write_csv(root / "12_TOP_GROWERS_DECLINERS.csv", mover_rows, list(mover_rows[0].keys()) if mover_rows else ["flag"])

    if not BASELINE_PROMO_ZIP.exists():
        gaps.append("BASELINE_PROMO_ZIP_MISSING_FOR_DELTA")
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
        "\n".join(
            [
                "# Master QA Report (collector draft)",
                "",
                f"Package `{PACKAGE}` at {_iso_msk(checked_at)}.",
                f"LAST_FULLY_CLOSED_DAY={closed_end.isoformat()}.",
                f"CURRENT_3D gross_drr={cur3['gross_drr']} sales={cur3['factual_order_value']}.",
                f"CURRENT_7D gross_drr={cur7['gross_drr']} sales={cur7['factual_order_value']}.",
                "MASTER should rewrite.",
            ]
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
