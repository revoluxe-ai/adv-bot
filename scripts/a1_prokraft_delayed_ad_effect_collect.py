"""READ_ONLY: collect and analyse ProKraft delayed advertising effects.

Модуль собирает свежие campaign fullstats и пагинированные supplier orders
для шести NMID магазина ProKraft, затем строит оконное, лаговое и
cross-SKU observational evidence. Используются существующие WB read-only
helpers; WB/PG/CH production state не изменяется.
"""

from __future__ import annotations

import argparse
import asyncio
import hashlib
import json
import math
import statistics
import zipfile
from collections import defaultdict
from datetime import date, timedelta, timezone
from pathlib import Path
from typing import Any
from zoneinfo import ZoneInfo

from scripts import a1_promo_adjusted_drr_collect as promo
from scripts.wb_a1_associated_conversions import _nm_rows, _read_float, _read_int

SHOP_ID = "5586b2ff-449c-4151-9518-60f46d32b7d9"
WB_CABINET_ID = 573
NMIDS = (
    143023475,
    751657528,
    234375724,
    214754056,
    1256595631,
    266109990,
)
DATE_FROM = date(2026, 8, 29)
DATE_TO = date(2026, 9, 12)
MSK = ZoneInfo("Europe/Moscow")
ANALYSIS_DAYS = tuple(
    DATE_FROM + timedelta(days=index)
    for index in range((DATE_TO - DATE_FROM).days + 1)
)
DAY_STRINGS = tuple(day.isoformat() for day in ANALYSIS_DAYS)
WINDOWS = {
    "BASELINE": ("2026-08-29", "2026-09-02"),
    "SPEND_WAVE": ("2026-09-03", "2026-09-07"),
    "POST_WAVE": ("2026-09-08", "2026-09-12"),
}


def _as_number(value: Any) -> float:
    """Преобразовать API-значение в число без падения на null/GAP."""
    try:
        return float(value or 0)
    except (TypeError, ValueError):
        return 0.0


def _day_from_row(row: dict[str, Any]) -> str:
    """Извлечь дату API-строки в формате MSK ISO date."""
    return str(row.get("date") or row.get("lastChangeDate") or "")[:10]


def _campaign_nmids(campaign: dict[str, Any]) -> set[int]:
    """Извлечь NMID из canonical/legacy WB campaign payload."""
    values: set[int] = set()
    raw_settings = campaign.get("nm_settings") or campaign.get("nmSettings") or []
    if isinstance(raw_settings, list):
        for item in raw_settings:
            if isinstance(item, dict):
                nmid = _read_int(item, "nm_id", "nmId", "nmID")
                if nmid:
                    values.add(nmid)
    return values


def _campaign_meta(campaigns: list[dict[str, Any]]) -> dict[int, dict[str, Any]]:
    """Построить неизменяемую локальную карту campaign identity."""
    result: dict[int, dict[str, Any]] = {}
    for campaign in campaigns:
        adv_id = _read_int(campaign, "advertId", "advert_id", "id")
        if not adv_id:
            continue
        settings = campaign.get("settings")
        settings = settings if isinstance(settings, dict) else {}
        placements = settings.get("placements")
        if not isinstance(placements, dict):
            placements = campaign.get("placement") or campaign.get("placements") or {}
        result[adv_id] = {
            "adv_id": adv_id,
            "nmids": sorted(_campaign_nmids(campaign)),
            "campaign_type": campaign.get("type") or campaign.get("advertType"),
            "payment_model": (
                settings.get("payment_type")
                or settings.get("paymentType")
                or campaign.get("payment_type")
                or campaign.get("paymentType")
            ),
            "placements": placements,
            "status": campaign.get("status"),
            "campaign_name": settings.get("name") or campaign.get("name"),
        }
    return result


def _in_scope(meta: dict[str, Any]) -> bool:
    """Проверить пересечение campaign identity с management scope."""
    return bool(set(meta.get("nmids") or ()) & set(NMIDS))


def _campaign_rows(
    campaigns: list[dict[str, Any]],
    nm_rows: list[dict[str, Any]],
    day_rows: list[dict[str, Any]],
) -> tuple[list[dict[str, Any]], list[str]]:
    """Нормализовать daily campaign×NMID fullstats и зафиксировать identity gaps."""
    meta = _campaign_meta(campaigns)
    grouped: dict[tuple[str, int, int], dict[str, Any]] = {}
    gaps: list[str] = []

    for row in nm_rows:
        day = str(row.get("date") or "")[:10]
        adv_id = _read_int(row, "advert_id", "advertId")
        nmid = _read_int(row, "ordered_nm_id", "nmId", "nmID")
        if day not in DAY_STRINGS or not adv_id or not nmid:
            continue
        campaign = meta.get(adv_id, {})
        if nmid not in NMIDS and not (set(campaign.get("nmids") or ()) & set(NMIDS)):
            continue
        if nmid not in NMIDS:
            gaps.append(f"ADV_NMID_MAPPING_GAP:{adv_id}:{day}:nmid_not_in_scope")
            continue
        key = (day, nmid, adv_id)
        bucket = grouped.setdefault(
            key,
            {
                "date_msk": day,
                "nmid": nmid,
                "adv_id": adv_id,
                "campaign_type": campaign.get("campaign_type"),
                "payment_model": campaign.get("payment_model"),
                "placements": campaign.get("placements"),
                "status_if_available": campaign.get("status"),
                "spend": 0.0,
                "impressions": 0,
                "clicks": 0,
                "carts": 0,
                "attributed_orders": 0,
                "ctr": None,
                "cpc": None,
                "attribution_semantics": "WB attributed; never factual sales",
            },
        )
        bucket["spend"] += _as_number(row.get("spend"))
        bucket["impressions"] += _read_int(row, "views", "impressions")
        bucket["clicks"] += _read_int(row, "clicks")
        bucket["carts"] += _read_int(row, "atbs", "carts")
        bucket["attributed_orders"] += _read_int(row, "orders")

    spend_by_adv_day: dict[tuple[str, int], float] = defaultdict(float)
    for row in day_rows:
        day = str(row.get("date") or "")[:10]
        adv_id = _read_int(row, "advert_id", "advertId")
        if day in DAY_STRINGS and adv_id:
            spend_by_adv_day[(day, adv_id)] += _as_number(row.get("day_spend"))

    for (day, adv_id), spend in spend_by_adv_day.items():
        campaign = meta.get(adv_id, {})
        if spend <= 0 or not _in_scope(campaign):
            continue
        if not any(key[0] == day and key[2] == adv_id for key in grouped):
            gaps.append(f"ADV_NMID_DAILY_BREAKDOWN_GAP:{adv_id}:{day}")

    rows = []
    for row in grouped.values():
        impressions = int(row["impressions"])
        clicks = int(row["clicks"])
        spend = float(row["spend"])
        row["ctr"] = round(100 * clicks / impressions, 6) if impressions else None
        row["cpc"] = round(spend / clicks, 6) if clicks else None
        row["spend"] = round(spend, 6)
        rows.append(row)
    rows.sort(key=lambda item: (item["date_msk"], item["nmid"], item["adv_id"]))
    return rows, sorted(set(gaps))


def _dedupe_orders(rows: list[dict[str, Any]]) -> tuple[list[dict[str, Any]], str, int]:
    """Дедуплицировать supplier orders и вернуть rows/key/число дублей."""
    result: list[dict[str, Any]] = []
    seen: set[str] = set()
    duplicate_count = 0
    for row in rows:
        key_value = (
            row.get("srid")
            or row.get("rid")
            or row.get("gNumber")
            or "|".join(
                [
                    str(row.get("nmId") or row.get("nmID") or ""),
                    _day_from_row(row),
                    str(row.get("finishedPrice") or row.get("priceWithDisc") or ""),
                    str(row.get("barcode") or ""),
                    str(row.get("orderUid") or ""),
                ]
            )
        )
        key = str(key_value)
        if key in seen:
            duplicate_count += 1
            continue
        seen.add(key)
        result.append(row)
    dedupe_key = "srid|rid|gNumber; fallback nmId+date+price+barcode+orderUid"
    return result, dedupe_key, duplicate_count


def _sales_rows(
    orders: list[dict[str, Any]],
) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    """Построить полную daily factual sales matrix для шести NMID."""
    deduped, dedupe_key, duplicate_count = _dedupe_orders(orders)
    buckets: dict[tuple[str, int], dict[str, Any]] = defaultdict(
        lambda: {"factual_orders": 0, "factual_units": 0.0, "factual_GMV": 0.0}
    )
    for row in deduped:
        day = _day_from_row(row)
        nmid = _read_int(row, "nmId", "nmID", "nm_id")
        if day not in DAY_STRINGS or nmid not in NMIDS:
            continue
        if str(row.get("isCancel")).lower() in {"true", "1"}:
            continue
        bucket = buckets[(day, nmid)]
        bucket["factual_orders"] += 1
        quantity = _read_float(row, "quantity", "count", "qty") or 1.0
        bucket["factual_units"] += quantity
        bucket["factual_GMV"] += _read_float(
            row, "finishedPrice", "priceWithDisc", "totalPrice"
        )

    rows: list[dict[str, Any]] = []
    for day in DAY_STRINGS:
        for nmid in NMIDS:
            value = buckets[(day, nmid)]
            rows.append(
                {
                    "date_msk": day,
                    "nmid": nmid,
                    "factual_orders": value["factual_orders"],
                    "factual_units": round(value["factual_units"], 4),
                    "factual_GMV": round(value["factual_GMV"], 2),
                    "imtID": None,
                    "glue_group": "GAP",
                }
            )
    date_counts = {
        day: sum(1 for row in deduped if _day_from_row(row) == day)
        for day in DAY_STRINGS
    }
    coverage = {
        "date_from": DATE_FROM.isoformat(),
        "date_to": DATE_TO.isoformat(),
        "pages_fetched": "reported_by_paginator_in_collection_manifest",
        "rows_fetched": len(orders),
        "rows_after_dedupe": len(deduped),
        "duplicate_rows_removed": duplicate_count,
        "dedupe_key": dedupe_key,
        "missing_dates": [day for day, count in date_counts.items() if count == 0],
        "coverage_status": (
            "COMPLETE_DATES_WITH_ZERO_ROWS_EXPLICIT"
            if not any(count == 0 for count in date_counts.values())
            else "GAP_MISSING_SOURCE_ROWS"
        ),
    }
    return rows, coverage


def _daily_metrics(rows: list[dict[str, Any]], key_fields: tuple[str, ...]) -> dict[tuple[Any, ...], dict[str, float]]:
    """Суммировать нормализованные daily rows по указанному ключу."""
    result: dict[tuple[Any, ...], dict[str, float]] = defaultdict(
        lambda: {"spend": 0.0, "impressions": 0.0, "clicks": 0.0}
    )
    for row in rows:
        key = tuple(row[field] for field in key_fields)
        result[key]["spend"] += _as_number(row.get("spend"))
        result[key]["impressions"] += _as_number(row.get("impressions"))
        result[key]["clicks"] += _as_number(row.get("clicks"))
    return result


def _pearson(xs: list[float], ys: list[float]) -> tuple[float | None, int]:
    """Рассчитать Pearson r; малые выборки явно возвращаются как GAP."""
    pairs = [(x, y) for x, y in zip(xs, ys) if math.isfinite(x) and math.isfinite(y)]
    n = len(pairs)
    if n < 5:
        return None, n
    x_values = [pair[0] for pair in pairs]
    y_values = [pair[1] for pair in pairs]
    x_mean = statistics.mean(x_values)
    y_mean = statistics.mean(y_values)
    numerator = sum((x - x_mean) * (y - y_mean) for x, y in pairs)
    denominator = math.sqrt(
        sum((x - x_mean) ** 2 for x in x_values)
        * sum((y - y_mean) ** 2 for y in y_values)
    )
    return (round(numerator / denominator, 6) if denominator else None), n


def _window(day: str, name: str) -> bool:
    """Проверить принадлежность дня к именованному окну."""
    start, end = WINDOWS[name]
    return start <= day <= end


def _window_summary(
    sales: list[dict[str, Any]],
    campaign_rows: list[dict[str, Any]],
) -> dict[str, Any]:
    """Собрать per-NMID и whole-store оконные агрегаты."""
    spend_by_nmid_day: dict[tuple[str, int], float] = defaultdict(float)
    for row in campaign_rows:
        spend_by_nmid_day[(row["date_msk"], row["nmid"])] += _as_number(row["spend"])
    sales_by_nmid: dict[tuple[str, int], dict[str, float]] = {
        (row["date_msk"], row["nmid"]): row for row in sales
    }

    per_nmid: dict[str, Any] = {}
    for nmid in NMIDS:
        values: dict[str, dict[str, float]] = {}
        for name in WINDOWS:
            selected = [
                sales_by_nmid[(day, nmid)]
                for day in DAY_STRINGS
                if _window(day, name)
            ]
            spend = sum(
                spend_by_nmid_day[(day, nmid)]
                for day in DAY_STRINGS
                if _window(day, name)
            )
            values[name] = {
                "orders": sum(row["factual_orders"] for row in selected),
                "units": sum(row["factual_units"] for row in selected),
                "GMV": round(sum(row["factual_GMV"] for row in selected), 2),
                "ad_spend": round(spend, 2),
                "avg_daily_spend": round(spend / 5, 2),
                "avg_daily_GMV": round(
                    sum(row["factual_GMV"] for row in selected) / 5, 2
                ),
            }
        baseline = values["BASELINE"]
        wave = values["SPEND_WAVE"]
        post = values["POST_WAVE"]
        spend_delta = wave["ad_spend"] - baseline["ad_spend"]
        per_nmid[str(nmid)] = {
            **values,
            "spend_change_wave_vs_baseline_abs": round(spend_delta, 2),
            "spend_change_wave_vs_baseline_pct": (
                round(100 * spend_delta / baseline["ad_spend"], 2)
                if baseline["ad_spend"]
                else None
            ),
            "GMV_change_post_vs_wave_abs": round(post["GMV"] - wave["GMV"], 2),
            "GMV_change_post_vs_wave_pct": (
                round(100 * (post["GMV"] - wave["GMV"]) / wave["GMV"], 2)
                if wave["GMV"]
                else None
            ),
            "orders_change_post_vs_wave_abs": post["orders"] - wave["orders"],
            "orders_change_post_vs_wave_pct": (
                round(100 * (post["orders"] - wave["orders"]) / wave["orders"], 2)
                if wave["orders"]
                else None
            ),
            "GMV_change_post_vs_baseline_abs": round(post["GMV"] - baseline["GMV"], 2),
            "GMV_change_post_vs_baseline_pct": (
                round(100 * (post["GMV"] - baseline["GMV"]) / baseline["GMV"], 2)
                if baseline["GMV"]
                else None
            ),
        }

    store: dict[str, Any] = {}
    for name in WINDOWS:
        selected = [row for row in sales if _window(row["date_msk"], name)]
        spend = sum(
            spend_by_nmid_day[(row["date_msk"], row["nmid"])] for row in selected
        )
        gmv = sum(row["factual_GMV"] for row in selected)
        orders = sum(row["factual_orders"] for row in selected)
        store[name] = {
            "avg_daily_spend": round(spend / 5, 2),
            "avg_daily_orders": round(orders / 5, 2),
            "avg_daily_GMV": round(gmv / 5, 2),
            "aggregate_DRR": round(100 * spend / gmv, 4) if gmv else None,
        }
    return {"per_nmid": per_nmid, "store": store}


def _lag_analysis(
    sales: list[dict[str, Any]],
    campaign_rows: list[dict[str, Any]],
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    """Рассчитать SKU и store lag correlations для 0..5 дней."""
    spend = defaultdict(float)
    for row in campaign_rows:
        spend[(row["date_msk"], row["nmid"])] += _as_number(row["spend"])
    sales_map = {(row["date_msk"], row["nmid"]): row for row in sales}
    sku_rows: list[dict[str, Any]] = []
    for nmid in NMIDS:
        for lag in range(6):
            xs: list[float] = []
            gmvs: list[float] = []
            orders: list[float] = []
            for index, day in enumerate(ANALYSIS_DAYS):
                target_index = index + lag
                if target_index >= len(ANALYSIS_DAYS):
                    continue
                target_day = ANALYSIS_DAYS[target_index].isoformat()
                xs.append(spend[(day.isoformat(), nmid)])
                target = sales_map[(target_day, nmid)]
                gmvs.append(target["factual_GMV"])
                orders.append(target["factual_orders"])
            gmv_r, gmv_n = _pearson(xs, gmvs)
            order_r, order_n = _pearson(xs, orders)
            sku_rows.append(
                {
                    "nmid": nmid,
                    "lag_days": lag,
                    "GMV_r": gmv_r,
                    "GMV_n": gmv_n,
                    "orders_r": order_r,
                    "orders_n": order_n,
                }
            )

    store_spend = {
        day: sum(spend[(day, nmid)] for nmid in NMIDS) for day in DAY_STRINGS
    }
    store_sales = {
        day: {
            "GMV": sum(
                row["factual_GMV"] for row in sales if row["date_msk"] == day
            ),
            "orders": sum(
                row["factual_orders"] for row in sales if row["date_msk"] == day
            ),
        }
        for day in DAY_STRINGS
    }
    store_rows: list[dict[str, Any]] = []
    for lag in range(6):
        xs = []
        gmvs = []
        orders = []
        for index, day in enumerate(ANALYSIS_DAYS):
            target_index = index + lag
            if target_index >= len(ANALYSIS_DAYS):
                continue
            xs.append(store_spend[day.isoformat()])
            target_day = ANALYSIS_DAYS[target_index].isoformat()
            gmvs.append(store_sales[target_day]["GMV"])
            orders.append(store_sales[target_day]["orders"])
        gmv_r, gmv_n = _pearson(xs, gmvs)
        order_r, order_n = _pearson(xs, orders)
        store_rows.append(
            {
                "lag_days": lag,
                "GMV_r": gmv_r,
                "GMV_n": gmv_n,
                "orders_r": order_r,
                "orders_n": order_n,
            }
        )
    return sku_rows, store_rows


def _rankings(
    window_summary: dict[str, Any],
    campaign_rows: list[dict[str, Any]],
) -> dict[str, Any]:
    """Сформировать spend-wave, sales-contributor и cross-SKU rankings."""
    grouped: dict[tuple[int, int], dict[str, float]] = defaultdict(
        lambda: {"baseline": 0.0, "wave": 0.0}
    )
    for row in campaign_rows:
        key = (row["nmid"], row["adv_id"])
        if _window(row["date_msk"], "BASELINE"):
            grouped[key]["baseline"] += _as_number(row["spend"]) / 5
        elif _window(row["date_msk"], "SPEND_WAVE"):
            grouped[key]["wave"] += _as_number(row["spend"]) / 5
    contributors = []
    for (nmid, adv_id), values in grouped.items():
        incremental = values["wave"] - values["baseline"]
        contributors.append(
            {
                "nmid": nmid,
                "adv_id": adv_id,
                "baseline_avg_daily_spend": round(values["baseline"], 2),
                "wave_avg_daily_spend": round(values["wave"], 2),
                "incremental_daily_spend": round(incremental, 2),
            }
        )
    total_incremental = sum(max(row["incremental_daily_spend"], 0) for row in contributors)
    for row in contributors:
        row["share_of_total_incremental_spend"] = (
            round(100 * max(row["incremental_daily_spend"], 0) / total_incremental, 2)
            if total_incremental
            else None
        )
    contributors.sort(key=lambda row: -row["incremental_daily_spend"])

    sales_contributors = []
    for nmid, values in window_summary["per_nmid"].items():
        wave = values["SPEND_WAVE"]
        post = values["POST_WAVE"]
        delta = post["avg_daily_GMV"] - wave["avg_daily_GMV"]
        sales_contributors.append(
            {
                "nmid": int(nmid),
                "baseline_avg_daily_GMV": values["BASELINE"]["avg_daily_GMV"],
                "wave_GMV_per_day": wave["avg_daily_GMV"],
                "post_GMV_per_day": post["avg_daily_GMV"],
                "post_GMV_increment_vs_wave": round(delta, 2),
                "post_orders_increment_vs_wave": post["orders"] - wave["orders"],
            }
        )
    positive_growth = sum(
        max(row["post_GMV_increment_vs_wave"], 0) for row in sales_contributors
    )
    for row in sales_contributors:
        row["share_of_total_store_GMV_increment"] = (
            round(
                100 * max(row["post_GMV_increment_vs_wave"], 0) / positive_growth,
                2,
            )
            if positive_growth
            else None
        )
    sales_contributors.sort(key=lambda row: -row["post_GMV_increment_vs_wave"])

    cross_sku = []
    for row in contributors[:10]:
        nmid = row["nmid"]
        own = window_summary["per_nmid"][str(nmid)]
        other_change = sum(
            values["POST_WAVE"]["GMV"] - values["SPEND_WAVE"]["GMV"]
            for other, values in window_summary["per_nmid"].items()
            if int(other) != nmid
        )
        cross_sku.append(
            {
                "advertising_entry_nmid": nmid,
                "adv_id": row["adv_id"],
                "spend_wave_increment": row["incremental_daily_spend"],
                "same_sku_post_GMV_change": round(
                    own["POST_WAVE"]["GMV"] - own["SPEND_WAVE"]["GMV"], 2
                ),
                "other_scope_post_GMV_change": round(other_change, 2),
                "related_glue_post_GMV_change": "GAP",
                "interpretation": "observational co-movement only",
            }
        )
    return {
        "top_spend_wave_contributors": contributors,
        "top_post_wave_sales_contributors": sales_contributors,
        "cross_sku_trace": cross_sku,
    }


def _write_jsonl(path: Path, rows: list[dict[str, Any]]) -> None:
    """Записать machine-readable JSONL без потери Unicode."""
    with path.open("w", encoding="utf-8") as handle:
        for row in rows:
            handle.write(json.dumps(row, ensure_ascii=False, sort_keys=True) + "\n")


def _sha256(path: Path) -> str:
    """Посчитать SHA-256 локального артефакта."""
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _materialize(output_dir: Path, payload: dict[str, Any]) -> Path:
    """Материализовать declared outputs, ZIP и checksum manifest."""
    output_dir.mkdir(parents=True, exist_ok=True)
    _write_jsonl(output_dir / "daily_campaign_inputs.jsonl", payload["campaign_rows"])
    _write_jsonl(output_dir / "daily_sku_factual_sales.jsonl", payload["sales_rows"])
    _write_jsonl(output_dir / "daily_store_control.jsonl", payload["store_rows"])
    for name in ("coverage.json", "integrity_report.json", "collection_manifest.json", "analysis_report.json"):
        (output_dir / name).write_text(
            json.dumps(payload[name], ensure_ascii=False, indent=2, sort_keys=True),
            encoding="utf-8",
        )

    zip_path = output_dir / "prokraft_delayed_ad_effect_evidence.zip"
    declared = [
        "daily_campaign_inputs.jsonl",
        "daily_sku_factual_sales.jsonl",
        "daily_store_control.jsonl",
        "coverage.json",
        "integrity_report.json",
        "collection_manifest.json",
        "analysis_report.json",
    ]
    with zipfile.ZipFile(zip_path, "w", compression=zipfile.ZIP_DEFLATED) as archive:
        for name in declared:
            archive.write(output_dir / name, arcname=name)
    manifest = {
        name: {"sha256": _sha256(output_dir / name), "bytes": (output_dir / name).stat().st_size}
        for name in declared + [zip_path.name]
    }
    (output_dir / "sha256_manifest.json").write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2, sort_keys=True),
        encoding="utf-8",
    )
    return zip_path


async def _collect() -> dict[str, Any]:
    """Получить свежие WB payload через существующий read-only async pipeline."""
    promo.SHOP_ID = SHOP_ID
    payload = await promo._async_collect_all(DATE_TO, DATE_TO)
    nm_rows, day_rows = _nm_rows(payload["fullstats_raw"])
    campaign_rows, campaign_gaps = _campaign_rows(
        payload["campaigns"], nm_rows, day_rows
    )
    sales_rows, sales_coverage = _sales_rows(payload["orders_raw"])
    spend_by_day = defaultdict(float)
    for row in day_rows:
        day = str(row.get("date") or "")[:10]
        if day in DAY_STRINGS:
            spend_by_day[day] += _as_number(row.get("day_spend"))
    scope_spend_by_day = defaultdict(float)
    for row in campaign_rows:
        scope_spend_by_day[row["date_msk"]] += _as_number(row["spend"])
    store_rows = []
    sales_by_day = defaultdict(lambda: {"orders": 0, "GMV": 0.0})
    for row in sales_rows:
        sales_by_day[row["date_msk"]]["orders"] += row["factual_orders"]
        sales_by_day[row["date_msk"]]["GMV"] += row["factual_GMV"]
    for day in DAY_STRINGS:
        whole_spend = spend_by_day[day]
        whole_gmv = sales_by_day[day]["GMV"]
        store_rows.append(
            {
                "date_msk": day,
                "whole_store_orders": sales_by_day[day]["orders"],
                "whole_store_GMV": round(whole_gmv, 2),
                "whole_store_ad_spend": round(whole_spend, 2),
                "management_scope_ad_spend": round(scope_spend_by_day[day], 2),
                "Store_DRR": round(100 * whole_spend / whole_gmv, 6) if whole_gmv else None,
            }
        )
    return {
        "payload": payload,
        "campaign_rows": campaign_rows,
        "campaign_gaps": campaign_gaps,
        "sales_rows": sales_rows,
        "sales_coverage": sales_coverage,
        "store_rows": store_rows,
    }


def run_collect(output_dir: Path) -> dict[str, Any]:
    """Собрать свежие read-only evidence и выполнить observational analysis."""
    collected = asyncio.run(_collect())
    window_summary = _window_summary(collected["sales_rows"], collected["campaign_rows"])
    sku_lag, store_lag = _lag_analysis(
        collected["sales_rows"], collected["campaign_rows"]
    )
    rankings = _rankings(window_summary, collected["campaign_rows"])
    payload = collected["payload"]
    pages = "GAP: paginator result metadata not exposed by legacy async wrapper"
    coverage = {
        **collected["sales_coverage"],
        "date_from": DATE_FROM.isoformat(),
        "date_to": DATE_TO.isoformat(),
        "campaign_days": len(DAY_STRINGS),
        "campaign_rows": len(collected["campaign_rows"]),
        "campaign_missing_identity_rows": collected["campaign_gaps"],
        "supplier_orders_pagination": "USED via _paginate_supplier_rows",
        "pages_fetched": pages,
        "source_rows_fetched": len(payload["orders_raw"]),
    }
    integrity = {
        "calendar_coverage": coverage["coverage_status"],
        "supplier_orders_paginated": True,
        "supplier_orders_deduplicated": True,
        "dedupe_key": coverage["dedupe_key"],
        "adv_id_nmid_identity_preserved": not collected["campaign_gaps"],
        "attributed_values_used_as_factual_denominator": False,
        "campaign_vs_whole_cabinet_spend_by_day": [
            {
                "date_msk": row["date_msk"],
                "whole_cabinet_spend": row["whole_store_ad_spend"],
                "management_scope_spend": row["management_scope_ad_spend"],
                "difference": round(
                    row["whole_store_ad_spend"] - row["management_scope_ad_spend"], 2
                ),
            }
            for row in collected["store_rows"]
        ],
        "confounders": {
            "buyer_price": "GAP",
            "supplier_price": "GAP",
            "SPP_discount": "GAP",
            "stock_availability": "GAP",
            "FBS_FBO_availability": "GAP",
            "campaign_transitions": "GAP",
            "major_card_changes": "GAP",
        },
        "gaps": sorted(
            set(
                collected["campaign_gaps"]
                + ["PAGES_FETCHED_NOT_EXPOSED_BY_LEGACY_WRAPPER", "GLUE_RELATIONS_GAP"]
            )
        ),
    }
    positive_post_growth = [
        row["post_GMV_increment_vs_wave"]
        for row in rankings["top_post_wave_sales_contributors"]
        if row["post_GMV_increment_vs_wave"] > 0
    ]
    analysis = {
        "STORE_WINDOWS": window_summary["store"],
        "TOP_SPEND_WAVE_CONTRIBUTORS": rankings["top_spend_wave_contributors"],
        "TOP_POST_WAVE_SALES_CONTRIBUTORS": rankings["top_post_wave_sales_contributors"],
        "SKU_TRACE": {
            str(nmid): {
                "spend_wave_delta": window_summary["per_nmid"][str(nmid)][
                    "spend_change_wave_vs_baseline_abs"
                ],
                "post_orders_delta": window_summary["per_nmid"][str(nmid)][
                    "orders_change_post_vs_wave_abs"
                ],
                "post_GMV_delta": window_summary["per_nmid"][str(nmid)][
                    "GMV_change_post_vs_wave_abs"
                ],
                "lags": [row for row in sku_lag if row["nmid"] == nmid],
            }
            for nmid in NMIDS
        },
        "STORE_LAG_TRACE": store_lag,
        "CROSS_SKU_TRACE": rankings["cross_sku_trace"],
        "CONFOUNDERS": integrity["confounders"],
        "HYPOTHESIS_VERDICT": (
            "INSUFFICIENT_EVIDENCE"
            if integrity["gaps"]
            else "MODERATE_TRACE"
        ),
        "DID_SPEND_WAVE_PRECEDE_STORE_GROWTH": (
            "YES"
            if window_summary["store"]["POST_WAVE"]["avg_daily_GMV"]
            > window_summary["store"]["SPEND_WAVE"]["avg_daily_GMV"]
            else "NO"
        ),
        "WAS_GROWTH_CONCENTRATED_IN_ADVERTISED_SKUS": (
            "YES" if len(positive_post_growth) <= 2 else "MIXED"
        ),
        "IS_SAME_SKU_RESPONSE_ENOUGH_TO_EXPLAIN_STORE_GROWTH": "UNCLEAR",
        "IS_CROSS_SKU_HALO_PLAUSIBLE_FROM_DATA": "UNCLEAR",
        "MOST_IMPORTANT_FINDING": (
            "Fresh store timing and scoped campaign evidence are reported separately; "
            "observational attribution remains limited by explicit integrity gaps."
        ),
    }
    manifest = {
        "checked_at_msk": __import__("datetime").datetime.now(timezone.utc).astimezone(MSK).isoformat(),
        "shop_id": SHOP_ID,
        "wb_cabinet_id": WB_CABINET_ID,
        "management_scope": list(NMIDS),
        "date_from": DATE_FROM.isoformat(),
        "date_to": DATE_TO.isoformat(),
        "windows": WINDOWS,
        "all_production_writes": 0,
        "source_campaigns": len(payload["campaigns"]),
        "source_fullstats_items": len(payload["fullstats_raw"]),
        "source_supplier_order_rows": len(payload["orders_raw"]),
        "outputs": [
            "daily_campaign_inputs.jsonl",
            "daily_sku_factual_sales.jsonl",
            "daily_store_control.jsonl",
            "coverage.json",
            "integrity_report.json",
            "collection_manifest.json",
            "analysis_report.json",
            "prokraft_delayed_ad_effect_evidence.zip",
            "sha256_manifest.json",
        ],
    }
    final_payload = {
        "campaign_rows": collected["campaign_rows"],
        "sales_rows": collected["sales_rows"],
        "store_rows": collected["store_rows"],
        "coverage.json": coverage,
        "integrity_report.json": integrity,
        "collection_manifest.json": manifest,
        "analysis_report.json": analysis,
    }
    zip_path = _materialize(output_dir, final_payload)
    print(f"PRIMARY_ARTIFACT={zip_path}")
    print(f"ZIP_SHA256={_sha256(zip_path)}")
    print("ARTIFACT_CLASS=PROKRAFT_DELAYED_AD_EFFECT_EVIDENCE")
    print(f"COVERAGE_STATUS={coverage['coverage_status']}")
    print(f"INTEGRITY_STATUS={'PASS' if not integrity['gaps'] else 'GAP'}")
    print(f"ANALYSIS_STATUS={'COMPLETE_WITH_GAPS' if integrity['gaps'] else 'COMPLETE'}")
    print("ALL_PRODUCTION_WRITES=0")
    return manifest


def parse_args() -> argparse.Namespace:
    """Разобрать CLI параметры collector."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output-dir", required=True)
    return parser.parse_args()


def main() -> None:
    """Запустить read-only collection и materialization."""
    args = parse_args()
    run_collect(Path(args.output_dir))


if __name__ == "__main__":
    main()
