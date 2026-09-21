"""READ_ONLY: parameterized whole-store daily DRR dynamics for a WB shop/cabinet.

Собирает дневной ряд: фактические заказы/GMV поставщика (paginated WB statistics),
весь рекламный spend кабинета (fullstats), Store CPO/DRR, окна 3/7/14/28 closed days
и открытый TODAY. Identity (shop_id, cabinet) задаётся runtime args. Без production writes.
"""

from __future__ import annotations

import argparse
import csv
import json
from dataclasses import dataclass
from datetime import date, datetime, timedelta, timezone
from pathlib import Path
from typing import Any
from zoneinfo import ZoneInfo

from scripts import a1_current_performance_drr_snapshot as base
from scripts import a1_daily_spend_control_reconciliation as spend_control
from scripts import a1_glue_topology_web_review_collect as glue
from scripts import a1_promo_adjusted_drr_collect as promo
from scripts import a1_promotion_funding_snapshot as funding
from scripts import ch_a1_evidence as evidence
from scripts.wb_a1_associated_conversions import _read_float, _read_int

LOOKBACK_DAYS = 28
MSK = ZoneInfo("Europe/Moscow")


@dataclass(frozen=True)
class CollectScope:
    """Runtime identity and DRR target for one whole-store collection."""

    shop_id: str
    wb_cabinet_id: int
    target_drr_fraction: float


def _msk_now() -> datetime:
    return datetime.now(timezone.utc).astimezone(MSK)


def _patch_scope(closed_end: date, scope: CollectScope) -> None:
    """Переопределить shop/cabinet и нижнюю границу сбора под lookback-окно."""
    evidence.SHOP_ID = scope.shop_id
    funding.SHOP_ID = scope.shop_id
    promo.SHOP_ID = scope.shop_id
    spend_control.SHOP_ID = scope.shop_id
    glue.SHOP_ID = scope.shop_id
    base.SHOP_ID = scope.shop_id
    promo.WB_CABINET_ID_EXPECTED = scope.wb_cabinet_id
    base.COLLECT_FROM = closed_end - timedelta(days=LOOKBACK_DAYS + 2)


def _cpo(spend: float, orders: int) -> float | str:
    return round(spend / orders, 2) if orders > 0 else "N/A"


def _drr_pct(spend: float, gmv: float) -> float | str:
    return round(100.0 * spend / gmv, 4) if gmv > 0 else "N/A"


def _load_csv_rows(path: Path) -> list[dict[str, str]]:
    if not path.is_file():
        return []
    with path.open(encoding="utf-8", newline="") as handle:
        return list(csv.DictReader(handle))


def _open_day_metrics(root: Path, open_d: date, scope: CollectScope) -> dict[str, Any]:
    """Факт и spend за открытый день из raw после perf pipeline."""
    orders_path = root / "raw" / "supplier_orders_raw.jsonl"
    fs_path = root / "raw" / "fullstats_v3_raw.jsonl"
    orders = 0
    gmv = 0.0
    if orders_path.is_file():
        for line in orders_path.read_text(encoding="utf-8").splitlines():
            if not line.strip():
                continue
            row = json.loads(line)
            if str(row.get("isCancel")).lower() in ("true", "1"):
                continue
            raw = str(row.get("date") or row.get("lastChangeDate") or "")[:10]
            try:
                d = date.fromisoformat(raw)
            except ValueError:
                continue
            if d != open_d:
                continue
            orders += 1
            price = _read_float(row, "finishedPrice", "priceWithDisc", "totalPrice") or 0
            qty = _read_int(row, "quantity", "qty") or 1
            gmv += float(price) * qty if price else float(price)
    spend = 0.0
    if fs_path.is_file():
        for line in fs_path.read_text(encoding="utf-8").splitlines():
            if not line.strip():
                continue
            st = json.loads(line)
            for day_row in st.get("days") or []:
                ds = str(day_row.get("date") or "")[:10]
                try:
                    d = date.fromisoformat(ds)
                except ValueError:
                    continue
                if d == open_d:
                    spend += float(_read_float(day_row, "sum") or 0)
    gmv = round(gmv, 2)
    spend = round(spend, 2)
    allowed = round(gmv * scope.target_drr_fraction, 2)
    return {
        "date": open_d.isoformat(),
        "day_status": "TODAY_OPEN",
        "factual_orders": orders,
        "factual_GMV": gmv,
        "all_shop_ad_spend": spend,
        "Store_CPO": _cpo(spend, orders),
        "Store_DRR_percent": _drr_pct(spend, gmv),
        "allowed_spend_at_10_percent": allowed,
        "headroom_vs_10_percent": round(allowed - spend, 2) if gmv > 0 else "N/A",
    }


def _daily_row_from_store_csv(row: dict[str, str], scope: CollectScope) -> dict[str, Any]:
    orders = int(float(row.get("purchase_events") or 0))
    gmv = float(row.get("factual_order_value") or 0)
    spend = float(row.get("gross_ad_spend") or 0)
    allowed = round(gmv * scope.target_drr_fraction, 2)
    return {
        "date": row["date"],
        "day_status": "CLOSED" if row.get("day_state") == "CLOSED" else str(row.get("day_state", "CLOSED")),
        "factual_orders": orders,
        "factual_GMV": round(gmv, 2),
        "all_shop_ad_spend": round(spend, 2),
        "Store_CPO": _cpo(spend, orders),
        "Store_DRR_percent": float(row.get("gross_drr") or 0) if row.get("gross_drr") else _drr_pct(spend, gmv),
        "allowed_spend_at_10_percent": allowed,
        "headroom_vs_10_percent": round(allowed - spend, 2) if gmv > 0 else "N/A",
    }


def _aggregate_closed(days: list[dict[str, Any]], n: int) -> dict[str, Any]:
    closed = [d for d in days if d.get("day_status") == "CLOSED"]
    slice_ = closed[-n:] if len(closed) >= n else closed
    orders = sum(int(d["factual_orders"]) for d in slice_)
    gmv = sum(float(d["factual_GMV"]) for d in slice_)
    spend = sum(float(d["all_shop_ad_spend"]) for d in slice_)
    return {
        "orders": orders,
        "GMV": round(gmv, 2),
        "spend": round(spend, 2),
        "Store_CPO": _cpo(spend, orders),
        "Store_DRR": _drr_pct(spend, gmv),
    }


def _interpretation(daily: list[dict[str, Any]], target_pct: float) -> dict[str, Any]:
    closed = [d for d in daily if d.get("day_status") == "CLOSED"]
    if len(closed) < 3:
        return {"note": "insufficient closed days"}
    drrs = [float(d["Store_DRR_percent"]) for d in closed[-7:] if d["Store_DRR_percent"] != "N/A"]
    spends = [float(d["all_shop_ad_spend"]) for d in closed[-7:]]
    gmvs = [float(d["factual_GMV"]) for d in closed[-7:]]
    trend = "stable"
    if len(drrs) >= 3:
        if drrs[-1] > drrs[0] * 1.15:
            trend = "rising"
        elif drrs[-1] < drrs[0] * 0.85:
            trend = "falling"
    spend_growth = spends[-1] / spends[0] if spends[0] > 0 else None
    gmv_growth = gmvs[-1] / gmvs[0] if gmvs[0] > 0 else None
    spikes = [
        d["date"]
        for d in closed
        if float(d["all_shop_ad_spend"]) > 0
        and len(closed) >= 5
        and float(d["all_shop_ad_spend"])
        > 2.5 * (sum(float(x["all_shop_ad_spend"]) for x in closed) / len(closed))
    ]
    below_target = 0
    for d in reversed(closed):
        val = d["Store_DRR_percent"]
        if val == "N/A":
            break
        if float(val) < target_pct:
            below_target += 1
        else:
            break
    latest = closed[-1] if closed else {}
    headroom_closed = latest.get("headroom_vs_10_percent")
    return {
        "store_drr_trend_7d_closed": trend,
        "spend_rising_faster_than_gmv": (
            spend_growth is not None and gmv_growth is not None and spend_growth > gmv_growth * 1.1
        ),
        "orders_gmv_scaling_with_spend": (
            gmv_growth is not None and spend_growth is not None and abs(gmv_growth - spend_growth) < 0.35
        ),
        "abnormal_spend_spike_days": spikes[-3:],
        "consecutive_closed_days_below_target_drr": below_target,
        "latest_closed_day_headroom_at_target": headroom_closed,
    }


def build_report(root: Path, perf_summary: dict[str, Any], scope: CollectScope) -> dict[str, Any]:
    manifest_path = root / "00_MANIFEST.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8")) if manifest_path.is_file() else {}
    closed_end = date.fromisoformat(perf_summary["LAST_FULLY_CLOSED_DAY"])
    open_d = date.fromisoformat(manifest.get("open_day") or _msk_now().date().isoformat())
    window_start = open_d - timedelta(days=LOOKBACK_DAYS - 1)

    store_rows = _load_csv_rows(root / "01_STORE_DAILY.csv")
    daily_closed = [
        _daily_row_from_store_csv(r, scope)
        for r in store_rows
        if date.fromisoformat(r["date"]) >= window_start
    ]
    open_row = _open_day_metrics(root, open_d, scope)
    daily = sorted(daily_closed + [open_row], key=lambda x: x["date"])
    target_pct = scope.target_drr_fraction * 100.0

    report = {
        "CHECKED_AT_MSK": _msk_now().isoformat(),
        "shop_id": scope.shop_id,
        "wb_cabinet_id": scope.wb_cabinet_id,
        "TARGET_STORE_DRR": scope.target_drr_fraction,
        "LAST_FULLY_CLOSED_DAY": closed_end.isoformat(),
        "OPEN_DAY_MSK": open_d.isoformat(),
        "DAILY_TABLE": daily,
        "3D_STORE_DRR": _aggregate_closed(daily_closed, 3),
        "7D_STORE_DRR": _aggregate_closed(daily_closed, 7),
        "14D_STORE_DRR": _aggregate_closed(daily_closed, 14),
        "28D_STORE_DRR": _aggregate_closed(daily_closed, min(28, len(daily_closed))),
        "TODAY_OPEN": {
            "orders_so_far": open_row["factual_orders"],
            "GMV_so_far": open_row["factual_GMV"],
            "spend_so_far": open_row["all_shop_ad_spend"],
            "Store_DRR_so_far": open_row["Store_DRR_percent"],
            "headroom_so_far": open_row["headroom_vs_10_percent"],
        },
        "DYNAMICS_INTERPRETATION": _interpretation(daily, target_pct),
        "perf_zip_sha256": perf_summary.get("ZIP_SHA256"),
        "CRITICAL_GAPS": perf_summary.get("CRITICAL_GAPS") or [],
        "ALL_PRODUCTION_WRITES": 0,
    }
    return report


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output-dir", required=True)
    parser.add_argument("--cabinet", type=int, required=True)
    parser.add_argument("--shop-id", required=True)
    parser.add_argument(
        "--target-drr-percent",
        type=float,
        default=10.0,
        help="Target store DRR percent (default 10).",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    out = Path(args.output_dir)
    scope = CollectScope(
        shop_id=str(args.shop_id),
        wb_cabinet_id=int(args.cabinet),
        target_drr_fraction=float(args.target_drr_percent) / 100.0,
    )
    closed_end = _msk_now().date() - timedelta(days=1)
    _patch_scope(closed_end, scope)
    perf_summary = base.run_collect(out)
    report = build_report(out, perf_summary, scope)
    primary = out / "whole_store_daily_drr.json"
    primary.write_text(json.dumps(report, ensure_ascii=False, indent=2, default=str), encoding="utf-8")
    print(f"PRIMARY_ARTIFACT={primary}")
    print("ARTIFACT_CLASS=WHOLE_STORE_DAILY_DRR")
    print("ALL_PRODUCTION_WRITES=0")
    print("ops-script: success; holding for output copy")


if __name__ == "__main__":
    main()
