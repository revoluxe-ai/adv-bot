"""READ_ONLY V2: A1 direct + associated value review with canonical parent AdvSetting contours.

Агрегирует AUTO+SEARCH physical legs per canonical parent AdvSetting.
Проверяет PG mapping, association semantics gate и Auto+Search dedupe.
Без writes и без рекомендаций MAX CPO.
"""

from __future__ import annotations

import argparse
import asyncio
import csv
import json
import os
import re
import sys
from collections import defaultdict
from datetime import date, datetime, timedelta, timezone
from pathlib import Path
from typing import Any
from zoneinfo import ZoneInfo

import dotenv

dotenv.load_dotenv()

from scripts import ch_a1_evidence as evidence
from scripts.wb_a1_associated_conversions import (
    _derive,
    _jsonable,
    _nm_rows,
    _read_float,
    _read_int,
)

SHOP_ID = evidence.SHOP_ID
MSK = ZoneInfo("Europe/Moscow")

CANONICAL_CONTOURS: list[dict[str, int]] = [
    {"adv_setting_id": 194194, "auto_adv_id": 17906286, "search_adv_id": 20646357, "nmid": 85970344},
    {"adv_setting_id": 1151722083, "auto_adv_id": 37236815, "search_adv_id": 34129888, "nmid": 770642983},
    {"adv_setting_id": 209749, "auto_adv_id": 21542370, "search_adv_id": 21542412, "nmid": 14166423},
    {"adv_setting_id": 1151722151, "auto_adv_id": 39900256, "search_adv_id": 39900211, "nmid": 837395782},
    {"adv_setting_id": 193441, "auto_adv_id": 17728892, "search_adv_id": 21027713, "nmid": 7974113},
    {"adv_setting_id": 1151722153, "auto_adv_id": 39943926, "search_adv_id": 39943851, "nmid": 14824677},
    {"adv_setting_id": 109218336, "auto_adv_id": 25183231, "search_adv_id": 25183303, "nmid": 4491664},
    {"adv_setting_id": 109073740, "auto_adv_id": 25174753, "search_adv_id": 25174782, "nmid": 7974106},
    {"adv_setting_id": 1151722085, "auto_adv_id": 37289966, "search_adv_id": 37289981, "nmid": 7839837},
    {"adv_setting_id": 114995429, "auto_adv_id": 25338885, "search_adv_id": 25338922, "nmid": 4491663},
    {"adv_setting_id": 1151721993, "auto_adv_id": 37096258, "search_adv_id": 37096282, "nmid": 13713289},
    {"adv_setting_id": 206579, "auto_adv_id": 20987867, "search_adv_id": 20987465, "nmid": 4491650},
    {"adv_setting_id": 211062, "auto_adv_id": 21604339, "search_adv_id": 21604374, "nmid": 147281596},
]

DIRECT_PRICE_CPO_BASELINE: dict[int, int] = {
    85970344: 423,
    770642983: 159,
    14166423: 104,
    837395782: 235,
    7974113: 287,
    14824677: 600,
    4491664: 600,
    7974106: 266,
    7839837: 94,
    4491663: 600,
    13713289: 86,
    4491650: 500,
    147281596: 259,
}

PG_ADV_FIELDS = [
    "id",
    "adv_id",
    "_search_adv_id",
    "name",
    "nmids",
    "aggressiveness",
    "bot_active",
    "auto_budget_daily_limit",
    "search_auto_budget_daily_limit",
    "target_price_for_order",
    "max_price_for_order",
]

WINDOWS = (3, 7, 14, 28)

ASSOCIATION_SEMANTICS = {
    "API_ROUTE": "GET /adv/v3/fullstats",
    "RAW_FIELD_PATH": "days[].apps[].nms[].{nmId,atbs,orders,sum_price}",
    "DIRECT_CLASSIFICATION_RULE": (
        "attributed nmId (ordered_nm_id) == canonical advertised_nmid for contour"
    ),
    "ASSOCIATED_CLASSIFICATION_RULE": (
        "attributed nmId (ordered_nm_id) != canonical advertised_nmid; "
        "field is purchase/cart SKU in WB nm breakdown, not campaign promoted set"
    ),
}


def _bootstrap() -> None:
    user = os.environ.get("POSTGRES_USER")
    password = os.environ.get("POSTGRES_PASSWORD")
    if user and password:
        evidence._PG_CREDENTIALS = user, password
    pg_host = os.environ.get("POSTGRES_MASTER_HOST") or os.environ.get(
        "POSTGRES_REPLICA_HOST"
    )
    pg_port = os.environ.get("POSTGRES_PORT")
    if pg_host:
        evidence.PG_EXTERNAL_HOST = pg_host
    if pg_port:
        evidence.PG_EXTERNAL_PORT = int(pg_port)


def _parse_nmids(raw: str) -> list[int]:
    out: list[int] = []
    for part in re.split(r"[,;\s]+", str(raw or "")):
        part = part.strip().strip("[]")
        if part.isdigit():
            out.append(int(part))
    return out


def _pg_db() -> str:
    return os.environ.get("POSTGRES_DBNAME") or "adv_updater"


def _msk_now() -> datetime:
    return datetime.now(timezone.utc).astimezone(MSK)


def _iso_msk(dt: datetime) -> str:
    return dt.astimezone(MSK).isoformat()


def _closed_end_day(now: datetime | None = None) -> date:
    return (now or _msk_now()).date() - timedelta(days=1)


def _closed_dates(closed_end: date, days: int) -> set[str]:
    start = closed_end - timedelta(days=days - 1)
    out: set[str] = set()
    d = start
    while d <= closed_end:
        out.add(d.isoformat())
        d += timedelta(days=1)
    return out


def _load_pg_adv(root: Path) -> dict[int, dict[str, str]]:
    staging = root / "staging"
    staging.mkdir(parents=True, exist_ok=True)
    out = staging / "pg_adv.csv"
    ids = ", ".join(str(c["adv_setting_id"]) for c in CANONICAL_CONTOURS)
    cols = ", ".join(f"a.{c}" for c in PG_ADV_FIELDS)
    q = (
        f"SELECT {cols} FROM public.advsetting a "
        f"JOIN public.wbcabinet c ON a.wb_cabinet_id = c.id "
        f"WHERE c.shop_id = '{SHOP_ID}' AND a.id IN ({ids})"
    )
    st = evidence.run_pg_query(_pg_db(), q, out, root / "sql" / "pg_adv_canonical.sql", csv_output=True)
    if not st["success"]:
        raise RuntimeError(st["stderr"])
    by_id: dict[int, dict[str, str]] = {}
    with out.open(encoding="utf-8", newline="") as f:
        for row in csv.DictReader(f):
            by_id[_read_int(row, "id")] = row
    return by_id


def _validate_mapping(pg_by_id: dict[int, dict[str, str]]) -> tuple[bool, list[dict[str, Any]]]:
    conflicts: list[dict[str, Any]] = []
    for spec in CANONICAL_CONTOURS:
        row = pg_by_id.get(spec["adv_setting_id"])
        issues: list[str] = []
        if not row:
            issues.append("missing_parent_advsetting_row")
        else:
            pg_auto = _read_int(row, "adv_id")
            pg_search = _read_int(row, "_search_adv_id")
            nmids = _parse_nmids(row.get("nmids") or "")
            if pg_auto != spec["auto_adv_id"]:
                issues.append(f"adv_id pg={pg_auto} canonical={spec['auto_adv_id']}")
            if pg_search != spec["search_adv_id"]:
                issues.append(
                    f"_search_adv_id pg={pg_search} canonical={spec['search_adv_id']}"
                )
            if spec["nmid"] not in nmids:
                issues.append(f"nmid {spec['nmid']} not in pg nmids={nmids}")
        if issues:
            conflicts.append(
                {
                    "adv_setting_id": spec["adv_setting_id"],
                    "nmid": spec["nmid"],
                    "canonical": spec,
                    "pg_row": row,
                    "issues": issues,
                }
            )
    return len(conflicts) == 0, conflicts


def _safe_div(num: float, den: float) -> float | None:
    if den <= 0:
        return None
    return round(num / den, 6)


def _contour_day_spend(
    day_rows: list[dict[str, Any]], advert_ids: set[int], dates: set[str]
) -> float:
    return round(
        sum(
            r["day_spend"]
            for r in day_rows
            if r["advert_id"] in advert_ids and r["date"] in dates
        ),
        2,
    )


def _contour_views_clicks(
    day_rows: list[dict[str, Any]], advert_ids: set[int], dates: set[str]
) -> tuple[int, int]:
    views = clicks = 0
    for r in day_rows:
        if r["advert_id"] in advert_ids and r["date"] in dates:
            views += r["day_views"]
            clicks += r["day_clicks"]
    return views, clicks


def _aggregate_contour_window(
    nm_rows: list[dict[str, Any]],
    day_rows: list[dict[str, Any]],
    auto_id: int,
    search_id: int,
    advertised_nmid: int,
    dates: set[str],
) -> dict[str, Any]:
    advert_ids = {auto_id, search_id}
    rows = [r for r in nm_rows if r["advert_id"] in advert_ids and r["date"] in dates]
    direct = [r for r in rows if r["ordered_nm_id"] == advertised_nmid]
    assoc = [r for r in rows if r["ordered_nm_id"] != advertised_nmid]

    spend = _contour_day_spend(day_rows, advert_ids, dates)
    views, clicks = _contour_views_clicks(day_rows, advert_ids, dates)

    d_carts = sum(r["atbs"] for r in direct)
    a_carts = sum(r["atbs"] for r in assoc)
    d_orders = sum(r["orders"] for r in direct)
    a_orders = sum(r["orders"] for r in assoc)
    d_gmv = round(sum(r["sum_price"] for r in direct), 2)
    a_gmv = round(sum(r["sum_price"] for r in assoc), 2)
    t_gmv = round(d_gmv + a_gmv, 2)
    t_orders = d_orders + a_orders

    return {
        "spend": spend,
        "views": views,
        "clicks": clicks,
        "direct_carts": d_carts,
        "associated_carts": a_carts,
        "total_carts": d_carts + a_carts,
        "direct_orders": d_orders,
        "associated_orders": a_orders,
        "total_orders": t_orders,
        "direct_gmv": d_gmv,
        "associated_gmv": a_gmv,
        "total_gmv": t_gmv,
        "direct_DRR": _safe_div(spend, d_gmv),
        "total_attributed_DRR": _safe_div(spend, t_gmv),
        "direct_CPO": _safe_div(spend, d_orders),
        "total_attributed_CPO": _safe_div(spend, t_orders),
        "associated_cart_share": _safe_div(a_carts, d_carts + a_carts),
        "associated_order_share": _safe_div(a_orders, t_orders),
        "associated_GMV_share": _safe_div(a_gmv, t_gmv),
        "by_leg": {
            "auto": _leg_metrics(nm_rows, day_rows, auto_id, advertised_nmid, dates),
            "search": _leg_metrics(nm_rows, day_rows, search_id, advertised_nmid, dates),
        },
    }


def _leg_metrics(
    nm_rows: list[dict[str, Any]],
    day_rows: list[dict[str, Any]],
    adv_id: int,
    advertised_nmid: int,
    dates: set[str],
) -> dict[str, Any]:
    ids = {adv_id}
    rows = [r for r in nm_rows if r["advert_id"] == adv_id and r["date"] in dates]
    direct = [r for r in rows if r["ordered_nm_id"] == advertised_nmid]
    assoc = [r for r in rows if r["ordered_nm_id"] != advertised_nmid]
    return {
        "spend": _contour_day_spend(day_rows, ids, dates),
        "direct_orders": sum(r["orders"] for r in direct),
        "associated_orders": sum(r["orders"] for r in assoc),
        "direct_carts": sum(r["atbs"] for r in direct),
        "associated_carts": sum(r["atbs"] for r in assoc),
    }


def _auto_search_dedupe(
    nm_rows: list[dict[str, Any]],
    auto_id: int,
    search_id: int,
    dates: set[str],
) -> tuple[str, dict[str, Any]]:
    auto_map: dict[tuple[str, int], tuple[int, int, float]] = {}
    search_map: dict[tuple[str, int], tuple[int, int, float]] = {}
    for r in nm_rows:
        if r["date"] not in dates:
            continue
        key = (r["date"], r["ordered_nm_id"])
        tup = (r["atbs"], r["orders"], round(r["sum_price"], 2))
        if r["advert_id"] == auto_id:
            auto_map[key] = tup
        elif r["advert_id"] == search_id:
            search_map[key] = tup
    identical: list[dict[str, Any]] = []
    for key in set(auto_map) & set(search_map):
        if auto_map[key] == search_map[key] and any(auto_map[key]):
            identical.append(
                {
                    "date": key[0],
                    "ordered_nm_id": key[1],
                    "atbs": auto_map[key][0],
                    "orders": auto_map[key][1],
                    "sum_price": auto_map[key][2],
                }
            )
    detail = {
        "identical_nm_day_rows_auto_search": len(identical),
        "samples": identical[:10],
        "rule": (
            "GAP if same date+ordered_nm_id has identical atbs/orders/sum_price on both legs"
        ),
    }
    return ("GAP" if identical else "PASS"), detail


def _association_matrix(
    nm_rows: list[dict[str, Any]],
    advert_ids: set[int],
    advertised_nmid: int,
    dates: set[str],
) -> list[dict[str, Any]]:
    grouped: dict[int, dict[str, Any]] = defaultdict(
        lambda: {"associated_carts": 0, "associated_orders": 0, "associated_GMV": 0.0}
    )
    for r in nm_rows:
        if r["advert_id"] not in advert_ids or r["date"] not in dates:
            continue
        purchased = r["ordered_nm_id"]
        if purchased == advertised_nmid:
            continue
        g = grouped[purchased]
        g["associated_carts"] += r["atbs"]
        g["associated_orders"] += r["orders"]
        g["associated_GMV"] += r["sum_price"]
    return [
        {
            "advertised_nmid": advertised_nmid,
            "attributed_nmid": pid,
            "associated_carts": g["associated_carts"],
            "associated_orders": g["associated_orders"],
            "associated_GMV": round(g["associated_GMV"], 2),
        }
        for pid, g in sorted(grouped.items(), key=lambda x: -x[1]["associated_GMV"])
    ]


def _find_semantics_example(
    nm_rows: list[dict[str, Any]], advertised_nmid: int, advert_ids: set[int]
) -> dict[str, Any] | None:
    for r in nm_rows:
        if r["advert_id"] not in advert_ids:
            continue
        if r["ordered_nm_id"] != advertised_nmid and (
            r["atbs"] or r["orders"] or r["sum_price"]
        ):
            return {
                "advertised_nmID": advertised_nmid,
                "attributed_nmID": r["ordered_nm_id"],
                "date": r["date"],
                "advert_id": r["advert_id"],
                "raw_fields": {
                    "atbs": r["atbs"],
                    "orders": r["orders"],
                    "sum_price": r["sum_price"],
                    "app_type": r.get("app_type"),
                },
            }
    return None


async def _fetch_fullstats(adv_ids: list[int], closed_end: date) -> list[dict[str, Any]]:
    from app.core.di.app_container import AppContainer
    from app.core.di.di_manager import DIManager
    from app.core.mp.wb.api.adapter.promotion_client.fullstats.chunked import (
        run_chunked_single_range,
    )

    begin = closed_end - timedelta(days=27)
    raw_items: list[dict[str, Any]] = []
    async with await DIManager.create(AppContainer) as container:  # type: ignore[attr-defined]
        factory = (
            container.module_resources.wb_manager_hub_factory_container.wb_manager_hub_factory()
        )
        hub = factory.get_wb_manager_hub(SHOP_ID)
        client = hub.wb_data_manager.promotion_manager._client
        adapter = client.fullstats_adapter

        async def fetcher(chunk: list[int], b: date, e: date) -> list[Any]:
            return await adapter._request_chunk(chunk, b, e)

        items = await run_chunked_single_range(adv_ids, begin, closed_end, fetcher)
        for item in items:
            raw_items.append(_jsonable(item.to_dict()))
    return raw_items


def _summary_table(
    contours_enriched: list[dict[str, Any]], window: int
) -> list[dict[str, Any]]:
    key = f"{window}d"
    out: list[dict[str, Any]] = []
    for c in contours_enriched:
        w = c["windows"][key]
        out.append(
            {
                "adv_setting_id": c["adv_setting_id"],
                "nmid": c["nmid"],
                "auto_adv_id": c["auto_adv_id"],
                "search_adv_id": c["search_adv_id"],
                "DIRECT_PRICE_CPO_BASELINE": c["DIRECT_PRICE_CPO_BASELINE"],
                "current_target_cpo": c.get("current_target_cpo"),
                "current_max_cpo": c.get("current_max_cpo"),
                "bot_active": c.get("bot_active"),
                "aggressiveness": c.get("aggressiveness"),
                **w,
            }
        )
    return out


async def run_review(root: Path, pg_by_id: dict[int, dict[str, str]]) -> dict[str, Any]:
    checked_at = _msk_now()
    closed_end = _closed_end_day(checked_at)
    mapping_pass, mapping_conflicts = _validate_mapping(pg_by_id)

    adv_ids = sorted(
        {c["auto_adv_id"] for c in CANONICAL_CONTOURS}
        | {c["search_adv_id"] for c in CANONICAL_CONTOURS}
    )
    raw_items = await _fetch_fullstats(adv_ids, closed_end)
    nm_rows, day_rows = _nm_rows(raw_items)
    _, _, _, reconciliation = _derive(nm_rows, day_rows, {})

    semantics_example: dict[str, Any] | None = None
    for spec in CANONICAL_CONTOURS:
        ex = _find_semantics_example(
            nm_rows,
            spec["nmid"],
            {spec["auto_adv_id"], spec["search_adv_id"]},
        )
        if ex:
            semantics_example = ex
            break
    association_semantics_confirmed = "YES" if semantics_example else "NO"

    dedupe_results: list[dict[str, Any]] = []
    dedupe_global = "PASS"
    contours_out: list[dict[str, Any]] = []
    matrix: dict[str, dict[str, list[dict[str, Any]]]] = {}

    for spec in CANONICAL_CONTOURS:
        pg = pg_by_id.get(spec["adv_setting_id"], {})
        windows: dict[str, Any] = {}
        for w in WINDOWS:
            dates = _closed_dates(closed_end, w)
            windows[f"{w}d"] = _aggregate_contour_window(
                nm_rows,
                day_rows,
                spec["auto_adv_id"],
                spec["search_adv_id"],
                spec["nmid"],
                dates,
            )
        dates_28 = _closed_dates(closed_end, 28)
        dedupe_status, dedupe_detail = _auto_search_dedupe(
            nm_rows, spec["auto_adv_id"], spec["search_adv_id"], dates_28
        )
        dedupe_results.append(
            {"nmid": spec["nmid"], "adv_setting_id": spec["adv_setting_id"], **dedupe_detail}
        )
        if dedupe_status == "GAP":
            dedupe_global = "GAP"

        matrix[str(spec["nmid"])] = {
            f"{w}d": _association_matrix(
                nm_rows,
                {spec["auto_adv_id"], spec["search_adv_id"]},
                spec["nmid"],
                _closed_dates(closed_end, w),
            )
            for w in (7, 14, 28)
        }

        contours_out.append(
            {
                **spec,
                "vendorCode": None,
                "bot_active": str(pg.get("bot_active")).lower() in ("true", "t", "1"),
                "aggressiveness": pg.get("aggressiveness"),
                "current_target_cpo": pg.get("target_price_for_order"),
                "current_max_cpo": pg.get("max_price_for_order"),
                "auto_budget_daily_limit": _read_int(pg, "auto_budget_daily_limit"),
                "search_auto_budget_daily_limit": _read_int(
                    pg, "search_auto_budget_daily_limit"
                ),
                "DIRECT_PRICE_CPO_BASELINE": DIRECT_PRICE_CPO_BASELINE.get(spec["nmid"]),
                "windows": windows,
                "AUTO_SEARCH_ATTRIBUTION_DEDUPE": dedupe_status,
            }
        )

    m7 = {r["nmid"]: r for r in _summary_table(contours_out, 7)}
    top_carts = sorted(
        contours_out, key=lambda c: c["windows"]["7d"]["associated_carts"], reverse=True
    )[:5]
    top_gmv = sorted(
        contours_out, key=lambda c: c["windows"]["7d"]["associated_gmv"], reverse=True
    )[:5]
    receivers: dict[int, float] = defaultdict(float)
    for nmid_str, periods in matrix.items():
        for edge in periods.get("7d", []):
            receivers[edge["attributed_nmid"]] += edge["associated_GMV"]

    integrity = "PASS" if reconciliation.get("pass") else "PARTIAL"

    return {
        "STATUS": "OK" if mapping_pass else "MAPPING_CONFLICT",
        "INTEGRITY": integrity,
        "CHECKED_AT_MSK": _iso_msk(checked_at),
        "CLOSED_DAY_END": closed_end.isoformat(),
        "CANONICAL_MAPPING_PASS": mapping_pass,
        "MAPPING_CONFLICTS": mapping_conflicts,
        "ASSOCIATION_SEMANTICS": ASSOCIATION_SEMANTICS,
        "ASSOCIATION_SEMANTICS_RAW_EXAMPLE": semantics_example,
        "ASSOCIATION_SEMANTICS_CONFIRMED": association_semantics_confirmed,
        "AUTO_SEARCH_ATTRIBUTION_DEDUPE": dedupe_global,
        "AUTO_SEARCH_DEDUPE_BY_CONTOUR": dedupe_results,
        "SUMMARY_7D": _summary_table(contours_out, 7),
        "SUMMARY_14D": _summary_table(contours_out, 14),
        "SUMMARY_28D": _summary_table(contours_out, 28),
        "ASSOCIATION_MATRIX": matrix,
        "TOP_TRAFFIC_DONORS_BY_ASSOC_CARTS": [
            {"nmid": c["nmid"], "associated_carts_7d": c["windows"]["7d"]["associated_carts"]}
            for c in top_carts
        ],
        "TOP_TRAFFIC_DONORS_BY_ASSOC_GMV": [
            {"nmid": c["nmid"], "associated_gmv_7d": c["windows"]["7d"]["associated_gmv"]}
            for c in top_gmv
        ],
        "TOP_RECEIVERS": [
            {"attributed_nmid": n, "associated_gmv_7d_inbound": round(v, 2)}
            for n, v in sorted(receivers.items(), key=lambda x: -x[1])[:10]
        ],
        "fullstats_reconciliation": reconciliation,
        "MAX_CPO_CHANGES_EXECUTED": "NO",
        "WB_API_WRITES": 0,
        "DB_WRITES": 0,
        "READ_ONLY": "CONFIRMED",
    }


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--output", default="")
    ap.add_argument("--output-dir", default=".tmp/a1_direct_assoc_value_review_v2")
    args = ap.parse_args(argv)
    root = Path(args.output_dir).resolve()
    root.mkdir(parents=True, exist_ok=True)
    (root / "sql").mkdir(exist_ok=True)
    _bootstrap()
    pg_by_id = _load_pg_adv(root)
    payload = asyncio.run(run_review(root, pg_by_id))
    if args.output:
        Path(args.output).write_text(
            json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8"
        )
    out = root / "a1_direct_associated_value_review_v2.json"
    out.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(payload, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
