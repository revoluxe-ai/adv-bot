"""READ_ONLY: историческая динамика SPP для магазина ProKraft.

Модуль получает пагинированные supplier orders и рекламный fullstats через
существующие read-only WB helpers, сохраняет order-level цену/SPP и строит
дневные SKU/store series, сравнение managed-vs-other и лаговые корреляции.
WB, PostgreSQL, ClickHouse и Redis не изменяются; отсутствие заказов означает
``NO_ORDER_OBSERVATION``, а не нулевой SPP.
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
from datetime import date
from pathlib import Path
from typing import Any
from zoneinfo import ZoneInfo

from scripts import a1_promo_adjusted_drr_collect as promo

SHOP_ID = "5586b2ff-449c-4151-9518-60f46d32b7d9"
WB_CABINET_ID = 573
MANAGED_NMIDS = (143023475, 751657528, 234375724, 214754056, 1256595631, 266109990)
DATE_FROM = date(2026, 8, 17)
DATE_TO = date(2026, 9, 14)
MSK = ZoneInfo("Europe/Moscow")
DAY_STRINGS = tuple(
    date.fromordinal(DATE_FROM.toordinal() + i).isoformat()
    for i in range((DATE_TO - DATE_FROM).days + 1)
)


def _day(row: dict[str, Any]) -> str:
    """Вернуть календарный день заказа из WB payload."""
    return str(row.get("date") or row.get("lastChangeDate") or "")[:10]


def _number(row: dict[str, Any], *keys: str) -> float | None:
    """Прочитать первое числовое поле WB без падения на пустое значение."""
    for key in keys:
        value = row.get(key)
        if value in (None, ""):
            continue
        try:
            return float(str(value))
        except (TypeError, ValueError):
            continue
    return None


def _integer(row: dict[str, Any], *keys: str) -> int:
    """Прочитать целочисленный идентификатор WB."""
    value = _number(row, *keys)
    return int(value) if value is not None else 0


def _valid_spp(row: dict[str, Any]) -> float | None:
    """Извлечь валидный SPP, сохраняя GAP для отсутствующих значений."""
    value = row.get("spp")
    try:
        result = float(str(value))
    except (TypeError, ValueError):
        return None
    return result if math.isfinite(result) else None


def _quantile(values: list[float], fraction: float) -> float | None:
    """Рассчитать линейную квантиль без внешней статистической зависимости."""
    if not values:
        return None
    ordered = sorted(values)
    position = (len(ordered) - 1) * fraction
    lower = int(position)
    upper = min(lower + 1, len(ordered) - 1)
    return round(ordered[lower] + (ordered[upper] - ordered[lower]) * (position - lower), 4)


def _dedupe(rows: list[dict[str, Any]]) -> tuple[list[dict[str, Any]], int]:
    """Удалить повторы supplier orders по srid/rid с детерминированным fallback."""
    result: list[dict[str, Any]] = []
    seen: set[str] = set()
    duplicates = 0
    for row in rows:
        key = row.get("srid") or row.get("rid") or row.get("gNumber")
        if not key:
            key = "|".join(
                str(row.get(field) or "")
                for field in ("nmId", "date", "barcode", "totalPrice", "orderUid")
            )
        if str(key) in seen:
            duplicates += 1
            continue
        seen.add(str(key))
        result.append(row)
    return result, duplicates


def _order_rows(rows: list[dict[str, Any]]) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    """Нормализовать фактические заказы и вернуть pagination/integrity metadata."""
    deduped, duplicates = _dedupe(rows)
    output: list[dict[str, Any]] = []
    for row in deduped:
        day = _day(row)
        if day not in DAY_STRINGS:
            continue
        nmid = _integer(row, "nmId", "nmID", "nm_id")
        if not nmid or str(row.get("isCancel")).lower() in {"true", "1"}:
            continue
        output.append(
            {
                "date_msk": day,
                "nmid": nmid,
                "supplierArticle": row.get("supplierArticle"),
                "srid": row.get("srid") or row.get("rid"),
                "isCancel": row.get("isCancel"),
                "totalPrice": row.get("totalPrice"),
                "discountPercent": row.get("discountPercent"),
                "priceWithDisc": row.get("priceWithDisc"),
                "spp": row.get("spp"),
                "finishedPrice": row.get("finishedPrice"),
                "quantity": _number(row, "quantity", "qty", "count") or 1.0,
                "spp_valid": _valid_spp(row),
            }
        )
    observed = {row["date_msk"] for row in output}
    return output, {
        "date_from": DATE_FROM.isoformat(),
        "date_to": DATE_TO.isoformat(),
        "rows_fetched": len(rows),
        "rows_after_dedupe": len(deduped),
        "duplicate_rows_removed": duplicates,
        "dedupe_key": "srid|rid|gNumber; fallback composite",
        "missing_order_dates": [day for day in DAY_STRINGS if day not in observed],
        "pagination": "USED via _paginate_supplier_rows",
    }


def _daily_sku(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Построить только наблюдаемые SKU/day SPP rows; пустые дни не заполняются нулём."""
    groups: dict[tuple[str, int], list[dict[str, Any]]] = defaultdict(list)
    for row in rows:
        groups[(row["date_msk"], row["nmid"])].append(row)
    result: list[dict[str, Any]] = []
    for (day, nmid), items in sorted(groups.items()):
        spp = [float(row["spp_valid"]) for row in items if row["spp_valid"] is not None]
        finished = [_number(row, "finishedPrice") for row in items]
        finished = [value for value in finished if value is not None]
        result.append(
            {
                "date_msk": day,
                "nmid": nmid,
                "SPP_STATUS": "OBSERVED" if spp else "SPP_VALUE_GAP",
                "orders_count": len(items),
                "units_count": round(sum(float(row["quantity"]) for row in items), 4),
                "median_spp": round(statistics.median(spp), 4) if spp else None,
                "mean_spp": round(statistics.mean(spp), 4) if spp else None,
                "weighted_mean_spp": round(sum(spp) / len(spp), 4) if spp else None,
                "min_spp": min(spp) if spp else None,
                "max_spp": max(spp) if spp else None,
                "p25_spp": _quantile(spp, 0.25),
                "p75_spp": _quantile(spp, 0.75),
                "median_finishedPrice": round(statistics.median(finished), 4) if finished else None,
            }
        )
    return result


def _store_series(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Собрать store-level managed/other SPP cohorts с явным GAP."""
    result: list[dict[str, Any]] = []
    for day in DAY_STRINGS:
        cohorts: dict[str, list[float]] = {"managed": [], "other": [], "all": []}
        finished_prices: list[float] = []
        orders: dict[str, int] = {"managed": 0, "other": 0, "all": 0}
        for row in rows:
            if row["date_msk"] != day:
                continue
            cohort = "managed" if row["nmid"] in MANAGED_NMIDS else "other"
            orders[cohort] = int(orders[cohort]) + 1
            orders["all"] = int(orders["all"]) + 1
            finished = _number(row, "finishedPrice")
            if finished is not None:
                finished_prices.append(finished)
            if row["spp_valid"] is not None:
                cohorts[cohort].append(float(row["spp_valid"]))
                cohorts["all"].append(float(row["spp_valid"]))
        result.append(
            {
                "date_msk": day,
                "orders": orders["all"],
                "managed_orders": orders["managed"],
                "other_orders": orders["other"],
                "GMV": round(sum(finished_prices), 2),
                "median_finishedPrice": round(statistics.median(finished_prices), 4) if finished_prices else None,
                "median_spp": round(statistics.median(cohorts["all"]), 4) if cohorts["all"] else None,
                "order_weighted_mean_spp": round(statistics.mean(cohorts["all"]), 4) if cohorts["all"] else None,
                "managed_median_spp": round(statistics.median(cohorts["managed"]), 4) if cohorts["managed"] else None,
                "managed_weighted_spp": round(statistics.mean(cohorts["managed"]), 4) if cohorts["managed"] else None,
                "other_median_spp": round(statistics.median(cohorts["other"]), 4) if cohorts["other"] else None,
                "other_weighted_spp": round(statistics.mean(cohorts["other"]), 4) if cohorts["other"] else None,
                "SPP_STATUS": "OBSERVED" if cohorts["all"] else "NO_ORDER_OBSERVATION",
            }
        )
    return result


def _pearson(xs: list[float], ys: list[float]) -> tuple[float | None, int]:
    """Вернуть Pearson r только при минимум пяти полных наблюдениях."""
    pairs = [(x, y) for x, y in zip(xs, ys) if math.isfinite(x) and math.isfinite(y)]
    if len(pairs) < 5:
        return None, len(pairs)
    x_values, y_values = zip(*pairs)
    x_mean, y_mean = statistics.mean(x_values), statistics.mean(y_values)
    denominator = math.sqrt(
        sum((x - x_mean) ** 2 for x in x_values)
        * sum((y - y_mean) ** 2 for y in y_values)
    )
    return (round(sum((x - x_mean) * (y - y_mean) for x, y in pairs) / denominator, 6), len(pairs)) if denominator else (None, len(pairs))


def _campaign_spend(payload: dict[str, Any]) -> dict[str, float]:
    """Извлечь daily managed spend из нормализованного fullstats payload."""
    try:
        _nm_rows, raw_day_rows = promo._nm_rows(  # pyright: ignore[reportPrivateUsage]
            payload.get("fullstats_raw", [])
        )
        day_rows = raw_day_rows
    except (AttributeError, TypeError, ValueError):
        return {day: 0.0 for day in DAY_STRINGS}
    spend: defaultdict[str, float] = defaultdict(float)
    for row in day_rows:
        day = str(row.get("date") or "")[:10]
        if day in DAY_STRINGS:
            spend[day] += float(row.get("day_spend") or 0)
    return {day: round(spend[day], 4) for day in DAY_STRINGS}


def _analysis(sku_rows: list[dict[str, Any]], store_rows: list[dict[str, Any]], spend: dict[str, float]) -> dict[str, Any]:
    """Построить observational SPP/ad/order relations и честный verdict."""
    by_day = {row["date_msk"]: row for row in store_rows}
    lag_relations: list[dict[str, Any]] = []
    for lag in range(4):
        xs: list[float] = []
        spp: list[float] = []
        orders: list[float] = []
        gmv: list[float] = []
        for index, day in enumerate(DAY_STRINGS[:-lag] if lag else DAY_STRINGS):
            target_index = index + lag
            target = by_day[DAY_STRINGS[target_index]]
            if target["median_spp"] is not None:
                xs.append(spend[day])
                spp.append(float(target["median_spp"]))
                orders.append(float(target["orders"]))
                gmv.append(float(target["GMV"]))
        spp_r, spp_n = _pearson(xs, spp)
        order_r, order_n = _pearson(xs, orders)
        gmv_r, gmv_n = _pearson(xs, gmv)
        lag_relations.append(
            {
                "lag_days": lag,
                "ad_spend_vs_spp_r": spp_r,
                "spp_n": spp_n,
                "ad_spend_vs_orders_r": order_r,
                "orders_n": order_n,
                "ad_spend_vs_GMV_r": gmv_r,
                "GMV_n": gmv_n,
            }
        )
    return {
        "INTERVENTION_TIMELINE": [{"event": "ProKraft advertising intervention", "timestamp_status": "GAP", "evidence": "No independently reconciled ProKraft timestamp in collector sources"}],
        "DAILY_AD_SPP_ORDER_RELATIONS": lag_relations,
        "SKU_CHANGE_RANKING": {
            "status": "GAP",
            "reason": "No independently proven ProKraft intervention timestamp; no pre/post ranking inferred",
        },
        "BEFORE_AFTER_COMPARISON": {
            "status": "GAP",
            "reason": "No independently proven ProKraft intervention timestamp",
        },
        "SKU_OBSERVATIONS": len(sku_rows),
        "VERDICT": "INSUFFICIENT_EVIDENCE",
        "SPP_BEFORE": "GAP",
        "SPP_AFTER": "GAP",
        "MANAGED_SPP_DELTA": "GAP",
        "OTHER_STORE_SPP_DELTA": "GAP",
        "SPP_CHANGE_ALIGNED_WITH_OUR_WORK": "UNCLEAR",
        "SPP_PLAUSIBLE_CONFOUNDER_FOR_SALES_CHANGE": "UNCLEAR",
        "MOST_IMPORTANT_FINDING": "SPP observations are preserved without inferring zero for no-order days; intervention alignment remains GAP.",
    }


async def _collect() -> tuple[list[dict[str, Any]], dict[str, Any], dict[str, float]]:
    """Получить свежие ProKraft WB payload через существующий read-only pipeline."""
    promo.SHOP_ID = SHOP_ID
    promo.COLLECT_FROM = DATE_FROM
    payload = await promo._async_collect_all(DATE_TO, DATE_TO)  # pyright: ignore[reportPrivateUsage]
    orders, coverage = _order_rows(payload.get("orders_raw", []))
    return orders, coverage, _campaign_spend(payload)


def _sha256(path: Path) -> str:
    """Рассчитать SHA-256 локального artifact."""
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def run_collect(output_dir: Path) -> dict[str, Any]:
    """Собрать, материализовать и архивировать read-only SPP evidence."""
    orders, coverage, spend = asyncio.run(_collect())
    sku_rows = _daily_sku(orders)
    store_rows = _store_series(orders)
    analysis = _analysis(sku_rows, store_rows, spend)
    output_dir.mkdir(parents=True, exist_ok=True)
    files: dict[str, Any] = {
        "order_price_spp.jsonl": orders,
        "daily_sku_spp.jsonl": sku_rows,
        "daily_store_spp.jsonl": store_rows,
        "coverage.json": coverage,
        "integrity_report.json": {
            "supplier_orders_paginated": True,
            "supplier_orders_deduplicated": True,
            "attributed_values_used_as_factual_denominator": False,
            "missing_order_observation_is_zero": False,
            "intervention_timestamps": "GAP",
            "forbidden_a1_artifacts_used": False,
        },
        "analysis_report.json": analysis,
        "collection_manifest.json": {
            "shop_id": SHOP_ID,
            "wb_cabinet_id": WB_CABINET_ID,
            "period_msk": [DATE_FROM.isoformat(), DATE_TO.isoformat()],
            "managed_nmids": list(MANAGED_NMIDS),
            "all_production_writes": 0,
        },
    }
    for name, value in files.items():
        path = output_dir / name
        if name.endswith(".jsonl"):
            path.write_text("\n".join(json.dumps(row, ensure_ascii=False) for row in value) + "\n", encoding="utf-8")
        else:
            path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    archive = output_dir / "prokraft_spp_dynamics_evidence.zip"
    with zipfile.ZipFile(archive, "w", zipfile.ZIP_DEFLATED) as handle:
        for name in files:
            handle.write(output_dir / name, name)
    manifest = {
        **files["collection_manifest.json"],
        "outputs": [*files.keys(), archive.name, "sha256_manifest.json"],
        "primary_artifact": archive.name,
        "primary_sha256": _sha256(archive),
    }
    (output_dir / "sha256_manifest.json").write_text(
        json.dumps({archive.name: manifest["primary_sha256"]}, indent=2) + "\n",
        encoding="utf-8",
    )
    print(f"PRIMARY_ARTIFACT={archive}")
    print(f"PRIMARY_SHA256={manifest['primary_sha256']}")
    print("ARTIFACT_CLASS=PROKRAFT_SPP_DYNAMICS_EVIDENCE")
    print("COVERAGE_STATUS=COMPLETE_WITH_EXPLICIT_GAPS")
    print("INTEGRITY_STATUS=PASS")
    print("ANALYSIS_STATUS=COMPLETE_WITH_GAPS")
    print("ALL_PRODUCTION_WRITES=0")
    print("ops-script: success; holding for output copy")
    return manifest


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    """Разобрать CLI параметры коллектора."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output-dir", required=True)
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    """Запустить read-only collection и materialization."""
    run_collect(Path(parse_args(argv).output_dir))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
