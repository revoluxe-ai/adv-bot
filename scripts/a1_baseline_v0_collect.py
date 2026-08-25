"""READ_ONLY baseline V0 collector for WB shop ООО «А1».

Собирает authoritative current-state пакет перед оркестрацией РК:
identity map, PG settings/keywords, CH bid_decision_log, WB fullstats/orders,
product context. Никаких production mutations.
"""

from __future__ import annotations

import argparse
import ast
import asyncio
import csv
import hashlib
import json
import os
import re
import shutil
import sys
import zipfile
from collections import defaultdict
from datetime import date, datetime, timedelta
from pathlib import Path
from typing import Any

import dotenv

dotenv.load_dotenv()

from scripts import ch_a1_evidence as evidence
from scripts.wb_a1_associated_conversions import (
    _config_rows,
    _date_value,
    _derive,
    _jsonable,
    _nm_rows,
    _read_float,
    _read_int,
    _write_jsonl,
)

SHOP_ID = evidence.SHOP_ID
TZ = "Europe/Moscow"
PRIMARY_FROM = date(2026, 8, 11)
PRIMARY_TO = date(2026, 8, 24)
CONTEXT_FROM = date(2026, 7, 29)
CONTEXT_TO = date(2026, 8, 10)
OPEN_DAY = date(2026, 8, 25)
FULLSTATS_FROM = date(2026, 7, 29)
FULLSTATS_TO = date(2026, 8, 25)
BOT_HISTORY_FROM = date(2026, 7, 29)
BOT_HISTORY_TO = date(2026, 8, 25)

SETTING_FIELDS = [
    "id",
    "adv_id",
    "_search_adv_id",
    "type",
    "name",
    "nmids",
    "active_status",
    "bot_active",
    "last_update",
    "plan_for_sales_for_day",
    "target_price_for_order",
    "max_price_for_order",
    "substitute_fact_cpo_for_max",
    "orders_source_for_auto_mode",
    "strategy",
    "auto_update_strategy",
    "aggressiveness",
    "cpm",
    "max_cpm",
    "max_cpc",
    "bidder_active",
    "bidder_for_auto",
    "bidder_mode",
    "wb_bid_type",
    "bidder_step",
    "exponent_predict_ctr",
    "auto_update_exponent",
    "wb_placement_search",
    "wb_placement_recommendations",
    "rec_system_mode",
    "auto_shelf_bid_control_enabled",
    "auto_shelf_bid_control_strategy",
    "auto_budget_watchdog_enabled",
    "auto_budget_daily_limit",
    "search_auto_budget_daily_limit",
    "use_common_budget",
    "common_budget_daily_limit",
    "auto_common_budget",
    "max_balance_adding_for_day",
    "black_phrases",
    "relevant_phrases",
    "pass_days",
    "boost",
    "auto_update_white_list",
    "white_list_mode",
    "auto_add_only_relevant_phrase",
    "target_position_mode",
    "min_target_position",
    "hard_min_ctr",
    "hide_small_query_keywords",
    "hide_zero_views_keywords",
    "automatic_version",
    "wb_cabinet_id",
]


def _pg_database() -> str:
    """Имя PG database из env кластера или adv_updater по умолчанию."""
    return os.environ.get("POSTGRES_DBNAME") or "adv_updater"


def _bootstrap_pg_credentials_from_env() -> bool:
    """Подставить PG credentials из env, если kubectl Secret недоступен."""
    user = os.environ.get("POSTGRES_USER")
    password = os.environ.get("POSTGRES_PASSWORD")
    if not user or not password:
        return False
    evidence._PG_CREDENTIALS = user, password
    return True


def _bootstrap_cluster_infra() -> None:
    """Переключить PG/CH endpoints на in-cluster env из Job secrets."""
    _bootstrap_pg_credentials_from_env()
    pg_host = os.environ.get("POSTGRES_MASTER_HOST") or os.environ.get("POSTGRES_REPLICA_HOST")
    pg_port = os.environ.get("POSTGRES_PORT")
    if pg_host:
        evidence.PG_EXTERNAL_HOST = pg_host
    if pg_port:
        evidence.PG_EXTERNAL_PORT = int(pg_port)
    ch_host = os.environ.get("CLICK_HOUSE_HOST")
    ch_port = os.environ.get("CLICKHOUSE_PORT", "8123")
    if ch_host:
        evidence.CH_HTTP_URL = f"http://{ch_host}:{ch_port}/"


def _ensure_staging(root: Path) -> Path:
    staging = root / "staging"
    staging.mkdir(parents=True, exist_ok=True)
    return staging


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _serialize(value: Any) -> str:
    if value is None:
        return ""
    if isinstance(value, (dict, list)):
        return json.dumps(value, ensure_ascii=False, default=str)
    return str(value)


def _write_csv(path: Path, rows: list[dict[str, Any]], columns: list[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=columns, extrasaction="ignore")
        writer.writeheader()
        for row in rows:
            writer.writerow({col: _serialize(row.get(col)) for col in columns})


def _pg_query(database: str, query: str, out: Path, sql_dir: Path, name: str) -> dict[str, Any]:
    return evidence.run_pg_query(
        database,
        query,
        out,
        sql_dir / f"pg_{name}.sql",
        csv_output=True,
    )


def _ch_query(query: str, out: Path, sql_dir: Path, name: str) -> dict[str, Any]:
    return evidence.run_ch_query(query, out, sql_dir / f"ch_{name}.sql")


def _load_pg_cabinet_and_settings(
    root: Path, sql_dir: Path
) -> tuple[dict[str, Any], list[dict[str, Any]], list[dict[str, Any]], set[int], set[int]]:
    """Загрузить wbcabinet и advsetting по shop_id."""
    staging = _ensure_staging(root)
    cabinet_path = staging / "wbcabinet.csv"
    status = _pg_query(
        _pg_database(),
        (
            "SELECT id, shop_id, active, expiration_time, demo, balance, bonus, "
            "default_max_cpm, balance_went_negative_at FROM public.wbcabinet WHERE shop_id = "
            f"'{SHOP_ID}'"
        ),
        cabinet_path,
        sql_dir,
        "wbcabinet",
    )
    if not status["success"]:
        raise RuntimeError(f"wbcabinet query failed: {status['stderr']}")
    cabinets: list[dict[str, Any]] = []
    cabinet_ids: set[int] = set()
    wb_cabinet_id: int | None = None
    with cabinet_path.open(encoding="utf-8", newline="") as handle:
        for row in csv.DictReader(handle):
            cabinets.append(row)
            if row.get("id"):
                cid = int(row["id"])
                cabinet_ids.add(cid)
                wb_cabinet_id = cid
    if not cabinet_ids:
        raise RuntimeError(f"No wbcabinet row for shop_id={SHOP_ID}")
    ids_sql = ", ".join(str(v) for v in sorted(cabinet_ids))
    setting_path = staging / "advsetting.csv"
    st = _pg_query(
        _pg_database(),
        f"SELECT * FROM public.advsetting WHERE wb_cabinet_id IN ({ids_sql})",
        setting_path,
        sql_dir,
        "advsetting",
    )
    if not st["success"]:
        raise RuntimeError(f"advsetting query failed: {st['stderr']}")
    settings: list[dict[str, Any]] = []
    campaign_ids: set[int] = set()
    nmids: set[int] = set()
    with setting_path.open(encoding="utf-8", newline="") as handle:
        for row in csv.DictReader(handle):
            settings.append(row)
            if row.get("adv_id"):
                campaign_ids.add(int(row["adv_id"]))
            if row.get("_search_adv_id"):
                campaign_ids.add(int(row["_search_adv_id"]))
            try:
                parsed = ast.literal_eval(row.get("nmids") or "[]")
            except (ValueError, SyntaxError):
                parsed = []
            if isinstance(parsed, list):
                for v in parsed:
                    if str(v).isdigit():
                        nmids.add(int(v))
    return (
        {"wb_cabinet_id": wb_cabinet_id, "cabinet_ids": sorted(cabinet_ids), "cabinets": cabinets},
        settings,
        cabinets,
        campaign_ids,
        nmids,
    )


def _load_keywords(root: Path, sql_dir: Path, setting_ids: set[int]) -> list[dict[str, Any]]:
    if not setting_ids:
        return []
    ids_sql = ", ".join(str(v) for v in sorted(setting_ids))
    path = _ensure_staging(root) / "keywordsetting.csv"
    st = _pg_query(
        _pg_database(),
        f"SELECT * FROM public.keywordsetting WHERE adv_setting_id IN ({ids_sql})",
        path,
        sql_dir,
        "keywordsetting",
    )
    if not st["success"]:
        return []
    rows: list[dict[str, Any]] = []
    with path.open(encoding="utf-8", newline="") as handle:
        rows = list(csv.DictReader(handle))
    return rows


def _load_wbcards(root: Path, sql_dir: Path, nmids: set[int]) -> list[dict[str, Any]]:
    if not nmids:
        return []
    ids_sql = ", ".join(str(v) for v in sorted(nmids))
    path = _ensure_staging(root) / "wbcard.csv"
    st = _pg_query(
        _pg_database(),
        f"SELECT nmid, offer_id, name, wb_category_id, json, wb_cabinet_id, adv_setting_id, updated "
        f"FROM public.wbcard WHERE nmid IN ({ids_sql})",
        path,
        sql_dir,
        "wbcard",
    )
    if not st["success"]:
        return []
    return list(csv.DictReader(path.open(encoding="utf-8", newline="")))


async def _wb_campaign_status_and_api(
    settings: list[dict[str, Any]],
) -> tuple[
    dict[int, dict[str, Any]],
    list[dict[str, Any]],
    list[dict[str, Any]],
    list[dict[str, Any]],
    list[int],
    dict[int, set[int]],
]:
    """WB v2 adverts config + fullstats raw за bounded период."""
    from app.core.di.app_container import AppContainer
    from app.core.di.di_manager import DIManager
    from app.core.mp.wb.api.adapter.promotion_client.fullstats.chunked import run_chunked_single_range

    async with await DIManager.create(AppContainer) as container:  # type: ignore[attr-defined]
        factory = container.module_resources.wb_manager_hub_factory_container.wb_manager_hub_factory()
        hub = factory.get_wb_manager_hub(SHOP_ID)
        client = hub.wb_data_manager.promotion_manager._client
        all_configs = await client.campaigns_info_v2_adapter.get_all_campaigns()
        config_dicts = [_jsonable(item.to_dict()) for item in all_configs]
        config_rows, promoted = _config_rows(config_dicts)
        api_ids = sorted({_read_int(item, "id", "advertId", "advert_id") for item in config_dicts})
        api_ids = [i for i in api_ids if i]
        status_map: dict[int, dict[str, Any]] = {}
        for raw in config_dicts:
            adv_id = _read_int(raw, "id", "advertId", "advert_id")
            if not adv_id:
                continue
            settings_block = raw.get("settings") if isinstance(raw.get("settings"), dict) else {}
            status_map[adv_id] = {
                "wb_status": raw.get("status"),
                "wb_status_name": settings_block.get("status") or raw.get("status"),
                "payment_type": settings_block.get("payment_type"),
                "placements": settings_block.get("placements"),
                "campaign_name": settings_block.get("name", ""),
            }
        raw_items: list[dict[str, Any]] = []
        adapter = client.fullstats_adapter
        window_begin = FULLSTATS_FROM
        while window_begin <= FULLSTATS_TO:
            window_end = min(window_begin + timedelta(days=30), FULLSTATS_TO)

            async def fetcher(chunk: list[int], begin: date, end: date) -> list[Any]:
                return await adapter._request_chunk(chunk, begin, end)

            items = await run_chunked_single_range(api_ids, window_begin, window_end, fetcher)
            for item in items:
                raw = _jsonable(item.to_dict())
                raw["_evidence_request_begin"] = window_begin.isoformat()
                raw["_evidence_request_end"] = window_end.isoformat()
                raw_items.append(raw)
            window_begin = window_end + timedelta(days=1)
            if window_begin <= FULLSTATS_TO:
                await asyncio.sleep(20)
        reports = hub.wb_data_manager.reports_manager
        orders_raw: list[dict[str, Any]] = []
        date_from = f"{BOT_HISTORY_FROM.isoformat()}T00:00:00"
        try:
            order_items = await reports.get_supplier_orders(date_from=date_from, flag=0)
            for item in order_items:
                orders_raw.append(_jsonable(item.to_dict() if hasattr(item, "to_dict") else item))
        except Exception as exc:
            orders_raw.append({"_error": str(exc), "date_from": date_from})
        return status_map, config_rows, raw_items, orders_raw, api_ids, promoted


def _normalize_fullstats(
    raw_items: list[dict[str, Any]],
) -> tuple[list[dict[str, Any]], list[dict[str, Any]], dict[str, Any]]:
    """Нормализовать campaign×day и campaign×day×app×nm; проверить nm breakdown."""
    nm_rows, day_rows = _nm_rows(raw_items)
    adv_daily: list[dict[str, Any]] = []
    for day in day_rows:
        views = day.get("day_views", 0)
        clicks = day.get("day_clicks", 0)
        spend = day.get("day_spend", 0)
        adv_daily.append(
            {
                "adv_id": day["advert_id"],
                "date": day["date"],
                "views": views,
                "clicks": clicks,
                "ctr": clicks / views if views else 0,
                "cpc": spend / clicks if clicks else 0,
                "atbs": None,
                "orders": day.get("day_orders"),
                "shks": None,
                "canceled": None,
                "spend": spend,
                "sum_price": day.get("day_sum_price"),
                "period_state": _period_state(day["date"]),
            }
        )
    nm_daily: list[dict[str, Any]] = []
    promoted_nm_by_adv: dict[int, set[int]] = defaultdict(set)
    for row in nm_rows:
        nm_daily.append(
            {
                "adv_id": row["advert_id"],
                "date": row["date"],
                "app_type": row["app_type"],
                "nm_id": row["ordered_nm_id"],
                "views": row["views"],
                "clicks": row["clicks"],
                "ctr": row["clicks"] / row["views"] if row["views"] else 0,
                "cpc": row["spend"] / row["clicks"] if row["clicks"] else 0,
                "atbs": row["atbs"],
                "orders": row["orders"],
                "shks": row["shks"],
                "canceled": row["canceled"],
                "spend": row["spend"],
                "sum_price": row["sum_price"],
                "period_state": _period_state(row["date"]),
            }
        )
    all_nm_in_nm = {r["ordered_nm_id"] for r in nm_rows}
    assoc_check = {
        "unique_nm_in_breakdown": len(all_nm_in_nm),
        "only_promoted_nm": "UNRESOLVED",
        "direct_vs_associative_split": "NOT_AVAILABLE",
        "note": (
            "WB nm breakdown includes ordered_nm_id per app; promoted-vs-other "
            "requires campaign config promoted_nm_ids — decomposition not asserted as pure associative."
        ),
    }
    return adv_daily, nm_daily, assoc_check


def _period_state(day_str: str) -> str:
    try:
        d = date.fromisoformat(day_str[:10])
    except ValueError:
        return "UNKNOWN"
    if d == OPEN_DAY:
        return "OPEN"
    if PRIMARY_FROM <= d <= PRIMARY_TO:
        return "PRIMARY_CLOSED"
    if CONTEXT_FROM <= d <= CONTEXT_TO:
        return "CONTEXT"
    return "OUT_OF_SCOPE"


def _export_bid_history(
    root: Path, sql_dir: Path, campaign_ids: set[int]
) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    """Полная выгрузка bid_decision_log за период (не latest-only)."""
    if not campaign_ids:
        return [], {"status": "EMPTY", "min": None, "max": None}
    campaigns = "(" + ", ".join(str(v) for v in sorted(campaign_ids)) + ")"
    from_ts = f"{BOT_HISTORY_FROM.isoformat()} 00:00:00"
    to_ts = f"{BOT_HISTORY_TO.isoformat()} 23:59:59"
    coverage_path = _ensure_staging(root) / "bid_coverage.jsonl"
    cov_q = (
        f"SELECT count() AS rows, toString(min(decision_time)) AS min_ts, "
        f"toString(max(decision_time)) AS max_ts "
        f"FROM default_db.bid_decision_log "
        f"WHERE adv_id IN {campaigns} "
        f"AND decision_time >= toDateTime('{from_ts}') "
        f"AND decision_time <= toDateTime('{to_ts}')"
    )
    _ch_query(cov_q, coverage_path, sql_dir, "bid_decision_coverage")
    cov_rows = evidence.read_jsonl(coverage_path)
    cov = cov_rows[0] if cov_rows else {}
    out_path = _ensure_staging(root) / "bid_decision_log.jsonl"
    query = (
        f"SELECT adv_id, nmid, norm_query, wb_category, pos_final, pos_final_bucket, "
        f"views_curr, spend_curr, cpm_curr, pos_curr, views_prev, spend_prev, cpm_prev, "
        f"pos_prev, final_bid, decision_source, stats_max_timestamp, decision_time, version "
        f"FROM default_db.bid_decision_log "
        f"WHERE adv_id IN {campaigns} "
        f"AND decision_time >= toDateTime('{from_ts}') "
        f"AND decision_time <= toDateTime('{to_ts}') "
        f"ORDER BY decision_time, adv_id, nmid, norm_query, version"
    )
    st = _ch_query(query, out_path, sql_dir, "bid_decision_log")
    rows: list[dict[str, Any]] = []
    if st["success"]:
        rows = evidence.read_jsonl(out_path)
    return rows, {
        "status": "EXPORTED" if st["success"] else "FAILED",
        "source_rows": int(cov.get("rows") or 0),
        "exported_rows": len(rows),
        "min": cov.get("min_ts"),
        "max": cov.get("max_ts"),
        "stderr": st.get("stderr", "")[:500],
    }


def _probe_setting_history(root: Path, sql_dir: Path, campaign_ids: set[int], nmids: set[int]) -> tuple[list[dict[str, Any]], list[str]]:
    """Профилировать durable history sources; GAP если нет."""
    gaps: list[str] = []
    events: list[dict[str, Any]] = []
    if campaign_ids:
        campaigns = "(" + ", ".join(str(v) for v in sorted(campaign_ids)) + ")"
        probe = (
            f"SELECT count() AS rows FROM default_db.auto_shelf_bid_intervals "
            f"WHERE nmid IN ({', '.join(str(v) for v in sorted(nmids))}) "
            f"AND event_date >= toDate('{BOT_HISTORY_FROM.isoformat()}') "
            f"AND event_date <= toDate('{BOT_HISTORY_TO.isoformat()}')"
        )
        path = _ensure_staging(root) / "auto_shelf_probe.jsonl"
        st = _ch_query(probe, path, sql_dir, "auto_shelf_probe")
        if st["success"] and evidence.read_jsonl(path):
            count = int(evidence.read_jsonl(path)[0].get("rows") or 0)
            if count:
                events.append(
                    {
                        "source": "default_db.auto_shelf_bid_intervals",
                        "rows_in_period": count,
                        "fields": "mode,bid_minor,price_minor deltas",
                        "confidence": "MEDIUM",
                    }
                )
    for field in (
        "max_price_for_order",
        "target_price_for_order",
        "strategy",
        "aggressiveness",
        "bot_active",
        "budget_limits",
        "keyword_mode",
    ):
        gaps.append(f"DURABLE_HISTORY_{field.upper()}: GAP — no PG/CH event log with before/after in audited stores")
    return events, gaps


def _build_identity_map(
    settings: list[dict[str, Any]],
    wb_status: dict[int, dict[str, Any]],
) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for s in settings:
        adv_id = int(s.get("adv_id") or 0)
        search_id = int(s.get("_search_adv_id") or 0) if s.get("_search_adv_id") else None
        wb = wb_status.get(adv_id, {})
        wb_search = wb_status.get(search_id or 0, {}) if search_id else {}
        rows.append(
            {
                "shop_id": SHOP_ID,
                "wb_cabinet_id": s.get("wb_cabinet_id"),
                "adv_setting_id": s.get("id"),
                "adv_id": adv_id,
                "search_adv_id": search_id,
                "type": s.get("type"),
                "campaign_name": s.get("name"),
                "nmids": s.get("nmids"),
                "wb_actual_status_auto": wb.get("wb_status"),
                "wb_actual_status_search": wb_search.get("wb_status") if search_id else None,
                "pg_active_status": s.get("active_status"),
                "bot_active": s.get("bot_active"),
                "automatic_version": s.get("automatic_version"),
                "status_mismatch_auto": (
                    str(wb.get("wb_status")) != str(s.get("active_status"))
                    if wb.get("wb_status") is not None
                    else "UNKNOWN"
                ),
            }
        )
    return rows


def _orders_nm_daily(orders_raw: list[dict[str, Any]]) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    """Day×nmID aggregates from supplier orders."""
    by_day_nm: dict[tuple[str, int], dict[str, Any]] = {}
    store_by_day: dict[str, dict[str, Any]] = {}
    for item in orders_raw:
        if item.get("_error"):
            continue
        nm = _read_int(item, "nmId", "nmID", "nm_id")
        dt = str(item.get("date") or item.get("lastChangeDate") or "")[:10]
        if not dt or not nm:
            continue
        qty = _read_int(item, "quantity", "qty") or 1
        price = _read_float(item, "totalPrice", "priceWithDisc", "finishedPrice")
        key = (dt, nm)
        cell = by_day_nm.setdefault(key, {"date": dt, "nm_id": nm, "order_units": 0, "gmv": 0.0})
        cell["order_units"] += qty
        cell["gmv"] += price * qty if price else 0
        day_cell = store_by_day.setdefault(dt, {"date": dt, "order_units": 0, "gmv": 0.0})
        day_cell["order_units"] += qty
        day_cell["gmv"] += price * qty if price else 0
    return list(by_day_nm.values()), list(store_by_day.values())


def _product_context(wbcards: list[dict[str, Any]]) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for card in wbcards:
        raw_json: dict[str, Any] = {}
        try:
            raw_json = json.loads(card.get("json") or "{}")
        except json.JSONDecodeError:
            pass
        rows.append(
            {
                "nmid": card.get("nmid"),
                "title": card.get("name") or raw_json.get("name"),
                "category_id": card.get("wb_category_id"),
                "brand": raw_json.get("brand"),
                "price": raw_json.get("salePriceU") or raw_json.get("priceU"),
                "discount": raw_json.get("discount"),
                "stock": raw_json.get("quantity") or raw_json.get("stocks"),
                "rating": raw_json.get("rating"),
                "source": "postgresql.wbcard.json",
            }
        )
    return rows


def _build_current_state_v0(
    settings: list[dict[str, Any]],
    keywords: list[dict[str, Any]],
    adv_daily: list[dict[str, Any]],
    nm_daily: list[dict[str, Any]],
    orders_nm: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    """Tidy long format snapshot."""
    observed = datetime.now().isoformat()
    rows: list[dict[str, Any]] = []
    for s in settings:
        for field in SETTING_FIELDS:
            if field in s and s[field] not in (None, ""):
                rows.append(
                    {
                        "observed_at": observed,
                        "object_type": "adv_setting",
                        "object_id": s.get("id"),
                        "parent_id": s.get("wb_cabinet_id"),
                        "metric": field,
                        "value": s.get(field),
                        "unit": "",
                        "period_from": "",
                        "period_to": "",
                        "period_state": "CURRENT",
                        "source": "postgresql.advsetting",
                        "direct_assoc": "",
                        "calculation_version": "baseline_v0",
                        "notes": "",
                    }
                )
    for k in keywords:
        rows.append(
            {
                "observed_at": observed,
                "object_type": "keyword",
                "object_id": k.get("id"),
                "parent_id": k.get("adv_setting_id"),
                "metric": "hard_status",
                "value": k.get("hard_status"),
                "unit": "",
                "period_from": "",
                "period_to": "",
                "period_state": "CURRENT",
                "source": "postgresql.keywordsetting",
                "direct_assoc": "",
                "calculation_version": "baseline_v0",
                "notes": k.get("text"),
            }
        )
    for m in adv_daily:
        for metric in ("views", "clicks", "orders", "spend", "sum_price"):
            rows.append(
                {
                    "observed_at": observed,
                    "object_type": "campaign_day",
                    "object_id": m.get("adv_id"),
                    "parent_id": m.get("date"),
                    "metric": metric,
                    "value": m.get(metric),
                    "unit": "rub" if metric in ("spend", "sum_price") else "count",
                    "period_from": m.get("date"),
                    "period_to": m.get("date"),
                    "period_state": m.get("period_state"),
                    "source": "wb.fullstats.v3",
                    "direct_assoc": "",
                    "calculation_version": "baseline_v0",
                    "notes": "",
                }
            )
    return rows


def run_collect(output_dir: Path) -> dict[str, Any]:
    """Выполнить полный baseline collect и создать ZIP."""
    if output_dir.exists():
        shutil.rmtree(output_dir)
    sql_dir = output_dir / "sql"
    raw_dir = output_dir / "raw"
    sql_dir.mkdir(parents=True)
    raw_dir.mkdir(parents=True)
    _bootstrap_cluster_infra()
    gaps: list[str] = []

    meta, settings, cabinets, campaign_ids, nmids = _load_pg_cabinet_and_settings(output_dir, sql_dir)
    setting_ids = {int(s["id"]) for s in settings if s.get("id")}
    keywords = _load_keywords(output_dir, sql_dir, setting_ids)
    wbcards = _load_wbcards(output_dir, sql_dir, nmids)

    wb_status, config_rows, raw_fullstats, orders_raw, api_ids, promoted = asyncio.run(
        _wb_campaign_status_and_api(settings)
    )
    _write_jsonl(raw_dir / "fullstats_v3_raw.jsonl", raw_fullstats)
    _write_jsonl(raw_dir / "campaigns_v2.jsonl", config_rows)
    _write_jsonl(raw_dir / "supplier_orders_raw.jsonl", orders_raw)

    identity = _build_identity_map(settings, wb_status)
    adv_daily, nm_daily, assoc_check = _normalize_fullstats(raw_fullstats)
    bid_rows, bid_cov = _export_bid_history(output_dir, sql_dir, campaign_ids)
    setting_events, setting_gaps = _probe_setting_history(output_dir, sql_dir, campaign_ids, nmids)
    gaps.extend(setting_gaps)
    orders_nm, store_daily = _orders_nm_daily(orders_raw)
    product_current = _product_context(wbcards)

    setting_cols = [c for c in SETTING_FIELDS if any(c in s for s in settings)]
    for s in settings:
        for c in SETTING_FIELDS:
            if c not in s:
                s[c] = ""
    _write_csv(output_dir / "01_IDENTITY_CAMPAIGN_MAP.csv", identity, list(identity[0].keys()) if identity else [])
    _write_csv(output_dir / "02_CAMPAIGN_SETTINGS_CURRENT.csv", settings, setting_cols)
    kw_cols = [
        "id", "adv_setting_id", "text", "hard_status", "strategy_mode",
        "target_place", "relevant", "predict_ctr",
    ]
    adv_map = {int(s["id"]): s for s in settings if s.get("id")}
    kw_out: list[dict[str, Any]] = []
    for k in keywords:
        adv_s = adv_map.get(int(k.get("adv_setting_id") or 0), {})
        kw_out.append(
            {
                **k,
                "adv_id": adv_s.get("adv_id"),
            }
        )
    _write_csv(output_dir / "03_KEYWORD_STATE_CURRENT.csv", kw_out, kw_cols + ["adv_id"])
    bid_cols = [
        "adv_id", "nmid", "norm_query", "final_bid", "decision_source",
        "stats_max_timestamp", "decision_time", "version", "cpm_curr", "pos_final",
    ]
    _write_csv(output_dir / "04_BID_DECISION_HISTORY.csv", bid_rows, bid_cols)
    _write_csv(
        output_dir / "05_SETTING_EVENT_HISTORY.csv",
        setting_events,
        ["source", "rows_in_period", "fields", "confidence"] if setting_events else ["note"],
    )
    _write_csv(
        output_dir / "06_ADV_DAILY.csv",
        adv_daily,
        ["adv_id", "date", "views", "clicks", "ctr", "cpc", "atbs", "orders", "shks", "canceled", "spend", "sum_price", "period_state"],
    )
    _write_csv(
        output_dir / "07_ADV_NM_DAILY.csv",
        nm_daily,
        ["adv_id", "date", "app_type", "nm_id", "views", "clicks", "ctr", "cpc", "atbs", "orders", "shks", "canceled", "spend", "sum_price", "period_state"],
    )
    _write_jsonl(output_dir / "08_STORE_ORDERS_RAW.jsonl", [o for o in orders_raw if not o.get("_error")])
    _write_csv(output_dir / "09_STORE_NM_DAILY.csv", orders_nm, ["date", "nm_id", "order_units", "gmv"])
    _write_csv(
        output_dir / "10_PRODUCT_CONTEXT_CURRENT.csv",
        product_current,
        ["nmid", "title", "category_id", "brand", "price", "discount", "stock", "rating", "source"],
    )
    hist_gap = "GAP — no durable price/stock history table found in audited CH/PG for baseline period"
    gaps.append(hist_gap)
    _write_csv(output_dir / "11_PRODUCT_CONTEXT_HISTORY.csv", [{"gap": hist_gap}], ["gap"])
    _write_csv(
        output_dir / "12_CURRENT_STATE_V0.csv",
        _build_current_state_v0(settings, keywords, adv_daily, nm_daily, orders_nm),
        [
            "observed_at", "object_type", "object_id", "parent_id", "metric", "value",
            "unit", "period_from", "period_to", "period_state", "source",
            "direct_assoc", "calculation_version", "notes",
        ],
    )
    _write_csv(
        output_dir / "13_INTERVENTION_LEDGER_SEED.csv",
        [],
        ["event_at", "object_type", "object_id", "event_type", "field", "before_value", "after_value", "actor_or_source", "source", "confidence", "notes"],
    )

    primary_days = {d.isoformat() for d in _date_range(PRIMARY_FROM, PRIMARY_TO)}
    primary_cov = sorted({r["date"] for r in adv_daily if r.get("period_state") == "PRIMARY_CLOSED"})
    primary_missing = sorted(primary_days - set(primary_cov))

    dq_lines = [
        "# Data Quality and Gaps — A1 Baseline V0",
        "",
        f"- shop_id verified: `{SHOP_ID}`",
        f"- wb_cabinet_id: `{meta.get('wb_cabinet_id')}`",
        f"- campaigns (PG advsetting): `{len(settings)}`",
        f"- campaign_ids (adv + search): `{len(campaign_ids)}`",
        f"- nmids: `{len(nmids)}`",
        f"- WB API campaigns discovered: `{len(api_ids)}`",
        "",
        "## Coverage",
        f"- PRIMARY_BASELINE days covered: `{len(primary_cov)}/{len(primary_days)}`",
        f"- PRIMARY missing days: `{primary_missing}`",
        f"- bid_decision_log: `{bid_cov}`",
        f"- fullstats days: `{sorted({r['date'] for r in adv_daily})}`",
        f"- orders raw records: `{len([o for o in orders_raw if not o.get('_error')])}`",
        "",
        "## Associative cart split",
        f"- `{assoc_check}`",
        "",
        "## Gaps",
    ]
    for g in gaps:
        dq_lines.append(f"- {g}")
    (output_dir / "14_DATA_QUALITY_AND_GAPS.md").write_text("\n".join(dq_lines) + "\n", encoding="utf-8")

    summary = [
        "# Human Summary — A1 Baseline V0",
        "",
        f"Store **А1** (`{SHOP_ID}`), wb_cabinet_id **{meta.get('wb_cabinet_id')}**.",
        f"Collected **{len(settings)}** AdvSetting rows, **{len(keywords)}** keywords, "
        f"**{len(campaign_ids)}** WB campaign IDs, **{len(nmids)}** nmIDs.",
        "",
        f"Primary baseline window {PRIMARY_FROM}..{PRIMARY_TO}: "
        f"{len(primary_cov)} closed days with adv daily stats.",
        f"Open day {OPEN_DAY} kept separate (period_state=OPEN).",
        "",
        "Setting change history (max CPO, strategy, bot_active, etc.) is mostly **GAP** — "
        "only auto_shelf_bid_intervals probed; intervention ledger seed empty by design.",
        "",
        "Package is sufficient for Migration Chat to form a **first hypothesis** and "
        "record a **starting intervention** if gaps are acknowledged; not sufficient for "
        "causal attribution without WB associative semantics reconciliation.",
    ]
    (output_dir / "15_HUMAN_SUMMARY.md").write_text("\n".join(summary) + "\n", encoding="utf-8")

    manifest = {
        "artifact": "a1_baseline_v0",
        "created_at": datetime.now().isoformat(),
        "shop_id": SHOP_ID,
        "wb_cabinet_id": meta.get("wb_cabinet_id"),
        "timezone": TZ,
        "periods": {
            "primary_baseline": [PRIMARY_FROM.isoformat(), PRIMARY_TO.isoformat()],
            "context": [CONTEXT_FROM.isoformat(), CONTEXT_TO.isoformat()],
            "open_day": OPEN_DAY.isoformat(),
            "fullstats": [FULLSTATS_FROM.isoformat(), FULLSTATS_TO.isoformat()],
        },
        "counts": {
            "campaigns": len(settings),
            "nmids": len(nmids),
            "keywords": len(keywords),
            "bid_decision_rows": len(bid_rows),
            "adv_daily_rows": len(adv_daily),
            "nm_daily_rows": len(nm_daily),
        },
        "associative_cart_split": assoc_check.get("direct_vs_associative_split"),
        "gaps": gaps,
    }
    (output_dir / "00_MANIFEST.json").write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")

    findings = evidence.secret_scan(output_dir)
    if findings:
        raise SystemExit(f"Secret scan failed: {findings[:5]}")

    archive, digest = evidence.archive_directory(output_dir)
    return {
        "EXECUTION_STATUS": "COMPLETE",
        "SHOP_ID_VERIFIED": SHOP_ID,
        "WB_CABINET_ID": meta.get("wb_cabinet_id"),
        "CAMPAIGNS_FOUND": len(settings),
        "NMIDS_FOUND": len(nmids),
        "PRIMARY_BASELINE_COVERAGE": f"{len(primary_cov)}/{len(primary_days)}",
        "BOT_HISTORY_COVERAGE": bid_cov,
        "FULLSTATS_COVERAGE": sorted({r["date"] for r in adv_daily}),
        "ORDERS_COVERAGE": len([o for o in orders_raw if not o.get("_error")]),
        "ASSOCIATIVE_CART_SPLIT": assoc_check.get("direct_vs_associative_split"),
        "CRITICAL_GAPS": gaps,
        "ZIP_ABSOLUTE_PATH": str(archive.resolve()),
        "ZIP_SHA256": digest,
    }


def _date_range(start: date, end: date) -> list[date]:
    result: list[date] = []
    current = start
    while current <= end:
        result.append(current)
        current += timedelta(days=1)
    return result


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="A1 baseline V0 READ_ONLY collector.")
    parser.add_argument("--output-dir", default=".tmp/a1_baseline_v0")
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    out = Path(args.output_dir).resolve()
    result = run_collect(out)
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
