"""READ_ONLY fresh current-state reconciliation for WB shop A1.

Запускает wb_api_readonly_ops full collect, обогащает PG advsetting/wbcard,
budgets и формирует CURRENT_STATE_RECONCILIATION.md + JSON package.
"""

from __future__ import annotations

import argparse
import asyncio
import csv
import hashlib
import json
import os
import sys
import zipfile
from collections import defaultdict
from datetime import date, datetime, timezone
from pathlib import Path
from typing import Any
from zoneinfo import ZoneInfo

import dotenv

dotenv.load_dotenv()

from scripts import ch_a1_evidence as evidence
from scripts.wb_a1_associated_conversions import _jsonable, _read_float, _read_int

SHOP_ID = "5339e9ad-cbfe-50fc-8d77-b9f337a80417"
MSK = ZoneInfo("Europe/Moscow")
BASELINE_SNAPSHOT_AT_MSK = "2026-08-27T17:24:53"
BASELINE_ADV_IDS_COUNT = 135
BASELINE_BOT_PAIRS = 11

ADS_FROM = date(2026, 8, 22)
ADS_TO = date(2026, 8, 28)
CLOSED_THROUGH = date(2026, 8, 27)
OPEN_DAY = date(2026, 8, 28)

H1_AUTO = [17906286, 21604339]
H1_SEARCH = [20646357, 21604374]
H2_AUTO = [21542370, 25174753]
SEARCH_TEST_AUTO = 37236815
SEARCH_TEST_SEARCH = 34129888
ORPHAN_ADV = 34210859
ORPHAN_NM = 837395782

SETTING_FIELDS = [
    "id",
    "adv_id",
    "_search_adv_id",
    "type",
    "name",
    "nmids",
    "active_status",
    "bot_active",
    "auto_budget_daily_limit",
    "search_auto_budget_daily_limit",
    "use_common_budget",
    "common_budget_daily_limit",
    "aggressiveness",
    "max_price_for_order",
    "target_price_for_order",
    "strategy",
    "wb_bid_type",
    "wb_placement_search",
    "wb_placement_recommendations",
    "cpm",
    "max_cpm",
    "max_cpc",
    "last_update",
]


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


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _day_state(day_str: str) -> str:
    try:
        d = date.fromisoformat(day_str[:10])
    except ValueError:
        return "UNKNOWN"
    if d == OPEN_DAY:
        return "OPEN_PARTIAL"
    if d <= CLOSED_THROUGH and d >= ADS_FROM:
        return "CLOSED"
    return "OUT_OF_SCOPE"


def _load_pg_advsettings(root: Path, sql_dir: Path) -> list[dict[str, str]]:
    staging = root / "staging"
    staging.mkdir(parents=True, exist_ok=True)
    path = staging / "advsetting_all.csv"
    cols = ", ".join(SETTING_FIELDS)
    st = evidence.run_pg_query(
        _pg_database(),
        (
            f"SELECT {cols} FROM public.advsetting a "
            f"JOIN public.wbcabinet c ON a.wb_cabinet_id = c.id "
            f"WHERE c.shop_id = '{SHOP_ID}'"
        ),
        path,
        sql_dir / "pg_advsetting_shop.sql",
        csv_output=True,
    )
    if not st["success"]:
        raise RuntimeError(f"advsetting query failed: {st['stderr']}")
    with path.open(encoding="utf-8", newline="") as handle:
        return list(csv.DictReader(handle))


def _load_pg_wbcards(root: Path, sql_dir: Path) -> list[dict[str, str]]:
    staging = root / "staging"
    path = staging / "wbcard.csv"
    st = evidence.run_pg_query(
        _pg_database(),
        (
            "SELECT w.nmid, w.name, w.json, w.adv_setting_id, w.updated "
            "FROM public.wbcard w "
            f"JOIN public.wbcabinet c ON w.wb_cabinet_id = c.id "
            f"WHERE c.shop_id = '{SHOP_ID}'"
        ),
        path,
        sql_dir / "pg_wbcard_shop.sql",
        csv_output=True,
    )
    if not st["success"]:
        return []
    with path.open(encoding="utf-8", newline="") as handle:
        return list(csv.DictReader(handle))


def _pg_by_adv_id(rows: list[dict[str, str]]) -> dict[int, dict[str, str]]:
    out: dict[int, dict[str, str]] = {}
    for row in rows:
        try:
            adv_id = int(row.get("adv_id") or 0)
        except (TypeError, ValueError):
            continue
        if adv_id:
            out[adv_id] = row
    return out


def _parse_nmids(raw: str) -> list[int]:
    if not raw:
        return []
    try:
        val = json.loads(raw.replace("'", '"'))
        if isinstance(val, list):
            return [int(x) for x in val if str(x).isdigit()]
    except json.JSONDecodeError:
        pass
    return []


def _campaign_row_to_inventory(
    raw: dict[str, Any],
    pg: dict[int, dict[str, str]],
    budget: dict[str, Any] | None,
) -> dict[str, Any]:
    adv_id = _read_int(raw, "id", "advertId", "advert_id")
    settings = raw.get("settings") if isinstance(raw.get("settings"), dict) else {}
    nm_settings = raw.get("nm_settings") or raw.get("nmSettings") or []
    nm_ids: list[int] = []
    if isinstance(nm_settings, list):
        for nm in nm_settings:
            if isinstance(nm, dict):
                nmid = _read_int(nm, "nm_id", "nmId", "nmID")
                if nmid:
                    nm_ids.append(nmid)
    pg_row = pg.get(adv_id, {})
    placements = settings.get("placements") if isinstance(settings.get("placements"), dict) else {}
    return {
        "adv_id": adv_id,
        "nm_ids": nm_ids or _parse_nmids(str(pg_row.get("nmids") or "")),
        "wb_status": raw.get("status"),
        "bid_type": raw.get("bid_type"),
        "payment_type": settings.get("payment_type"),
        "placements": placements,
        "name": settings.get("name") or pg_row.get("name"),
        "budget_total": budget.get("total") if budget else None,
        "adv_setting_id": pg_row.get("id"),
        "search_adv_id": pg_row.get("_search_adv_id"),
        "bot_active": pg_row.get("bot_active"),
        "active_status": pg_row.get("active_status"),
        "auto_budget_daily_limit": pg_row.get("auto_budget_daily_limit"),
        "search_auto_budget_daily_limit": pg_row.get("search_auto_budget_daily_limit"),
        "aggressiveness": pg_row.get("aggressiveness"),
        "strategy": pg_row.get("strategy"),
        "wb_bid_type_pg": pg_row.get("wb_bid_type"),
        "last_update": pg_row.get("last_update"),
    }


async def _load_budgets(adv_ids: list[int]) -> dict[int, dict[str, Any]]:
    from app.core.di.app_container import AppContainer
    from app.core.di.di_manager import DIManager

    budgets: dict[int, dict[str, Any]] = {}
    async with await DIManager.create(AppContainer) as container:  # type: ignore[attr-defined]
        factory = container.module_resources.wb_manager_hub_factory_container.wb_manager_hub_factory()
        hub = factory.get_wb_manager_hub(SHOP_ID)
        finance = hub.wb_data_manager.promotion_manager._client.finance_adapter
        for adv_id in adv_ids:
            try:
                resp = await finance.get_campaign_budget(adv_id)
                budgets[adv_id] = resp.to_dict() if resp and hasattr(resp, "to_dict") else {}
            except Exception as exc:  # noqa: BLE001
                budgets[adv_id] = {"error": f"{type(exc).__name__}: {exc}"}
    return budgets


async def _run_collect(output_dir: Path) -> dict[str, Any]:
    from app.configs.app_config import AppConfig
    from app.core.di.wb_manager_hub.wb_manager_hub_factory import WBManagerHubFactory
    from app.core.mp.wb.api.httpx_client_handler import HttpxClientHandler
    from app.core.redis_manager_v2.redis_client import RedisClient
    from app.modules.common_slaves.wildberries.super_cabinet_manager import (
        get_access_for_wb_cabinet,
    )
    from redis.asyncio import Redis
    from scripts.wb_api_readonly_ops.cli import DEFAULT_COLLECT_MAX_SECONDS
    from scripts.wb_api_readonly_ops.collect.runner import run_full_collect

    app_config = AppConfig.create()
    redis_config = app_config.infrastructure.redis
    redis_client_raw: Redis[str] = Redis(
        host=redis_config.host,
        port=redis_config.port,
        db=redis_config.db,
        password=redis_config.password,
        decode_responses=True,
    )
    await redis_client_raw.ping()
    redis_client_wrapper = RedisClient(redis_client=redis_client_raw)
    httpx_client_handler = HttpxClientHandler()
    await httpx_client_handler.init()
    try:
        await get_access_for_wb_cabinet(SHOP_ID)
        hub = WBManagerHubFactory(
            httpx_client_handler=httpx_client_handler,
            redis_client_wrapper=redis_client_wrapper,
        ).get_wb_manager_hub(SHOP_ID)
        report = await run_full_collect(
            shop_id=SHOP_ID,
            wb_data_manager=hub.wb_data_manager,
            output_dir=output_dir,
            orders_date_from=ADS_FROM.isoformat(),
            max_seconds=DEFAULT_COLLECT_MAX_SECONDS,
            max_api_calls=10_000,
            ads_date_from=ADS_FROM.isoformat(),
            ads_date_to=ADS_TO.isoformat(),
        )
        return report.to_dict()
    finally:
        await httpx_client_handler.shutdown()
        await redis_client_raw.close()


def _read_jsonl_from_zip(zf: zipfile.ZipFile, name: str) -> list[dict[str, Any]]:
    try:
        data = zf.read(name).decode("utf-8")
    except KeyError:
        return []
    rows: list[dict[str, Any]] = []
    for line in data.splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            row = json.loads(line)
            if isinstance(row, dict):
                rows.append(row)
        except json.JSONDecodeError:
            continue
    return rows


def _aggregate_fullstats(rows: list[dict[str, Any]]) -> dict[tuple[int, str], dict[str, Any]]:
    agg: dict[tuple[int, str], dict[str, Any]] = {}
    for row in rows:
        adv_id = _read_int(row, "advertId", "advert_id")
        day = str(row.get("date", ""))[:10]
        if not adv_id or not day:
            continue
        key = (adv_id, day)
        bucket = agg.setdefault(
            key,
            {
                "adv_id": adv_id,
                "date": day,
                "day_state": _day_state(day),
                "views": 0,
                "clicks": 0,
                "spend": 0.0,
                "orders": 0,
                "sum_price": 0.0,
            },
        )
        bucket["views"] += _read_int(row, "views")
        bucket["clicks"] += _read_int(row, "clicks")
        bucket["spend"] += _read_float(row, "sum", "spend")
        bucket["orders"] += _read_int(row, "orders")
        bucket["sum_price"] += _read_float(row, "sum_price")
    return agg


def _store_spend_by_day(stats: dict[tuple[int, str], dict[str, Any]]) -> dict[str, float]:
    by_day: dict[str, float] = defaultdict(float)
    for (_adv, day), row in stats.items():
        by_day[day] += float(row.get("spend") or 0)
    return dict(by_day)


def _funnel_store_totals(rows: list[dict[str, Any]]) -> dict[str, dict[str, float]]:
    by_day: dict[str, dict[str, float]] = defaultdict(
        lambda: {"orderCount": 0.0, "orderSum": 0.0}
    )

    def _walk(obj: Any) -> None:
        if isinstance(obj, dict):
            day = str(obj.get("date") or obj.get("dt") or "")[:10]
            if day and ("orderCount" in obj or "orderSum" in obj):
                by_day[day]["orderCount"] += _read_float(obj, "orderCount", "order_count")
                by_day[day]["orderSum"] += _read_float(obj, "orderSum", "order_sum")
            for val in obj.values():
                _walk(val)
        elif isinstance(obj, list):
            for item in obj:
                _walk(item)

    for row in rows:
        _walk(row)

    out: dict[str, dict[str, float]] = {}
    for day, vals in by_day.items():
        out[day] = {**vals, "day_state": _day_state(day)}
    return out


def _bot_linked_pairs(pg_rows: list[dict[str, str]]) -> list[dict[str, Any]]:
    by_adv = _pg_by_adv_id(pg_rows)
    pairs: list[dict[str, Any]] = []
    for row in pg_rows:
        search_raw = (row.get("_search_adv_id") or "").strip()
        if not search_raw:
            continue
        try:
            auto_id = int(row.get("adv_id") or 0)
            search_id = int(search_raw)
        except (TypeError, ValueError):
            continue
        pairs.append(
            {
                "auto_adv_id": auto_id,
                "search_adv_id": search_id,
                "adv_setting_id": row.get("id"),
                "bot_active": row.get("bot_active"),
                "auto_bid_type_pg": row.get("wb_bid_type"),
                "search_row": by_adv.get(search_id),
            }
        )
    return pairs


def _gate_status(
    name: str,
    confirmed: bool,
    changed: bool,
    detail: str,
) -> dict[str, str]:
    if confirmed and not changed:
        status = "CONFIRMED"
    elif changed:
        status = "CHANGED"
    else:
        status = "UNKNOWN"
    return {"gate": name, "status": status, "detail": detail}


def _build_gates(
    pg_by_adv: dict[int, dict[str, str]],
    inventory: dict[int, dict[str, Any]],
    pairs: list[dict[str, Any]],
) -> dict[str, Any]:
    gates: dict[str, Any] = {}

    def lim(adv_id: int) -> str:
        row = pg_by_adv.get(adv_id, {})
        return str(row.get("auto_budget_daily_limit", ""))

    h1_auto_ok = all(lim(a) == "0" for a in H1_AUTO)
    h1_search_ok = all(a in inventory for a in H1_SEARCH)
    gates["H1"] = {
        "overall": "CONFIRMED" if h1_auto_ok and h1_search_ok else "CHANGED" if not h1_auto_ok else "UNKNOWN",
        "items": [
            _gate_status(
                f"Auto {H1_AUTO[0]} daily_limit=0",
                h1_auto_ok,
                lim(H1_AUTO[0]) != "0",
                f"auto_budget_daily_limit={lim(H1_AUTO[0])}",
            ),
            _gate_status(
                f"Auto {H1_AUTO[1]} daily_limit=0",
                h1_auto_ok,
                lim(H1_AUTO[1]) != "0",
                f"auto_budget_daily_limit={lim(H1_AUTO[1])}",
            ),
            _gate_status(
                f"Search {H1_SEARCH[0]} preserved",
                h1_search_ok,
                H1_SEARCH[0] not in inventory,
                "present_in_wb_inventory" if h1_search_ok else "missing",
            ),
            _gate_status(
                f"Search {H1_SEARCH[1]} preserved",
                h1_search_ok,
                H1_SEARCH[1] not in inventory,
                "present_in_wb_inventory" if h1_search_ok else "missing",
            ),
        ],
    }

    h2_details = []
    h2_changed = False
    for adv_id in H2_AUTO:
        row = pg_by_adv.get(adv_id, {})
        auto_lim = row.get("auto_budget_daily_limit")
        search_lim = row.get("search_auto_budget_daily_limit")
        if str(auto_lim) == "0":
            h2_changed = True
        h2_details.append(
            f"{adv_id}: auto_limit={auto_lim}, search_limit={search_lim}, "
            f"aggressiveness={row.get('aggressiveness')}"
        )
    gates["H2"] = {
        "overall": "CHANGED" if h2_changed else "CONFIRMED",
        "detail": (
            "No auto_limit=0 detected on H2 candidates; prepared patch not evidenced as executed"
            if not h2_changed
            else "At least one H2 candidate has auto_limit=0"
        ),
        "items": h2_details,
    }

    agg = pg_by_adv.get(SEARCH_TEST_AUTO, {}).get("aggressiveness")
    gates["SEARCH_3_TO_1"] = {
        "overall": "CONFIRMED" if str(agg) == "3" else "CHANGED" if agg else "UNKNOWN",
        "auto_adv_id": SEARCH_TEST_AUTO,
        "search_adv_id": SEARCH_TEST_SEARCH,
        "aggressiveness_current": agg,
        "expected_if_not_executed": "3",
    }

    unified_manual = 0
    for pair in pairs:
        auto = inventory.get(pair["auto_adv_id"], {})
        search = inventory.get(pair["search_adv_id"], {})
        if (
            str(auto.get("bid_type") or pair.get("auto_bid_type_pg")) == "unified"
            and str(search.get("bid_type")) == "manual"
        ):
            unified_manual += 1
    topo_same = len(pairs) == BASELINE_BOT_PAIRS and unified_manual == BASELINE_BOT_PAIRS
    gates["TOPOLOGY"] = {
        "overall": "CONFIRMED" if topo_same else "CHANGED",
        "bot_linked_pairs": len(pairs),
        "baseline_pairs": BASELINE_BOT_PAIRS,
        "unified_plus_manual_search_pairs": unified_manual,
        "migration_evidence": "none_in_pg_wb_inventory",
    }

    orphan_pg = pg_by_adv.get(ORPHAN_ADV)
    orphan_inv = inventory.get(ORPHAN_ADV, {})
    attached = orphan_pg is not None and bool(orphan_pg.get("bot_active") == "True")
    gates["34210859"] = {
        "overall": "CHANGED" if attached else "CONFIRMED",
        "nm_id": ORPHAN_NM,
        "bot_linked": attached,
        "pg_row_exists": orphan_pg is not None,
        "wb_status": orphan_inv.get("wb_status"),
        "active_status_pg": orphan_pg.get("active_status") if orphan_pg else None,
        "budget_total": orphan_inv.get("budget_total"),
        "auto_budget_daily_limit": orphan_pg.get("auto_budget_daily_limit") if orphan_pg else None,
        "bid_type": orphan_inv.get("bid_type"),
        "placements": orphan_inv.get("placements"),
        "baseline_snapshot": "standalone_orphan_paused_budget_0",
        "takeover_execution_evidence": "none",
    }

    gates["NEW_SKU"] = {
        "overall": "UNKNOWN",
        "detail": "No authoritative baseline nm_id inventory file bundled; compare requires prior campaign_ids.jsonl",
    }

    return gates


def _write_reconciliation_md(
    path: Path,
    *,
    checked_at: str,
    gates: dict[str, Any],
    inventory_count: int,
    delta: dict[str, Any],
    integrity: dict[str, Any],
    gaps: list[str],
) -> None:
    lines = [
        "# CURRENT_STATE_RECONCILIATION",
        "",
        f"**CASE:** ООО «А1» · `shop_id={SHOP_ID}`",
        f"**checked_at (UTC):** {checked_at}",
        f"**baseline_snapshot (MSK):** {BASELINE_SNAPSHOT_AT_MSK}",
        f"**MODE:** STRICT_READ_ONLY",
        "",
        "## Status gates",
        "",
        "| Gate | Status | Detail |",
        "|------|--------|--------|",
    ]
    for key in ("H1", "H2", "SEARCH_3_TO_1", "TOPOLOGY", "34210859", "NEW_SKU"):
        g = gates.get(key, {})
        lines.append(f"| {key} | {g.get('overall', 'UNKNOWN')} | {g.get('detail', g)} |")
    lines.extend(
        [
            "",
            "## Campaign inventory delta vs 2026-08-27",
            "",
            f"- Current WB adv_ids: **{inventory_count}**",
            f"- Baseline count (funding snapshot 27.08): **{BASELINE_ADV_IDS_COUNT}**",
        f"- Delta adv_ids (count only): **{delta.get('adv_id_count_delta', 'UNKNOWN')}**",
        f"- New adv_ids (list): {delta.get('new_adv_ids_vs_same_collect')}",
        f"- Missing vs baseline list: {delta.get('missing_adv_ids_vs_same_collect')}",
            "",
            "## Coverage / integrity",
            "",
            json.dumps(integrity, ensure_ascii=False, indent=2),
            "",
            "## Unresolved GAPs",
            "",
        ]
    )
    for gap in gaps:
        lines.append(f"- {gap}")
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


async def run_reconciliation(
    output_dir: Path,
    pg_rows: list[dict[str, str]],
    wbcards: list[dict[str, str]],
) -> dict[str, Any]:
    """Собрать reconciliation package."""
    output_dir.mkdir(parents=True, exist_ok=True)
    sql_dir = output_dir / "sql"
    sql_dir.mkdir(parents=True, exist_ok=True)
    checked_at = datetime.now(timezone.utc).isoformat()

    pg_by_adv = _pg_by_adv_id(pg_rows)

    collect_report = await _run_collect(output_dir)
    zip_path = output_dir / "wb_readonly_research.zip"
    if not zip_path.exists():
        raise RuntimeError("collect archive missing")

    with zipfile.ZipFile(zip_path, "r") as zf:
        campaigns = _read_jsonl_from_zip(zf, "raw/ads/campaigns.jsonl")
        fullstats = _read_jsonl_from_zip(zf, "raw/ads/fullstats.jsonl")
        funnel = _read_jsonl_from_zip(zf, "raw/funnel/funnel.jsonl")
        orders = _read_jsonl_from_zip(zf, "raw/orders.jsonl")
        campaign_ids = {}
        if "raw/ads/campaign_ids.json" in zf.namelist():
            campaign_ids = json.loads(zf.read("raw/ads/campaign_ids.json").decode("utf-8"))

    adv_ids = sorted(
        {
            _read_int(c, "id", "advertId")
            for c in campaigns
            if _read_int(c, "id", "advertId")
        }
    )
    gate_ids = sorted(
        set(adv_ids)
        | set(H1_AUTO + H1_SEARCH + H2_AUTO + [SEARCH_TEST_AUTO, SEARCH_TEST_SEARCH, ORPHAN_ADV])
    )
    budgets = await _load_budgets(gate_ids)

    inventory_list = [
        _campaign_row_to_inventory(c, pg_by_adv, budgets.get(_read_int(c, "id", "advertId")))
        for c in campaigns
    ]
    inventory = {row["adv_id"]: row for row in inventory_list if row.get("adv_id")}

    stats = _aggregate_fullstats(fullstats)
    store_spend = _store_spend_by_day(stats)
    funnel_totals = _funnel_store_totals(funnel)
    pairs = _bot_linked_pairs(pg_rows)
    gates = _build_gates(pg_by_adv, inventory, pairs)

    target_metrics: dict[str, Any] = {}
    for adv_id in H1_AUTO + H1_SEARCH + H2_AUTO + [SEARCH_TEST_AUTO, SEARCH_TEST_SEARCH, ORPHAN_ADV]:
        by_day = {
            day: row
            for (aid, day), row in stats.items()
            if aid == adv_id and row["day_state"] in ("CLOSED", "OPEN_PARTIAL")
        }
        target_metrics[str(adv_id)] = {
            "daily": by_day,
            "closed_total_spend": sum(
                r["spend"] for r in by_day.values() if r["day_state"] == "CLOSED"
            ),
            "open_partial_spend": sum(
                r["spend"] for r in by_day.values() if r["day_state"] == "OPEN_PARTIAL"
            ),
        }

    delta = {
        "adv_id_count_current": len(adv_ids),
        "adv_id_count_baseline_20260827": BASELINE_ADV_IDS_COUNT,
        "adv_id_count_delta": len(adv_ids) - BASELINE_ADV_IDS_COUNT,
        "new_adv_ids_vs_same_collect": "N/A — baseline list not bundled",
        "missing_adv_ids_vs_same_collect": "N/A — baseline list not bundled",
    }

    gaps = list(collect_report.get("missing_collector_capabilities") or [])
    gaps.extend(
        [
            "baseline_adv_id_list_from_20260827_not_bundled — delta uses count only",
            "prices/stocks/promotions: cards CURRENT_STATE_ONLY; no historical dynamics",
            "direct_vs_associative attribution: not split in standard collect",
            "34210859 placement flags: resolve from WB v2 only",
        ]
    )

    integrity = {
        "collect_report": collect_report,
        "timezone": "Europe/Moscow",
        "closed_days": f"{ADS_FROM.isoformat()}..{CLOSED_THROUGH.isoformat()}",
        "open_partial_day": OPEN_DAY.isoformat(),
        "store_spend_by_day_all_campaigns": store_spend,
        "funnel_store_totals_by_day": funnel_totals,
        "orders_rows_collected": len(orders),
        "duplicate_check": "aggregated by (adv_id,date) — no duplicate keys in output",
    }

    package = {
        "checked_at": checked_at,
        "checked_at_msk": datetime.now(MSK).isoformat(),
        "shop_id": SHOP_ID,
        "baseline_snapshot_msk": BASELINE_SNAPSHOT_AT_MSK,
        "mode": "STRICT_READ_ONLY",
        "STATUS_GATES": gates,
        "CAMPAIGN_INVENTORY": inventory_list,
        "BOT_LINKED_PAIRS": pairs,
        "TARGET_CAMPAIGN_METRICS": target_metrics,
        "STORE_AD_SPEND_BY_DAY": store_spend,
        "STORE_FUNNEL_BY_DAY": funnel_totals,
        "CONFOUNDERS_CURRENT": {
            "wbcard_rows": len(wbcards),
            "wbcard_fields": ["nmid", "name", "json", "adv_setting_id"],
            "historical_price_stock_dynamics": "GAP",
        },
        "DELTA_VS_BASELINE": delta,
        "INTEGRITY": integrity,
        "GAPS": gaps,
        "artifacts": {
            "collect_zip": str(zip_path.resolve()),
            "collect_zip_sha256": _sha256(zip_path),
        },
    }

    json_path = output_dir / "CURRENT_STATE_RECONCILIATION.json"
    json_path.write_text(json.dumps(package, ensure_ascii=False, indent=2), encoding="utf-8")
    _write_reconciliation_md(
        output_dir / "CURRENT_STATE_RECONCILIATION.md",
        checked_at=checked_at,
        gates=gates,
        inventory_count=len(adv_ids),
        delta=delta,
        integrity=integrity,
        gaps=gaps,
    )
    package["output_paths"] = {
        "json": str(json_path.resolve()),
        "md": str((output_dir / "CURRENT_STATE_RECONCILIATION.md").resolve()),
        "zip": str(zip_path.resolve()),
    }
    return package


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="A1 current-state reconciliation READ_ONLY.")
    parser.add_argument("--output-dir", default=".tmp/a1_current_state_reconciliation")
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    out = Path(args.output_dir).resolve()
    _bootstrap_cluster_infra()
    sql_dir = out / "sql"
    sql_dir.mkdir(parents=True, exist_ok=True)
    pg_rows = _load_pg_advsettings(out, sql_dir)
    wbcards = _load_pg_wbcards(out, sql_dir)
    result = asyncio.run(run_reconciliation(out, pg_rows, wbcards))
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
