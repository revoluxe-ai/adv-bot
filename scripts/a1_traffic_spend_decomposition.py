"""READ_ONLY traffic/spend decomposition for a single WB auto campaign (A1).

Собирает GET /adv/v3/fullstats, POST /adv/v0/normquery/stats (per day),
campaign v2 config, PG keywordsetting и latest CH bid_decision_log bids.
"""

from __future__ import annotations

import argparse
import asyncio
import csv
import json
import os
import sys
from collections import defaultdict
from datetime import date, datetime, timedelta, timezone
from pathlib import Path
from typing import Any

import dotenv

dotenv.load_dotenv()

from scripts import ch_a1_evidence as evidence
from scripts.wb_a1_associated_conversions import (
    _date_value,
    _jsonable,
    _nm_rows,
    _read_float,
    _read_int,
)

SHOP_ID = evidence.SHOP_ID
ADV_ID = 37096258
NM_ID = 13713289
SEARCH_ADV_ID = 37096282
PERIOD_A_FROM = date(2026, 8, 22)
PERIOD_A_TO = date(2026, 8, 26)
PERIOD_B_FROM = date(2026, 8, 27)
PERIOD_B_TO = date(2026, 8, 27)
COLLECT_FROM = PERIOD_A_FROM
COLLECT_TO = PERIOD_B_TO

STRATEGY_LETTER = {
    "OFF": "o",
    "MIN_CPA": "M",
    "OPTIMUM": "O",
    "MAX_CONVERSION": "C",
}


def _pg_database() -> str:
    return os.environ.get("POSTGRES_DBNAME") or "adv_updater"


def _bootstrap_cluster_infra() -> None:
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
    ch_host = os.environ.get("CLICK_HOUSE_HOST")
    ch_port = os.environ.get("CLICKHOUSE_PORT", "8123")
    if ch_host:
        evidence.CH_HTTP_URL = f"http://{ch_host}:{ch_port}/"


def _load_pg_keywords(root: Path, sql_dir: Path) -> tuple[dict[str, Any], list[dict[str, str]]]:
    staging = root / "staging"
    staging.mkdir(parents=True, exist_ok=True)
    setting_path = staging / "advsetting_row.csv"
    st = evidence.run_pg_query(
        _pg_database(),
        (
            "SELECT id, adv_id, _search_adv_id, name, type, nmids, active_status, bot_active, "
            "wb_bid_type, wb_placement_search, wb_placement_recommendations, strategy "
            f"FROM public.advsetting WHERE adv_id = {ADV_ID}"
        ),
        setting_path,
        sql_dir / "pg_advsetting_one.sql",
        csv_output=True,
    )
    if not st["success"]:
        raise RuntimeError(f"advsetting query failed: {st['stderr']}")
    with setting_path.open(encoding="utf-8", newline="") as handle:
        settings = list(csv.DictReader(handle))
    if not settings:
        raise RuntimeError(f"advsetting not found for adv_id={ADV_ID}")
    adv_setting = settings[0]
    adv_setting_id = int(adv_setting["id"])
    kw_path = staging / "keywordsetting.csv"
    st2 = evidence.run_pg_query(
        _pg_database(),
        (
            "SELECT id, text, hard_status, strategy_mode, target_place, predict_ctr, "
            "added_clicks, added_views, auto_block, relevant "
            f"FROM public.keywordsetting WHERE adv_setting_id = {adv_setting_id}"
        ),
        kw_path,
        sql_dir / "pg_keywordsetting.sql",
        csv_output=True,
    )
    if not st2["success"]:
        raise RuntimeError(f"keywordsetting query failed: {st2['stderr']}")
    with kw_path.open(encoding="utf-8", newline="") as handle:
        keywords = list(csv.DictReader(handle))
    return adv_setting, keywords


def _load_ch_latest_bids(root: Path, sql_dir: Path) -> dict[str, dict[str, Any]]:
    out = root / "staging" / "latest_bids.jsonl"
    query = (
        f"SELECT norm_query, argMax(cpm_curr, version) AS cpm_curr, "
        f"argMax(final_bid, version) AS final_bid, "
        f"argMax(decision_time, version) AS decision_time "
        f"FROM default_db.bid_decision_log "
        f"WHERE adv_id = {ADV_ID} AND nmid = {NM_ID} "
        f"GROUP BY norm_query"
    )
    st = evidence.run_ch_query(query, out, sql_dir / "ch_latest_bids.sql")
    if not st["success"]:
        return {}
    rows = evidence.read_jsonl(out)
    return {str(r.get("norm_query") or ""): r for r in rows}


def _strategy_letter(mode_raw: str) -> str:
    mode = (mode_raw or "").strip().upper()
    if mode in STRATEGY_LETTER:
        return STRATEGY_LETTER[mode]
    if mode.isdigit():
        mapping = {0: "o", 1: "M", 2: "O", 3: "C"}
        return mapping.get(int(mode), mode)
    return mode_raw or "?"


def _is_off_keyword(kw: dict[str, str] | None) -> bool:
    if kw is None:
        return False
    hard = str(kw.get("hard_status") or "").strip()
    mode = (kw.get("strategy_mode") or "").strip().upper()
    if hard == "3":
        return True
    if mode in ("OFF", "0"):
        return True
    return False


def _classify_query(
    norm_query: str,
    views: int,
    kw_map: dict[str, dict[str, str]],
) -> str:
    kw = kw_map.get(norm_query)
    if kw is None:
        return "UNKNOWN/NOT_CLASSIFIED"
    if _is_off_keyword(kw):
        return "OFF"
    if views >= 100:
        return "MATURE_VISIBLE"
    return "LEARNING_VISIBLE"


def _period_label(day_str: str) -> str:
    try:
        d = date.fromisoformat(day_str[:10])
    except ValueError:
        return "OUT_OF_SCOPE"
    if PERIOD_A_FROM <= d <= PERIOD_A_TO:
        return "A"
    if PERIOD_B_FROM <= d <= PERIOD_B_TO:
        return "B"
    return "OUT_OF_SCOPE"


def _empty_metrics() -> dict[str, float]:
    return {
        "TOTAL_CAMPAIGN_SPEND": 0.0,
        "VISIBLE_QUERY_SPEND": 0.0,
        "MATURE_VISIBLE_SPEND": 0.0,
        "LEARNING_VISIBLE_SPEND": 0.0,
        "QUERY_SPEND_SHARE": 0.0,
        "RESIDUAL": 0.0,
    }


def _finalize_metrics(metrics: dict[str, float]) -> dict[str, float]:
    total = metrics["TOTAL_CAMPAIGN_SPEND"]
    visible = metrics["VISIBLE_QUERY_SPEND"]
    metrics["QUERY_SPEND_SHARE"] = visible / total if total else 0.0
    metrics["RESIDUAL"] = total - visible
    return metrics


async def _collect_wb(
    kw_map: dict[str, dict[str, str]],
) -> tuple[list[dict[str, Any]], list[dict[str, Any]], dict[str, Any], dict[str, Any]]:
    from app.core.di.app_container import AppContainer
    from app.core.di.di_manager import DIManager
    from app.core.mp.wb.api.adapter.promotion_client.normquery_stats.command import (
        GetNormqueryStatsCommand,
        GetNormqueryStatsCommandBatchForAdv,
    )

    async with await DIManager.create(AppContainer) as container:  # type: ignore[attr-defined]
        factory = container.module_resources.wb_manager_hub_factory_container.wb_manager_hub_factory()
        hub = factory.get_wb_manager_hub(SHOP_ID)
        client = hub.wb_data_manager.promotion_manager._client

        pm = hub.wb_data_manager.promotion_manager
        configs = await pm.get_adverts_v2_by_ids([ADV_ID, SEARCH_ADV_ID])
        config_dicts = [_jsonable(c.to_dict()) for c in (configs or [])]
        campaign_meta: dict[str, Any] = {}
        for raw in config_dicts:
            adv_id = _read_int(raw, "id", "advertId")
            settings = raw.get("settings") if isinstance(raw.get("settings"), dict) else {}
            campaign_meta[str(adv_id)] = {
                "adv_id": adv_id,
                "bid_type": raw.get("bid_type"),
                "status": raw.get("status"),
                "payment_type": settings.get("payment_type"),
                "placements": settings.get("placements"),
                "name": settings.get("name"),
                "nm_settings": raw.get("nm_settings") or raw.get("nmSettings"),
            }

        fullstats_adapter = client.fullstats_adapter
        raw_fullstats = await fullstats_adapter._request_chunk(
            [ADV_ID], COLLECT_FROM, COLLECT_TO
        )
        raw_items = [_jsonable(item.to_dict()) for item in (raw_fullstats or [])]

        norm_rows: list[dict[str, Any]] = []
        norm_adapter = client.normquery_stats_adapter
        day = COLLECT_FROM
        while day <= COLLECT_TO:
            command = GetNormqueryStatsCommand(
                date_from=day,
                date_to=day,
                batchs=[GetNormqueryStatsCommandBatchForAdv(adv_id=ADV_ID, nmid=NM_ID)],
            )
            dtos = await norm_adapter.get_adv_v0_normquery_stats(command)
            for dto in dtos or []:
                dto_dict = _jsonable(dto.model_dump())
                for stat in dto_dict.get("stats") or []:
                    norm_rows.append(
                        {
                            "date": day.isoformat(),
                            "adv_id": dto_dict.get("adv_id", ADV_ID),
                            "nm_id": dto_dict.get("nmid", NM_ID),
                            "norm_query": stat.get("norm_query"),
                            "views": int(stat.get("views") or 0),
                            "clicks": int(stat.get("clicks") or 0),
                            "spend": float(stat.get("spend") or 0),
                            "atbs": stat.get("add_to_cart"),
                            "orders": int(stat.get("orders") or 0),
                            "avg_pos": stat.get("avr_pos"),
                            "cpm": stat.get("cpm"),
                            "cpc": stat.get("cpc"),
                            "ctr": stat.get("ctr"),
                        }
                    )
            if day < COLLECT_TO:
                await asyncio.sleep(2)
            day += timedelta(days=1)

        return raw_items, norm_rows, campaign_meta.get(str(ADV_ID), {}), campaign_meta.get(
            str(SEARCH_ADV_ID), {}
        )


def _fullstats_daily(raw_items: list[dict[str, Any]]) -> list[dict[str, Any]]:
    nm_rows, day_rows = _nm_rows(raw_items)
    nm_by_day: dict[str, dict[str, int]] = defaultdict(
        lambda: {"atbs": 0, "views": 0, "clicks": 0, "orders": 0, "sum_price": 0.0}
    )
    for row in nm_rows:
        if row["ordered_nm_id"] != NM_ID:
            continue
        bucket = nm_by_day[row["date"]]
        bucket["atbs"] += int(row.get("atbs") or 0)
        bucket["views"] += int(row.get("views") or 0)
        bucket["clicks"] += int(row.get("clicks") or 0)
        bucket["orders"] += int(row.get("orders") or 0)
        bucket["sum_price"] += float(row.get("sum_price") or 0)

    daily: list[dict[str, Any]] = []
    for day in day_rows:
        if day["advert_id"] != ADV_ID:
            continue
        nm_part = nm_by_day.get(day["date"], {})
        daily.append(
            {
                "date": day["date"],
                "period": _period_label(day["date"]),
                "views": day.get("day_views") or nm_part.get("views", 0),
                "clicks": day.get("day_clicks") or nm_part.get("clicks", 0),
                "spend": day.get("day_spend") or 0.0,
                "atbs": nm_part.get("atbs", 0),
                "orders": day.get("day_orders") or nm_part.get("orders", 0),
                "sum_price": day.get("day_sum_price") or nm_part.get("sum_price", 0.0),
            }
        )
    return daily


def _build_decomposition(
    fullstats_daily: list[dict[str, Any]],
    norm_rows: list[dict[str, Any]],
    kw_map: dict[str, dict[str, str]],
) -> dict[str, Any]:
    period_views: dict[str, dict[str, int]] = defaultdict(lambda: defaultdict(int))
    for row in norm_rows:
        period = _period_label(row["date"])
        if period == "OUT_OF_SCOPE":
            continue
        nq = str(row.get("norm_query") or "")
        period_views[period][nq] += int(row.get("views") or 0)

    period_class: dict[str, dict[str, str]] = {}
    for period, queries in period_views.items():
        period_class[period] = {}
        for nq, views in queries.items():
            period_class[period][nq] = _classify_query(nq, views, kw_map)

    daily_metrics: dict[str, dict[str, float]] = defaultdict(_empty_metrics)
    total_metrics: dict[str, dict[str, float]] = {
        "A": _empty_metrics(),
        "B": _empty_metrics(),
        "ALL": _empty_metrics(),
    }

    for row in fullstats_daily:
        period = row.get("period")
        if period not in ("A", "B"):
            continue
        spend = float(row.get("spend") or 0)
        daily_metrics[row["date"]]["TOTAL_CAMPAIGN_SPEND"] += spend
        total_metrics[period]["TOTAL_CAMPAIGN_SPEND"] += spend
        total_metrics["ALL"]["TOTAL_CAMPAIGN_SPEND"] += spend

    for row in norm_rows:
        period = _period_label(row["date"])
        if period not in ("A", "B"):
            continue
        nq = str(row.get("norm_query") or "")
        spend = float(row.get("spend") or 0)
        cls = period_class.get(period, {}).get(nq) or _classify_query(
            nq, int(row.get("views") or 0), kw_map
        )
        day_key = row["date"]
        if cls == "MATURE_VISIBLE":
            daily_metrics[day_key]["VISIBLE_QUERY_SPEND"] += spend
            daily_metrics[day_key]["MATURE_VISIBLE_SPEND"] += spend
            total_metrics[period]["VISIBLE_QUERY_SPEND"] += spend
            total_metrics[period]["MATURE_VISIBLE_SPEND"] += spend
            total_metrics["ALL"]["VISIBLE_QUERY_SPEND"] += spend
            total_metrics["ALL"]["MATURE_VISIBLE_SPEND"] += spend
        elif cls == "LEARNING_VISIBLE":
            daily_metrics[day_key]["VISIBLE_QUERY_SPEND"] += spend
            daily_metrics[day_key]["LEARNING_VISIBLE_SPEND"] += spend
            total_metrics[period]["VISIBLE_QUERY_SPEND"] += spend
            total_metrics[period]["LEARNING_VISIBLE_SPEND"] += spend
            total_metrics["ALL"]["VISIBLE_QUERY_SPEND"] += spend
            total_metrics["ALL"]["LEARNING_VISIBLE_SPEND"] += spend

    for bucket in daily_metrics.values():
        _finalize_metrics(bucket)
    for bucket in total_metrics.values():
        _finalize_metrics(bucket)

    classified_norm_rows = []
    for row in norm_rows:
        period = _period_label(row["date"])
        nq = str(row.get("norm_query") or "")
        cls = (
            period_class.get(period, {}).get(nq)
            if period in period_class
            else _classify_query(nq, int(row.get("views") or 0), kw_map)
        )
        classified_norm_rows.append({**row, "traffic_class": cls, "period": period})

    return {
        "daily_spend_metrics": dict(sorted(daily_metrics.items())),
        "period_totals": {k: _finalize_metrics(v.copy()) for k, v in total_metrics.items()},
        "normquery_by_day": classified_norm_rows,
        "query_period_classification": period_class,
    }


def _keyword_export(
    keywords: list[dict[str, str]],
    latest_bids: dict[str, dict[str, Any]],
    period_class_all: dict[str, str],
) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for kw in keywords:
        text = str(kw.get("text") or "")
        bid = latest_bids.get(text, {})
        rows.append(
            {
                "normquery": text,
                "hard_status": kw.get("hard_status"),
                "strategy_mode": kw.get("strategy_mode"),
                "strategy_letter": _strategy_letter(str(kw.get("strategy_mode") or "")),
                "target_place": kw.get("target_place"),
                "predict_ctr": kw.get("predict_ctr"),
                "relevant": kw.get("relevant"),
                "auto_block": kw.get("auto_block"),
                "last_cpm_curr": bid.get("cpm_curr"),
                "last_final_bid": bid.get("final_bid"),
                "last_bid_decision_time": bid.get("decision_time"),
                "period_views_all": None,
                "traffic_class_all": period_class_all.get(text),
            }
        )
    return rows


async def run_collect(
    output_dir: Path,
    adv_setting: dict[str, Any],
    keywords: list[dict[str, str]],
    latest_bids: dict[str, dict[str, Any]],
) -> dict[str, Any]:
    kw_map = {str(k.get("text") or ""): k for k in keywords}
    raw_fullstats, norm_rows, auto_meta, search_meta = await _collect_wb(kw_map)
    fullstats_daily = _fullstats_daily(raw_fullstats)
    decomposition = _build_decomposition(fullstats_daily, norm_rows, kw_map)
    period_views_all: dict[str, int] = defaultdict(int)
    for row in norm_rows:
        nq = str(row.get("norm_query") or "")
        period_views_all[nq] += int(row.get("views") or 0)
    period_class_all = {
        nq: _classify_query(nq, views, kw_map) for nq, views in period_views_all.items()
    }
    keyword_rows = _keyword_export(keywords, latest_bids, period_class_all)
    for row in keyword_rows:
        row["period_views_all"] = period_views_all.get(row["normquery"], 0)

    result = {
        "snapshot_at": datetime.now(timezone.utc).isoformat(),
        "shop_id": SHOP_ID,
        "adv_id": ADV_ID,
        "nm_id": NM_ID,
        "search_adv_id": SEARCH_ADV_ID,
        "paired_search_adv_id": adv_setting.get("_search_adv_id") or SEARCH_ADV_ID,
        "mode": "STRICT_READ_ONLY",
        "periods": {
            "A": [PERIOD_A_FROM.isoformat(), PERIOD_A_TO.isoformat()],
            "B": [PERIOD_B_FROM.isoformat(), PERIOD_B_TO.isoformat()],
        },
        "CAMPAIGN_META": {
            "auto": auto_meta,
            "search_paired": search_meta,
            "pg_adv_setting": adv_setting,
        },
        "FULLSTATS_DAILY": fullstats_daily,
        "KEYWORD_SETTINGS": keyword_rows,
        "DECOMPOSITION": decomposition,
    }
    out_path = output_dir / "A1_TRAFFIC_SPEND_DECOMPOSITION_37096258.json"
    out_path.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
    result["output_path"] = str(out_path.resolve())
    return result


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="A1 traffic/spend decomposition READ_ONLY.")
    parser.add_argument("--output-dir", default=".tmp/a1_traffic_spend_37096258")
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    out = Path(args.output_dir).resolve()
    sql_dir = out / "sql"
    sql_dir.mkdir(parents=True, exist_ok=True)
    _bootstrap_cluster_infra()
    adv_setting, keywords = _load_pg_keywords(out, sql_dir)
    latest_bids = _load_ch_latest_bids(out, sql_dir)
    result = asyncio.run(run_collect(out, adv_setting, keywords, latest_bids))
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
