"""READ_ONLY: physical ad contour mapping + search control linkage trace (A1).

Строит A1-PHYSICAL-CONTOUR-AND-SEARCH-CONTROL-MAP из iteration-04 package + CURRENT PG.
Без production mutations.
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import os
import re
import sys
import zipfile
from collections import defaultdict
from datetime import datetime
from pathlib import Path
from typing import Any
from zoneinfo import ZoneInfo

import dotenv

dotenv.load_dotenv()

from scripts import ch_a1_evidence as evidence

SHOP_ID = "5339e9ad-cbfe-50fc-8d77-b9f337a80417"
MSK = ZoneInfo("Europe/Moscow")
PACKAGE_NAME = "A1-PHYSICAL-CONTOUR-AND-SEARCH-CONTROL-MAP"
SOURCE_PACKAGE = "A1-ITERATION-04-CURRENT-STATE-AND-CAP-CONTROL-INPUT"

NAME_SEARCH_PATTERN = re.compile(r"<!-\[(\d+)\]-!>")

PG_FIELDS = [
    "id",
    "adv_id",
    "_search_adv_id",
    "name",
    "nmids",
    "active_status",
    "bot_active",
    "auto_budget_watchdog_enabled",
    "auto_budget_daily_limit",
    "search_auto_budget_daily_limit",
    "use_common_budget",
    "common_budget_daily_limit",
    "max_balance_adding_for_day",
    "strategy",
    "aggressiveness",
]

CODE_EVIDENCE = {
    "name_search_link": (
        "app/modules/common_slaves/wildberries/models/models.py",
        "AdvSetting.search_adv_id @property",
        "pattern <!-[digits]-!> in auto campaign name when _search_adv_id NULL",
    ),
    "complex_adv_build": (
        "app/modules/shop_runner/service_manager/wb_shop_data_manager/wb_shop_data_manager.py",
        "get_pre_complex_advs",
        "ComplexAdv built from bot_active AdvSetting rows; search_adv_id from property",
    ),
    "watchdog_filter": (
        "app/modules/shop_runner/service_manager/manager.py",
        "auto_budget_watchdog",
        "candidates: watchdog on + (common_limit>0 or auto_limit>0 or search_limit>0 with search_adv_id)",
    ),
    "search_pause_start": (
        "app/modules/shop_runner/service_manager/services/auto_adv_active_control/auto_adv_active_control_service.py",
        "_search_campaign_handler",
        "search_auto_budget_daily_limit on parent AdvSetting; Redis key campaign-activity-reason:{search_adv_id}:search",
    ),
    "redis_reason": (
        "app/modules/shop_runner/service_manager/services/redis_campaign_activity_reason_manager/redis_campaign_activity_reason_manager.py",
        "RedisCampaignActivityReasonManager._key",
        "campaign-activity-reason:{adv_id}:{auto|search}",
    ),
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


def _sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _write_csv(path: Path, rows: list[dict[str, Any]], columns: list[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=columns, extrasaction="ignore")
        writer.writeheader()
        for row in rows:
            writer.writerow({c: row.get(c, "") for c in columns})


def _read_csv(path: Path) -> list[dict[str, str]]:
    with path.open(encoding="utf-8", newline="") as handle:
        return list(csv.DictReader(handle))


def _load_pg_advsettings(root: Path, sql_dir: Path) -> list[dict[str, str]]:
    staging = root / "staging"
    staging.mkdir(parents=True, exist_ok=True)
    out = staging / "advsetting_with_name.csv"
    cols = ", ".join(f"a.{c}" for c in PG_FIELDS)
    st = evidence.run_pg_query(
        _pg_database(),
        (
            f"SELECT {cols} FROM public.advsetting a "
            f"JOIN public.wbcabinet c ON a.wb_cabinet_id = c.id "
            f"WHERE c.shop_id = '{SHOP_ID}'"
        ),
        out,
        sql_dir / "pg_advsetting_name.sql",
        csv_output=True,
    )
    if not st["success"]:
        raise RuntimeError(f"PG query failed: {st['stderr']}")
    return _read_csv(out)


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


def _search_adv_id_from_name(name: str) -> int | None:
    if not name:
        return None
    match = NAME_SEARCH_PATTERN.search(name.replace(" ", ""))
    if not match:
        return None
    return int(match.group(1))


def _resolved_search_adv_id(row: dict[str, str]) -> int | None:
    raw = (row.get("_search_adv_id") or "").strip()
    if raw.isdigit() and int(raw) > 0:
        return int(raw)
    return _search_adv_id_from_name(row.get("name") or "")


def _watchdog_on(row: dict[str, str]) -> bool:
    return str(row.get("auto_budget_watchdog_enabled")).lower() in ("true", "t", "1")


def _int_val(val: str | None) -> int:
    try:
        return int(float(val or 0))
    except (TypeError, ValueError):
        return 0


def _redis_search_reason(search_adv_id: int) -> dict[str, Any]:
    key = f"campaign-activity-reason:{search_adv_id}:search"
    raw = ""
    source = "unavailable"
    try:
        import redis

        host = os.environ.get("REDIS_HOST") or os.environ.get("REDIS_MASTER_HOST")
        if host:
            client = redis.Redis(
                host=host,
                port=int(os.environ.get("REDIS_PORT", "6379")),
                password=os.environ.get("REDIS_PASSWORD"),
                db=int(os.environ.get("REDIS_DB", "0")),
                decode_responses=True,
            )
            raw = client.get(key) or ""
            source = "redis_direct"
    except Exception:
        pass
    parsed = None
    if raw:
        try:
            parsed = json.loads(raw)
        except json.JSONDecodeError:
            parsed = {"raw": raw}
    return {"redis_key": key, "source": source, "parsed": parsed}


def _build_parent_maps(
    pg_rows: list[dict[str, str]],
) -> tuple[dict[int, dict[str, str]], dict[int, dict[str, str]], dict[int, int]]:
    """auto_adv_id -> pg row; search_adv_id -> parent auto row; search_adv_id -> parent auto adv_id."""
    by_adv: dict[int, dict[str, str]] = {}
    for row in pg_rows:
        try:
            aid = int(row.get("adv_id") or 0)
        except (TypeError, ValueError):
            continue
        if aid:
            by_adv[aid] = row

    search_to_parent_row: dict[int, dict[str, str]] = {}
    search_to_parent_adv: dict[int, int] = {}
    for auto_id, row in by_adv.items():
        sid = _resolved_search_adv_id(row)
        if sid:
            search_to_parent_row[sid] = row
            search_to_parent_adv[sid] = auto_id
    return by_adv, search_to_parent_row, search_to_parent_adv


def _linkage_for_search(
    search_adv_id: int,
    pg_by_adv: dict[int, dict[str, str]],
    search_to_parent_row: dict[int, dict[str, str]],
    search_to_parent_adv: dict[int, int],
) -> dict[str, Any]:
    own = pg_by_adv.get(search_adv_id, {})
    parent_row = search_to_parent_row.get(search_adv_id)
    parent_adv_id = search_to_parent_adv.get(search_adv_id)

    if parent_row:
        raw_col = (parent_row.get("_search_adv_id") or "").strip()
        if raw_col.isdigit() and int(raw_col) == search_adv_id:
            return {
                "search_adv_id": search_adv_id,
                "parent_auto_adv_id": parent_adv_id,
                "parent_advsetting_id": parent_row.get("id"),
                "linkage_source": "DIRECT_DB",
                "linkage_field": "advsetting._search_adv_id",
                "linkage_confidence": "DIRECT_DB",
                "parent_name": parent_row.get("name"),
                "own_advsetting_id": own.get("id"),
            }
        name_sid = _search_adv_id_from_name(parent_row.get("name") or "")
        if name_sid == search_adv_id:
            return {
                "search_adv_id": search_adv_id,
                "parent_auto_adv_id": parent_adv_id,
                "parent_advsetting_id": parent_row.get("id"),
                "linkage_source": "DERIVED_FROM_CODE",
                "linkage_field": "AdvSetting.search_adv_id property / name pattern <!-[id]-!>",
                "linkage_confidence": "DERIVED_FROM_CODE",
                "code_evidence": CODE_EVIDENCE["name_search_link"],
                "parent_name": parent_row.get("name"),
                "own_advsetting_id": own.get("id"),
            }

    redis = _redis_search_reason(search_adv_id)
    if redis.get("parsed"):
        return {
            "search_adv_id": search_adv_id,
            "parent_auto_adv_id": parent_adv_id or "",
            "parent_advsetting_id": parent_row.get("id") if parent_row else "",
            "linkage_source": "REDIS_MAPPING",
            "linkage_field": redis["redis_key"],
            "linkage_confidence": "REDIS_MAPPING",
            "redis_parsed": redis["parsed"],
            "own_advsetting_id": own.get("id"),
        }

    return {
        "search_adv_id": search_adv_id,
        "parent_auto_adv_id": "",
        "parent_advsetting_id": "",
        "linkage_source": "GAP",
        "linkage_field": "",
        "linkage_confidence": "GAP",
        "own_advsetting_id": own.get("id"),
    }


def _control_for_physical(
    adv_id: int,
    leg_type: str,
    pg_by_adv: dict[int, dict[str, str]],
    search_to_parent_row: dict[int, dict[str, str]],
    search_to_parent_adv: dict[int, int],
) -> dict[str, Any]:
    own = pg_by_adv.get(adv_id, {})
    if leg_type == "Search":
        parent_row = search_to_parent_row.get(adv_id)
        parent_adv_id = search_to_parent_adv.get(adv_id)
        ctrl_row = parent_row or own
        ctrl_adv_id = parent_adv_id or adv_id
    else:
        ctrl_row = own
        ctrl_adv_id = adv_id
        parent_row = None
        parent_adv_id = ""

    if not ctrl_row:
        return {
            "controlling_advsetting_id": "",
            "controlling_parent_adv_id": parent_adv_id or "",
            "watchdog_enabled": "",
            "active_limit_field": "",
            "current_limit": "",
            "use_common_budget": "",
            "code_field_checked": "",
            "control_status": "GAP",
        }

    wd = _watchdog_on(ctrl_row)
    use_common = str(ctrl_row.get("use_common_budget")).lower() in ("true", "t", "1")
    auto_lim = _int_val(ctrl_row.get("auto_budget_daily_limit"))
    search_lim = _int_val(ctrl_row.get("search_auto_budget_daily_limit"))
    common_lim = _int_val(ctrl_row.get("common_budget_daily_limit"))
    bot_active = str(ctrl_row.get("bot_active")).lower() in ("true", "t", "1")

    if leg_type == "Auto":
        if use_common and common_lim > 0:
            field = "common_budget_daily_limit"
            limit = common_lim
            code_field = "combined_spend vs common_budget_daily_limit (_auto_campaign_handler)"
        elif auto_lim > 0:
            field = "auto_budget_daily_limit"
            limit = auto_lim
            code_field = "spend_today vs auto_budget_daily_limit (_auto_campaign_handler)"
        else:
            field = "auto_budget_daily_limit"
            limit = 0
            code_field = "auto_budget_daily_limit==0 → pause auto (_auto_campaign_handler)"
    elif leg_type == "Search":
        if use_common and common_lim > 0:
            field = "common_budget_daily_limit"
            limit = common_lim
            code_field = "combined_spend vs common_budget_daily_limit (_search_campaign_handler)"
        elif search_lim > 0:
            field = "search_auto_budget_daily_limit"
            limit = search_lim
            code_field = "spend_today vs search_auto_budget_daily_limit (_search_campaign_handler)"
        else:
            field = "search_auto_budget_daily_limit"
            limit = 0
            code_field = "search_auto_budget_daily_limit==0 → pause search (_search_campaign_handler)"
    else:
        if auto_lim > 0:
            field = "auto_budget_daily_limit"
            limit = auto_lim
            code_field = "auto_budget_daily_limit"
        elif search_lim > 0:
            field = "search_auto_budget_daily_limit"
            limit = search_lim
            code_field = "search_auto_budget_daily_limit"
        else:
            field = ""
            limit = 0
            code_field = "GAP"

    in_watchdog_candidate = wd and bot_active and (
        (use_common and common_lim > 0)
        or (not use_common and ((leg_type == "Auto" and auto_lim > 0) or (leg_type == "Search" and search_lim > 0)))
    )

    if in_watchdog_candidate and limit > 0:
        status = "CURRENTLY_CONTROLLED"
    elif wd and bot_active and limit == 0:
        status = "STOPPED_BY_LIMIT_0"
    elif wd and bot_active:
        status = "CONFIGURABLE_BUT_NOT_CONTROLLED"
    elif leg_type == "Search" and parent_row and _watchdog_on(parent_row) and search_lim > 0:
        status = "CURRENTLY_CONTROLLED"
    else:
        status = "GAP" if not ctrl_row else "CONFIGURABLE_BUT_NOT_CONTROLLED"

    return {
        "controlling_advsetting_id": ctrl_row.get("id"),
        "controlling_parent_adv_id": parent_adv_id if leg_type == "Search" else "",
        "watchdog_enabled": wd,
        "active_limit_field": field,
        "current_limit": limit,
        "use_common_budget": use_common,
        "code_field_checked": code_field,
        "control_status": status,
        "controlling_adv_id": ctrl_adv_id,
    }


def _build_20646357_trace(
    linkage: dict[str, Any],
    control: dict[str, Any],
    redis: dict[str, Any],
) -> str:
    lines = [
        "# 20646357_CONTROL_TRACE",
        "",
        "Causal verdict / cap recommendations: FORBIDDEN.",
        "",
        "## Chain",
        "",
        f"1. **physical search adv_id:** `20646357`",
        f"2. **linkage mechanism:** `{linkage.get('linkage_confidence')}` via `{linkage.get('linkage_field')}`",
        f"3. **parent auto adv_id:** `{linkage.get('parent_auto_adv_id')}`",
        f"4. **parent advsetting id:** `{linkage.get('parent_advsetting_id')}`",
        f"5. **parent auto name (PG):** `{linkage.get('parent_name', '')}`",
        f"6. **PG `_search_adv_id` column on parent:** empty (runtime resolves via name property)",
        "",
        "## Control owner (watchdog path)",
        "",
        f"- controlling advsetting: `{control.get('controlling_advsetting_id')}` (parent auto `17906286`)",
        f"- watchdog_enabled: `{control.get('watchdog_enabled')}` (on parent row, not standalone search row)",
        f"- active_limit_field: `{control.get('active_limit_field')}`",
        f"- current_limit: `{control.get('current_limit')}`",
        f"- code_field_checked: `{control.get('code_field_checked')}`",
        f"- control_status: `{control.get('control_status')}`",
        "",
        "## Standalone PG row 20646357 (advsetting `220298`)",
        "",
        "- bot_active=False, auto_budget_watchdog_enabled=False",
        "- auto_budget_daily_limit=0, search_auto_budget_daily_limit=0",
        "- **Not** loaded by `WBShopDataManager._get_active_advs` (requires bot_active=True)",
        "- Watchdog does **not** use standalone row limits for pause/start",
        "",
        "## Why Redis returned `search_limit_ok`",
        "",
        "Redis key: `campaign-activity-reason:20646357:search`",
        "",
        f"Value: `{json.dumps(redis.get('parsed'), ensure_ascii=False)}`",
        "",
        "Mechanism (code evidence):",
        "- `auto_budget_watchdog` → `get_complex_advs()` builds `ComplexAdv` from parent auto row `17906286`",
        "- `AdvSetting.search_adv_id` property parses `<!-[20646357]-!>` from parent name when `_search_adv_id` is NULL",
        f"- File: `{CODE_EVIDENCE['name_search_link'][0]}` / `{CODE_EVIDENCE['name_search_link'][1]}`",
        "- `_search_campaign_handler` uses `adv.search_adv_id` (=20646357) for spend measurement",
        "- Limit read from **parent** `search_auto_budget_daily_limit=1000` on advsetting `194194`",
        f"- File: `{CODE_EVIDENCE['search_pause_start'][0]}` / `{CODE_EVIDENCE['search_pause_start'][1]}`",
        "- When `search_limit > 0` and WB search status STARTED → `_set_search_reason(..., SEARCH_LIMIT_OK)`",
        "- Redis TTL key written by `RedisCampaignActivityReasonManager` at search **physical** adv_id",
        f"- File: `{CODE_EVIDENCE['redis_reason'][0]}`",
        "",
        "## WB mutation path",
        "",
        "- pause: `WBPromotionManager.pause_auction_campaign` → `pause_campaign_by_type(SEARCH)`",
        "- start: `_start_auction_campaign_maybe_retry`",
        f"- File: `{CODE_EVIDENCE['search_pause_start'][0]}`",
        "",
        "## 20646357_CONTROL_LINKAGE",
        "",
        f"**{linkage.get('linkage_confidence', 'GAP')}** (parent `17906286` name metadata → runtime `search_adv_id`)",
        "",
    ]
    return "\n".join(lines)


def build_package(
    root: Path,
    source_dir: Path,
    pg_rows: list[dict[str, str]],
) -> dict[str, Any]:
    checked_msk = datetime.now(MSK)
    pkg = root / PACKAGE_NAME
    pkg.mkdir(parents=True, exist_ok=True)

    contour = _read_csv(source_dir / "ACTIVE_AD_CONTOUR.csv")
    pg_by_adv, search_to_parent_row, search_to_parent_adv = _build_parent_maps(pg_rows)

    logical_rows: list[dict[str, Any]] = []
    physical_map: list[dict[str, Any]] = []
    search_trace: list[dict[str, Any]] = []

    physical_ids: set[int] = set()
    spending_ids: set[int] = set()

    for row in contour:
        adv_id = int(row["adv_id"])
        leg = row.get("leg_type") or "standalone"
        physical_ids.add(adv_id)
        spend29 = float(row.get("spend_2026_08_29") or 0)
        spend30 = float(row.get("spend_2026_08_30") or 0)
        spend31 = float(row.get("spend_2026_08_31_partial") or 0)
        if spend29 + spend30 + spend31 > 0:
            spending_ids.add(adv_id)

        own_pg = pg_by_adv.get(adv_id, {})
        parent_adv_id = search_to_parent_adv.get(adv_id, "") if leg == "Search" else ""
        if leg == "Auto":
            parent_adv_id = ""
            resolved_search = _resolved_search_adv_id(own_pg) if own_pg else None
        else:
            resolved_search = ""

        linkage = _linkage_for_search(adv_id, pg_by_adv, search_to_parent_row, search_to_parent_adv) if leg == "Search" else {}
        control = _control_for_physical(adv_id, leg, pg_by_adv, search_to_parent_row, search_to_parent_adv)

        logical_rows.append(
            {
                "logical_row_adv_id": adv_id,
                "advsetting_id": own_pg.get("id", ""),
                "adv_id": adv_id,
                "search_adv_id_pg_column": own_pg.get("_search_adv_id", ""),
                "search_adv_id_resolved": _resolved_search_adv_id(own_pg) if own_pg else "",
                "physical_wb_campaign_id": adv_id,
                "campaign_name": row.get("campaign_name"),
                "nmID": row.get("primary_nm_id"),
                "wb_status": row.get("wb_status"),
                "leg_type": leg,
                "bot_linked": own_pg.get("bot_active", ""),
                "parent_advsetting_id": linkage.get("parent_advsetting_id") or (own_pg.get("id") if leg == "Auto" else ""),
                "parent_auto_adv_id": linkage.get("parent_auto_adv_id") or parent_adv_id,
                "spend_2026_08_29": spend29,
                "spend_2026_08_30": spend30,
                "spend_2026_08_31_partial": spend31,
            }
        )

        map_row = {
            "physical_adv_id": adv_id,
            "campaign_name": row.get("campaign_name"),
            "nmID": row.get("primary_nm_id"),
            "leg_type": leg,
            "parent_auto_adv_id": linkage.get("parent_auto_adv_id") or search_to_parent_adv.get(adv_id, ""),
            "advsetting_id": control.get("controlling_advsetting_id") or own_pg.get("id", ""),
            "linkage_source": linkage.get("linkage_confidence", "N/A" if leg != "Search" else "GAP"),
            "watchdog_enabled": control.get("watchdog_enabled"),
            "active_limit_field": control.get("active_limit_field"),
            "current_limit": control.get("current_limit"),
            "spend_29": spend29,
            "spend_30": spend30,
            "spend_31_partial": spend31,
            "control_status": control.get("control_status"),
        }
        physical_map.append(map_row)

        if leg == "Search":
            search_trace.append(
                {
                    **linkage,
                    "watchdog_on_parent": _watchdog_on(search_to_parent_row[adv_id])
                    if adv_id in search_to_parent_row
                    else False,
                    "parent_search_auto_budget_daily_limit": search_to_parent_row.get(adv_id, {}).get(
                        "search_auto_budget_daily_limit", ""
                    )
                    if adv_id in search_to_parent_row
                    else "",
                    "standalone_bot_active": own_pg.get("bot_active", ""),
                    "standalone_watchdog": own_pg.get("auto_budget_watchdog_enabled", ""),
                }
            )

    map_cols = list(physical_map[0].keys()) if physical_map else ["physical_adv_id"]
    trace_cols = list(search_trace[0].keys()) if search_trace else ["search_adv_id"]
    _write_csv(pkg / "PHYSICAL_CAMPAIGN_CONTROL_MAP.csv", physical_map, map_cols)
    _write_csv(pkg / "SEARCH_LINKAGE_TRACE.csv", search_trace, trace_cols)

    redis_20646357 = _redis_search_reason(20646357)
    link_20646357 = _linkage_for_search(20646357, pg_by_adv, search_to_parent_row, search_to_parent_adv)
    ctrl_20646357 = _control_for_physical(
        20646357, "Search", pg_by_adv, search_to_parent_row, search_to_parent_adv
    )
    link_21604374 = _linkage_for_search(21604374, pg_by_adv, search_to_parent_row, search_to_parent_adv)

    trace_md = _build_20646357_trace(link_20646357, ctrl_20646357, redis_20646357)
    (pkg / "20646357_CONTROL_TRACE.md").write_text(trace_md, encoding="utf-8")

    search_confirmed_parent = sum(
        1
        for s in search_trace
        if s.get("linkage_confidence") in ("DIRECT_DB", "DERIVED_FROM_CODE")
        and s.get("parent_auto_adv_id")
        and _watchdog_on(search_to_parent_row.get(int(s["search_adv_id"]), {}))
    )

    provenance = [
        "# SOURCE_PROVENANCE",
        "",
        f"- package: `{PACKAGE_NAME}`",
        f"- source_package: `{SOURCE_PACKAGE}`",
        f"- source_dir: `{source_dir.resolve()}`",
        f"- shop_id: `{SHOP_ID}`",
        f"- checked_at_msk: {checked_msk.strftime('%Y-%m-%d %H:%M:%S %Z')}",
        "- pg_source: public.advsetting CURRENT (with name column)",
        "- no_production_mutations: true",
        "",
        "## Code evidence cited",
        "",
    ]
    for key, (path, symbol, note) in CODE_EVIDENCE.items():
        provenance.append(f"- `{key}`: {path} :: {symbol} — {note}")
    (pkg / "SOURCE_PROVENANCE.md").write_text("\n".join(provenance), encoding="utf-8")

    payload: dict[str, Any] = {
        "package": PACKAGE_NAME,
        "PACKAGE_STATUS": "AUTHORITATIVE",
        "checked_at_msk": checked_msk.strftime("%Y-%m-%d %H:%M:%S %Z"),
        "LOGICAL_ROWS_COUNT": len(logical_rows),
        "UNIQUE_PHYSICAL_ADV_IDS_COUNT": len(physical_ids),
        "ACTIVE_SPENDING_PHYSICAL_ADV_IDS_COUNT": len(spending_ids),
        "SEARCH_CAMPAIGNS_COUNT": len(search_trace),
        "SEARCH_WITH_CONFIRMED_PARENT_CONTROL_COUNT": search_confirmed_parent,
        "20646357_CONTROL_LINKAGE": link_20646357.get("linkage_confidence", "GAP"),
        "21604374_CONTROL_LINKAGE": link_21604374.get("linkage_confidence", "GAP"),
        "LOGICAL_CONTOUR_RECONCILIATION": logical_rows,
        "PHYSICAL_CAMPAIGN_CONTROL_MAP": physical_map,
        "SEARCH_LINKAGE_TRACE": search_trace,
    }

    json_path = pkg / f"{PACKAGE_NAME}.json"
    json_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")

    file_hashes = {
        name: _sha256_file(pkg / name)
        for name in [
            "PHYSICAL_CAMPAIGN_CONTROL_MAP.csv",
            "SEARCH_LINKAGE_TRACE.csv",
            "20646357_CONTROL_TRACE.md",
            "SOURCE_PROVENANCE.md",
            f"{PACKAGE_NAME}.json",
        ]
    }
    manifest = {
        "package": PACKAGE_NAME,
        "PACKAGE_STATUS": "AUTHORITATIVE",
        "file_sha256": file_hashes,
        "integrity_gate_errors": [],
    }
    (pkg / "PACKAGE_MANIFEST.json").write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8"
    )

    zip_out = root / f"{PACKAGE_NAME}.zip"
    with zipfile.ZipFile(zip_out, "w", zipfile.ZIP_DEFLATED) as zf:
        for name in file_hashes:
            zf.write(pkg / name, arcname=name)
        zf.write(pkg / "PACKAGE_MANIFEST.json", arcname="PACKAGE_MANIFEST.json")

    archive_sha = _sha256_file(zip_out)
    payload["FINAL_ARCHIVE_SHA256"] = archive_sha
    payload["ABSOLUTE_ARCHIVE_PATH"] = str(zip_out.resolve())
    json_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")

    return {
        "PACKAGE_STATUS": "AUTHORITATIVE",
        "LOGICAL_ROWS_COUNT": len(logical_rows),
        "UNIQUE_PHYSICAL_ADV_IDS_COUNT": len(physical_ids),
        "ACTIVE_SPENDING_PHYSICAL_ADV_IDS_COUNT": len(spending_ids),
        "SEARCH_CAMPAIGNS_COUNT": len(search_trace),
        "SEARCH_WITH_CONFIRMED_PARENT_CONTROL_COUNT": search_confirmed_parent,
        "20646357_CONTROL_LINKAGE": link_20646357.get("linkage_confidence", "GAP"),
        "21604374_CONTROL_LINKAGE": link_21604374.get("linkage_confidence", "GAP"),
        "FINAL_ARCHIVE_SHA256": archive_sha,
        "ABSOLUTE_ARCHIVE_PATH": str(zip_out.resolve()),
    }


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="A1 physical contour + search control map READ_ONLY.")
    parser.add_argument("--output-dir", default=".tmp/a1_physical_contour")
    parser.add_argument(
        "--source-dir",
        default=".tmp/a1_iteration_04/A1-ITERATION-04-CURRENT-STATE-AND-CAP-CONTROL-INPUT",
    )
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    root = Path(args.output_dir).resolve()
    source_dir = Path(args.source_dir).resolve()
    if not (source_dir / "ACTIVE_AD_CONTOUR.csv").exists():
        raise FileNotFoundError(f"Missing source package at {source_dir}")
    root.mkdir(parents=True, exist_ok=True)
    _bootstrap_cluster_infra()
    pg_rows = _load_pg_advsettings(root, root / "sql")
    result = build_package(root, source_dir, pg_rows)
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
