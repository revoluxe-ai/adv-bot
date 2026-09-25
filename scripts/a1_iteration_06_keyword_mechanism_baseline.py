"""READ_ONLY: A1 Iteration-06 keyword mechanism baseline for aggressiveness test prep.

Собирает keyword-level baseline по CONTROL/TEST parents из Iteration-06 design:
  CONTROL: 25174753, 21542370
  TEST:    37236815, 37289966

Источники (read-only):
  - PG advsetting + keywordsetting (ladder state, max_cpm)
  - WB POST /adv/v0/normquery/stats (views/clicks/spend per norm_query)
  - WB POST /adv/v0/normquery/get-bids (live bids, search leg)
  - CH bid_decision_log (internal last bid — NOT WB ground truth)
"""

from __future__ import annotations

import argparse
import asyncio
import csv
import json
import os
import re
import statistics
import sys
from collections import defaultdict
from datetime import date, datetime
from pathlib import Path
from typing import Any
from zoneinfo import ZoneInfo

import dotenv

dotenv.load_dotenv()

from scripts import ch_a1_evidence as evidence
from scripts.wb_a1_associated_conversions import _jsonable, _read_float, _read_int
from scripts.wb_api_readonly_ops.mutation_guard import assert_read_only_op

SHOP_ID = "5339e9ad-cbfe-50fc-8d77-b9f337a80417"
MSK = ZoneInfo("Europe/Moscow")
PACKAGE = "A1-ITERATION-06-KEYWORD-MECHANISM-BASELINE"

TARGETS: dict[int, str] = {
    25174753: "CONTROL",
    21542370: "CONTROL",
    37236815: "TEST",
    37289966: "TEST",
}

# Ближайший закрытый день перед PROPOSED_START 2026-09-03 + окно стабильности.
PRIMARY_BASELINE_DAY = date(2026, 9, 1)
WINDOW_FROM = date(2026, 8, 27)
WINDOW_TO = date(2026, 9, 1)
NEAR_MAX_BID_RATIO = 0.9

NAME_SEARCH = re.compile(r"<!-\[(\d+)\]-!>")

PG_ADV_FIELDS = [
    "id", "adv_id", "_search_adv_id", "name", "nmids", "aggressiveness",
    "strategy", "automatic_version", "max_cpm", "active_status", "bot_active",
]
PG_KW_FIELDS = [
    "id", "text", "hard_status", "strategy_mode", "target_place",
    "predict_ctr", "relevant", "auto_block",
]


def _pg_db() -> str:
    return os.environ.get("POSTGRES_DBNAME") or "adv_updater"


def _bootstrap() -> None:
    u, p = os.environ.get("POSTGRES_USER"), os.environ.get("POSTGRES_PASSWORD")
    if u and p:
        evidence._PG_CREDENTIALS = u, p
    h = os.environ.get("POSTGRES_MASTER_HOST") or os.environ.get("POSTGRES_REPLICA_HOST")
    if h:
        evidence.PG_EXTERNAL_HOST = h
    pt = os.environ.get("POSTGRES_PORT")
    if pt:
        evidence.PG_EXTERNAL_PORT = int(pt)
    ch_host = os.environ.get("CLICK_HOUSE_HOST")
    ch_port = os.environ.get("CLICKHOUSE_PORT", "8123")
    if ch_host:
        evidence.CH_HTTP_URL = f"http://{ch_host}:{ch_port}/"


def _parse_nmids(raw: str) -> list[int]:
    if not raw:
        return []
    try:
        val = json.loads(raw.replace("'", '"'))
        return [int(x) for x in val if str(x).isdigit()] if isinstance(val, list) else []
    except json.JSONDecodeError:
        return []


def _resolved_search(row: dict[str, str]) -> int | None:
    raw = (row.get("_search_adv_id") or "").strip()
    if raw.isdigit() and int(raw) > 0:
        return int(raw)
    m = NAME_SEARCH.search((row.get("name") or "").replace(" ", ""))
    return int(m.group(1)) if m else None


def _is_active_keyword(kw: dict[str, str]) -> bool:
    hard = str(kw.get("hard_status") or "").strip()
    mode = (kw.get("strategy_mode") or "").strip().upper()
    if hard in ("0", "3"):
        return False
    if mode in ("OFF", "0"):
        return False
    return True


def _percentile(vals: list[float], p: float) -> float | None:
    if not vals:
        return None
    s = sorted(vals)
    if len(s) == 1:
        return float(s[0])
    k = (len(s) - 1) * p / 100.0
    f = int(k)
    c = min(f + 1, len(s) - 1)
    if f == c:
        return float(s[f])
    return float(s[f] + (s[c] - s[f]) * (k - f))


def _concentration(rows: list[dict[str, Any]], field: str) -> dict[str, Any]:
    total = sum(float(r.get(field) or 0) for r in rows)
    if total <= 0:
        return {
            "total": 0.0,
            "top1_share_pct": 0.0,
            "top3_share_pct": 0.0,
            "top10_share_pct": 0.0,
            "top_keywords": [],
        }
    ranked = sorted(rows, key=lambda r: -float(r.get(field) or 0))

    def _share(n: int) -> float:
        return round(100 * sum(float(r.get(field) or 0) for r in ranked[:n]) / total, 2)

    return {
        "total": round(total, 2),
        "top1_share_pct": _share(1),
        "top3_share_pct": _share(3),
        "top10_share_pct": _share(10),
        "top_keywords": [r.get("norm_query") for r in ranked[:10]],
    }


def _load_pg(root: Path) -> tuple[dict[int, dict[str, str]], dict[int, list[dict[str, str]]]]:
    staging = root / "staging"
    staging.mkdir(parents=True, exist_ok=True)
    ids = ",".join(str(i) for i in TARGETS)
    adv_out = staging / "advsetting.csv"
    cols = ", ".join(f"a.{c}" for c in PG_ADV_FIELDS)
    q_adv = (
        f"SELECT {cols} FROM public.advsetting a "
        f"JOIN public.wbcabinet c ON a.wb_cabinet_id = c.id "
        f"WHERE c.shop_id = '{SHOP_ID}' AND a.adv_id IN ({ids})"
    )
    st = evidence.run_pg_query(_pg_db(), q_adv, adv_out, root / "sql" / "pg_adv.sql", csv_output=True)
    if not st["success"]:
        raise RuntimeError(st["stderr"])
    adv_by_parent: dict[int, dict[str, str]] = {}
    advsetting_ids: list[int] = []
    with adv_out.open(encoding="utf-8", newline="") as f:
        for row in csv.DictReader(f):
            aid = int(row["adv_id"])
            adv_by_parent[aid] = row
            advsetting_ids.append(int(row["id"]))

    kw_by_parent: dict[int, list[dict[str, str]]] = {p: [] for p in TARGETS}
    if advsetting_ids:
        kw_out = staging / "keywordsetting.csv"
        id_list = ",".join(str(i) for i in advsetting_ids)
        kw_cols = ", ".join(PG_KW_FIELDS) + ", adv_setting_id"
        q_kw = f"SELECT {kw_cols} FROM public.keywordsetting WHERE adv_setting_id IN ({id_list})"
        st2 = evidence.run_pg_query(_pg_db(), q_kw, kw_out, root / "sql" / "pg_kw.sql", csv_output=True)
        if not st2["success"]:
            raise RuntimeError(st2["stderr"])
        adv_id_by_setting = {int(v["id"]): int(v["adv_id"]) for v in adv_by_parent.values()}
        setting_to_parent = adv_id_by_setting
        with kw_out.open(encoding="utf-8", newline="") as f:
            for row in csv.DictReader(f):
                sid = int(row["adv_setting_id"])
                parent = setting_to_parent.get(sid)
                if parent in kw_by_parent:
                    kw_by_parent[parent].append(row)
    return adv_by_parent, kw_by_parent


def _load_ch_bids(root: Path, adv_id: int, nmid: int) -> dict[str, dict[str, Any]]:
    out = root / "staging" / f"ch_bids_{adv_id}.jsonl"
    q = (
        f"SELECT norm_query, argMax(cpm_curr, version) AS cpm_curr, "
        f"argMax(final_bid, version) AS final_bid, "
        f"argMax(decision_time, version) AS decision_time "
        f"FROM default_db.bid_decision_log "
        f"WHERE adv_id = {adv_id} AND nmid = {nmid} "
        f"GROUP BY norm_query"
    )
    st = evidence.run_ch_query(q, out, root / "sql" / f"ch_bids_{adv_id}.sql")
    if not st["success"]:
        return {}
    return {str(r.get("norm_query") or ""): r for r in evidence.read_jsonl(out)}


async def _fetch_wb(
    contours: list[dict[str, Any]],
) -> tuple[list[dict[str, Any]], list[dict[str, Any]], list[str]]:
    """Возвращает (normquery_rows, live_bid_rows, gaps)."""
    from app.configs.app_config import AppConfig
    from app.core.di.wb_manager_hub.wb_manager_hub_factory import WBManagerHubFactory
    from app.core.mp.wb.api.adapter.promotion_client.normquery_stats.command import (
        GetNormqueryStatsCommand,
        GetNormqueryStatsCommandBatchForAdv,
    )
    from app.core.mp.wb.api.generated.promotion.v1.marketing_and_promotions_client.models import (
        V0GetNormQueryBidsRequest,
        V0GetNormQueryBidsRequestItem,
    )
    from app.core.mp.wb.api.httpx_client_handler import HttpxClientHandler
    from app.core.redis_manager_v2.redis_client import RedisClient
    from app.modules.common_slaves.wildberries.super_cabinet_manager import get_access_for_wb_cabinet
    from redis.asyncio import Redis

    assert_read_only_op("keyword_mechanism_baseline")
    gaps: list[str] = []
    app_config = AppConfig.create()
    rc = app_config.infrastructure.redis
    redis_raw: Redis[str] = Redis(
        host=rc.host, port=rc.port, db=rc.db, password=rc.password, decode_responses=True,
    )
    await redis_raw.ping()
    redis_wrap = RedisClient(redis_client=redis_raw)
    httpx = HttpxClientHandler()
    await httpx.init()
    norm_rows: list[dict[str, Any]] = []
    bid_rows: list[dict[str, Any]] = []
    try:
        await get_access_for_wb_cabinet(SHOP_ID)
        hub = WBManagerHubFactory(httpx_client_handler=httpx, redis_client_wrapper=redis_wrap).get_wb_manager_hub(SHOP_ID)
        pm = hub.wb_data_manager.promotion_manager
        norm_adapter = pm._client.normquery_stats_adapter
        bids_adapter = pm._client.normquery_bids_adapter

        # normquery stats: primary day + full window per leg
        for c in contours:
            parent = c["parent_auto_adv_id"]
            nmid = c["nmID"]
            for leg in c["legs"]:
                adv_id = leg["physical_adv_id"]
                for label, d_from, d_to in (
                    ("PRIMARY_DAY", PRIMARY_BASELINE_DAY, PRIMARY_BASELINE_DAY),
                    ("WINDOW", WINDOW_FROM, WINDOW_TO),
                ):
                    cmd = GetNormqueryStatsCommand(
                        date_from=d_from,
                        date_to=d_to,
                        batchs=[GetNormqueryStatsCommandBatchForAdv(adv_id=adv_id, nmid=nmid)],
                    )
                    dtos = await norm_adapter.get_adv_v0_normquery_stats(cmd)
                    for dto in dtos or []:
                        dto_dict = _jsonable(dto.model_dump() if hasattr(dto, "model_dump") else dto)
                        for stat in dto_dict.get("stats") or []:
                            norm_rows.append({
                                "window_label": label,
                                "parent_auto_adv_id": parent,
                                "leg_type": leg["leg_type"],
                                "physical_adv_id": adv_id,
                                "nmID": nmid,
                                "norm_query": stat.get("norm_query"),
                                "views": int(stat.get("views") or 0),
                                "clicks": int(stat.get("clicks") or 0),
                                "spend": round(float(stat.get("spend") or 0), 2),
                                "cpm": stat.get("cpm"),
                                "cpc": stat.get("cpc"),
                                "ctr": stat.get("ctr"),
                                "orders": int(stat.get("orders") or 0),
                                "avr_pos": stat.get("avr_pos"),
                            })
                    await asyncio.sleep(0.5)

        # live bids — search leg only (WB authoritative route)
        bid_items: list[V0GetNormQueryBidsRequestItem] = []
        for c in contours:
            sid = c.get("search_physical_adv_id")
            nmid = c["nmID"]
            if sid:
                bid_items.append(V0GetNormQueryBidsRequestItem(advert_id=sid, nm_id=nmid))
        if bid_items:
            req = V0GetNormQueryBidsRequest(items=bid_items)
            live = await bids_adapter.post_adv_v0_normquery_get_bids(req)
            if not live:
                gaps.append("wb_normquery_get_bids_returned_empty_or_none")
            for dto in live or []:
                bid_rows.append({
                    "source": "WB_API_normquery_get_bids",
                    "parent_auto_adv_id": next(
                        c["parent_auto_adv_id"] for c in contours
                        if c.get("search_physical_adv_id") == dto.advert_id
                    ),
                    "physical_adv_id": dto.advert_id,
                    "leg_type": "Search",
                    "nmID": dto.nm_id,
                    "norm_query": dto.norm_query,
                    "bid": dto.bid,
                })
        else:
            gaps.append("no_search_legs_for_get_bids")
    finally:
        await httpx.shutdown()
        await redis_raw.aclose()
    return norm_rows, bid_rows, gaps


def _aggregate_leg(
    parent: int,
    leg: dict[str, Any],
    keywords: list[dict[str, str]],
    norm_primary: list[dict[str, Any]],
    norm_window: list[dict[str, Any]],
    wb_bids: dict[str, int],
    ch_bids: dict[str, dict[str, Any]],
    max_cpm: int | None,
) -> dict[str, Any]:
    kw_texts = {str(k.get("text") or "") for k in keywords}
    active_kws = [k for k in keywords if _is_active_keyword(k)]
    active_texts = {str(k.get("text") or "") for k in active_kws}

    with_impr = [r for r in norm_primary if int(r.get("views") or 0) > 0]
    with_clicks = [r for r in norm_primary if int(r.get("clicks") or 0) > 0]
    served_queries = {str(r.get("norm_query") or "") for r in norm_primary if float(r.get("spend") or 0) > 0 or int(r.get("views") or 0) > 0}

    # bid map: prefer WB live, fallback CH internal
    bid_map: dict[str, dict[str, Any]] = {}
    for nq in kw_texts | served_queries:
        entry: dict[str, Any] = {"norm_query": nq}
        if nq in wb_bids:
            entry["bid"] = wb_bids[nq]
            entry["bid_source"] = "WB_API_normquery_get_bids"
        elif nq in ch_bids:
            entry["bid"] = ch_bids[nq].get("cpm_curr")
            entry["bid_source"] = "CH_bid_decision_log_internal"
        else:
            entry["bid"] = None
            entry["bid_source"] = "GAP"
        bid_map[nq] = entry

    bid_vals = [float(v["bid"]) for v in bid_map.values() if v.get("bid") is not None]
    near_max_count = 0
    at_max_count = 0
    if max_cpm and max_cpm > 0:
        for v in bid_vals:
            if v >= max_cpm:
                at_max_count += 1
            elif v >= NEAR_MAX_BID_RATIO * max_cpm:
                near_max_count += 1

    # spend-weighted bid for served keywords
    spend_by_kw = {str(r.get("norm_query") or ""): float(r.get("spend") or 0) for r in norm_primary}
    total_spend = sum(spend_by_kw.values())
    high_bid_spend = 0.0
    if bid_vals:
        p90 = _percentile(bid_vals, 90) or max(bid_vals)
        for nq, sp in spend_by_kw.items():
            b = bid_map.get(nq, {}).get("bid")
            if b is not None and float(b) >= p90:
                high_bid_spend += sp

    return {
        "parent_auto_adv_id": parent,
        "physical_adv_id": leg["physical_adv_id"],
        "leg_type": leg["leg_type"],
        "baseline_day": PRIMARY_BASELINE_DAY.isoformat(),
        "window": f"{WINDOW_FROM.isoformat()}..{WINDOW_TO.isoformat()}",
        "configured_max_cpm": max_cpm,
        "pg_keyword_counts": {
            "total_keyword_count": len(keywords),
            "active_keyword_count": len(active_kws),
            "active_not_in_pg_but_served": len(served_queries - active_texts),
        },
        "primary_day_traffic": {
            "keywords_with_impressions": len(with_impr),
            "keywords_with_clicks": len(with_clicks),
            "keywords_with_spend_gt_0": sum(1 for r in norm_primary if float(r.get("spend") or 0) > 0),
            "total_views": sum(int(r.get("views") or 0) for r in norm_primary),
            "total_clicks": sum(int(r.get("clicks") or 0) for r in norm_primary),
            "total_spend": round(total_spend, 2),
            "spend_concentration": _concentration(norm_primary, "spend"),
            "click_concentration": _concentration(norm_primary, "clicks"),
        },
        "window_traffic": {
            "keywords_with_impressions": sum(1 for r in norm_window if int(r.get("views") or 0) > 0),
            "keywords_with_clicks": sum(1 for r in norm_window if int(r.get("clicks") or 0) > 0),
            "total_spend": round(sum(float(r.get("spend") or 0) for r in norm_window), 2),
            "spend_concentration": _concentration(norm_window, "spend"),
            "click_concentration": _concentration(norm_window, "clicks"),
        },
        "bid_distribution": {
            "keywords_with_bid": len(bid_vals),
            "bid_source_mix": {
                "WB_API": sum(1 for v in bid_map.values() if v.get("bid_source") == "WB_API_normquery_get_bids"),
                "CH_internal": sum(1 for v in bid_map.values() if v.get("bid_source") == "CH_bid_decision_log_internal"),
                "GAP": sum(1 for v in bid_map.values() if v.get("bid_source") == "GAP"),
            },
            "min": min(bid_vals) if bid_vals else None,
            "median": round(statistics.median(bid_vals), 2) if bid_vals else None,
            "p75": _percentile(bid_vals, 75),
            "p90": _percentile(bid_vals, 90),
            "max": max(bid_vals) if bid_vals else None,
            "at_or_near_max": {
                "configured_max_cpm": max_cpm,
                "at_max_count": at_max_count,
                "near_max_count": near_max_count,
                "near_max_threshold_ratio": NEAR_MAX_BID_RATIO,
            },
            "share_spend_from_highest_bid_decile": round(
                100 * high_bid_spend / total_spend, 2
            ) if total_spend > 0 and bid_vals else None,
        },
        "keyword_detail_sample": sorted(
            [
                {
                    **bid_map.get(str(r.get("norm_query") or ""), {"norm_query": r.get("norm_query")}),
                    "views": r.get("views"),
                    "clicks": r.get("clicks"),
                    "spend": r.get("spend"),
                    "cpc": r.get("cpc"),
                }
                for r in norm_primary
            ],
            key=lambda x: -float(x.get("spend") or 0),
        )[:25],
    }


_ch_cache: dict[tuple[int, int, int], dict[str, dict[str, Any]]] = {}
_ch_root = Path(".")


def _load_ch_bids_for(parent: int, nmid: int, phys: int) -> dict[str, dict[str, Any]]:
    key = (parent, nmid, phys)
    if key not in _ch_cache:
        _ch_cache[key] = _load_ch_bids(_ch_root, phys, nmid)
    return _ch_cache[key]


def _finalize(
    checked: datetime,
    contours: list[dict[str, Any]],
    parent_reports: list[dict[str, Any]],
    norm_rows: list[dict[str, Any]],
    bid_rows: list[dict[str, Any]],
    gaps: list[str],
    kw_by_parent: dict[int, list[dict[str, str]]],
) -> dict[str, Any]:
    has_norm = any(float(r.get("spend") or 0) > 0 or int(r.get("views") or 0) > 0 for r in norm_rows)
    has_wb_bids = len(bid_rows) > 0
    has_pg_kw = all(len(kw_by_parent.get(p, [])) > 0 for p in TARGETS)

    # Re-evaluate observability
    if not has_norm:
        gaps.append("normquery_stats_empty_for_baseline_window")
    if not has_wb_bids:
        gaps.append("wb_get_bids_empty_known_unreliable_api")

    keyword_observable = "NO"
    if has_norm and has_pg_kw:
        keyword_observable = "PARTIAL" if not has_wb_bids else "YES"
    elif has_norm:
        keyword_observable = "PARTIAL"

    baseline_complete = "YES" if has_norm and all(
        any(lg["primary_day_traffic"]["total_spend"] > 0 or lg["primary_day_traffic"]["total_views"] > 0
            for lg in p["legs_baseline"])
        for p in parent_reports
    ) else "NO"

    minimal_gap = (
        "Add wb_api_readonly_ops collect_normquery_bids + per-leg normquery stats export to runner; "
        "wire keyword baseline into iteration-06 observation packet. "
        "For full bid-traffic hypothesis: require reliable WB get-bids OR persist WB bids at write-path; "
        "keyword distribution metrics need normquery/stats + get-bids per search leg at daily cadence."
    )

    return {
        "CHECKED_AT_MSK": checked.strftime("%Y-%m-%d %H:%M:%S %Z"),
        "MODE": "STRICT_READ_ONLY",
        "AGGRESSIVENESS_TEST": "NOT_EXECUTED",
        "BASELINE_DAY": PRIMARY_BASELINE_DAY.isoformat(),
        "BASELINE_WINDOW": f"{WINDOW_FROM.isoformat()}..{WINDOW_TO.isoformat()}",
        "TARGETS": TARGETS,
        "HYPOTHESIS": (
            "aggressiveness 3→1 → lower bid pressure → broader/cheaper served keyword traffic "
            "→ more clicks per ₽ without severe traffic loss"
        ),
        "HYPOTHESIS_MEASURABILITY": {
            "bid_pressure": "PARTIAL — WB get-bids (search leg) + CH bid_decision_log fallback; adapter notes API may return empty",
            "served_keyword_breadth": "YES — normquery/stats views/clicks/spend per norm_query per leg",
            "clicks_per_ruble": "YES — aggregate clicks/spend from normquery/stats",
            "traffic_loss": "YES — views/clicks totals + concentration metrics",
            "auto_vs_search_split": "YES — per-leg normquery/stats",
        },
        "AUTHORITATIVE_SOURCES": {
            "keyword_traffic": "WB POST /adv/v0/normquery/stats",
            "live_bids": "WB POST /adv/v0/normquery/get-bids (search physical adv_id only)",
            "ladder_state": "PG public.keywordsetting (strategy_mode, target_place, hard_status)",
            "configured_max_bid": "PG public.advsetting.max_cpm",
            "internal_bid_fallback": "CH default_db.bid_decision_log (NOT WB ground truth)",
            "NOT_AUTHORITATIVE": "GET /adv/v3/fullstats (no keyword dimension)",
        },
        "PARENT_BASELINES": parent_reports,
        "NORMQUERY_ROW_COUNT": len(norm_rows),
        "WB_LIVE_BID_ROW_COUNT": len(bid_rows),
        "KEYWORD_MECHANISM_OBSERVABLE": keyword_observable,
        "BASELINE_COMPLETE": baseline_complete,
        "MINIMAL_GAP_TO_CLOSE": minimal_gap,
        "OPEN_GAPS": gaps,
    }


# Patch build to set _ch_root before CH loads
def build_with_root(
    root: Path,
    checked: datetime,
    adv_by_parent: dict[int, dict[str, str]],
    kw_by_parent: dict[int, list[dict[str, str]]],
    norm_rows: list[dict[str, Any]],
    bid_rows: list[dict[str, Any]],
    fetch_gaps: list[str],
) -> dict[str, Any]:
    global _ch_root
    _ch_root = root
    _ch_cache.clear()

    contours: list[dict[str, Any]] = []
    for parent, role in TARGETS.items():
        row = adv_by_parent.get(parent, {})
        nmid = (_parse_nmids(row.get("nmids") or "") or [0])[0]
        sid = _resolved_search(row)
        max_cpm_raw = row.get("max_cpm")
        max_cpm = int(max_cpm_raw) if str(max_cpm_raw or "").isdigit() else None
        legs = [{"leg_type": "Auto", "physical_adv_id": parent}]
        if sid:
            legs.append({"leg_type": "Search", "physical_adv_id": sid})
        contours.append({
            "parent_auto_adv_id": parent,
            "test_role": role,
            "nmID": nmid,
            "search_physical_adv_id": sid,
            "aggressiveness": row.get("aggressiveness"),
            "strategy": row.get("strategy"),
            "automatic_version": row.get("automatic_version"),
            "max_cpm_configured": max_cpm,
            "legs": legs,
        })

    wb_bids_by_parent: dict[int, dict[str, int]] = defaultdict(dict)
    for br in bid_rows:
        wb_bids_by_parent[int(br["parent_auto_adv_id"])][str(br["norm_query"])] = int(br["bid"])

    parent_reports: list[dict[str, Any]] = []
    gaps = list(fetch_gaps)

    for c in contours:
        parent = c["parent_auto_adv_id"]
        nmid = c["nmID"]
        leg_reports = []
        parent_auto_spend = 0.0
        parent_search_spend = 0.0
        for leg in c["legs"]:
            phys = leg["physical_adv_id"]
            norm_p = [
                r for r in norm_rows
                if r["window_label"] == "PRIMARY_DAY"
                and r["physical_adv_id"] == phys
                and r["parent_auto_adv_id"] == parent
            ]
            norm_w = [
                r for r in norm_rows
                if r["window_label"] == "WINDOW"
                and r["physical_adv_id"] == phys
                and r["parent_auto_adv_id"] == parent
            ]
            ch = _load_ch_bids_for(parent, nmid, phys)
            wb_map = wb_bids_by_parent.get(parent, {}) if leg["leg_type"] == "Search" else {}
            leg_rep = _aggregate_leg(
                parent, leg, kw_by_parent.get(parent, []),
                norm_p, norm_w, wb_map, ch, c["max_cpm_configured"],
            )
            leg_reports.append(leg_rep)
            sp = leg_rep["primary_day_traffic"]["total_spend"]
            if leg["leg_type"] == "Auto":
                parent_auto_spend += sp
            else:
                parent_search_spend += sp

        total_parent_spend = parent_auto_spend + parent_search_spend
        parent_reports.append({
            **{k: v for k, v in c.items() if k != "legs"},
            "legs_baseline": leg_reports,
            "auto_search_split_primary_day": {
                "auto_spend": round(parent_auto_spend, 2),
                "search_spend": round(parent_search_spend, 2),
                "auto_share_pct": round(100 * parent_auto_spend / total_parent_spend, 2) if total_parent_spend else None,
                "search_share_pct": round(100 * parent_search_spend / total_parent_spend, 2) if total_parent_spend else None,
            },
        })

    return _finalize(checked, contours, parent_reports, norm_rows, bid_rows, gaps, kw_by_parent)


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--output-dir", default=".tmp/a1_iter06_keyword_baseline")
    args = ap.parse_args(argv)
    root = Path(args.output_dir).resolve()
    root.mkdir(parents=True, exist_ok=True)
    _bootstrap()
    adv_by_parent, kw_by_parent = _load_pg(root)

    contours_pre = []
    for parent in TARGETS:
        row = adv_by_parent.get(parent, {})
        nmid = (_parse_nmids(row.get("nmids") or "") or [0])[0]
        sid = _resolved_search(row)
        legs = [{"leg_type": "Auto", "physical_adv_id": parent}]
        if sid:
            legs.append({"leg_type": "Search", "physical_adv_id": sid})
        contours_pre.append({
            "parent_auto_adv_id": parent,
            "nmID": nmid,
            "search_physical_adv_id": sid,
            "legs": legs,
        })

    async def _run() -> dict[str, Any]:
        norm_rows, bid_rows, gaps = await _fetch_wb(contours_pre)
        checked = datetime.now(MSK)
        payload = build_with_root(root, checked, adv_by_parent, kw_by_parent, norm_rows, bid_rows, gaps)
        pkg = root / PACKAGE
        pkg.mkdir(parents=True, exist_ok=True)
        (pkg / f"{PACKAGE}.json").write_text(
            json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8"
        )
        return payload

    out = asyncio.run(_run())
    summary = {k: v for k, v in out.items() if k != "PARENT_BASELINES"}
    summary["PARENT_BASELINE_SUMMARY"] = []
    for p in out.get("PARENT_BASELINES", []):
        legs_compact = []
        for lg in p.get("legs_baseline", []):
            legs_compact.append({
                "leg_type": lg["leg_type"],
                "physical_adv_id": lg["physical_adv_id"],
                "pg_total_keywords": lg["pg_keyword_counts"]["total_keyword_count"],
                "pg_active_keywords": lg["pg_keyword_counts"]["active_keyword_count"],
                "kw_with_impressions": lg["primary_day_traffic"]["keywords_with_impressions"],
                "kw_with_clicks": lg["primary_day_traffic"]["keywords_with_clicks"],
                "views": lg["primary_day_traffic"]["total_views"],
                "clicks": lg["primary_day_traffic"]["total_clicks"],
                "spend": lg["primary_day_traffic"]["total_spend"],
                "spend_top1_pct": lg["primary_day_traffic"]["spend_concentration"]["top1_share_pct"],
                "spend_top3_pct": lg["primary_day_traffic"]["spend_concentration"]["top3_share_pct"],
                "click_top1_pct": lg["primary_day_traffic"]["click_concentration"]["top1_share_pct"],
                "bid_median": lg["bid_distribution"]["median"],
                "bid_p90": lg["bid_distribution"]["p90"],
                "bid_max": lg["bid_distribution"]["max"],
                "at_max_bid_count": lg["bid_distribution"]["at_or_near_max"]["at_max_count"],
                "near_max_bid_count": lg["bid_distribution"]["at_or_near_max"]["near_max_count"],
                "high_bid_spend_share_pct": lg["bid_distribution"]["share_spend_from_highest_bid_decile"],
                "bid_wb_api_count": lg["bid_distribution"]["bid_source_mix"]["WB_API"],
                "bid_ch_internal_count": lg["bid_distribution"]["bid_source_mix"]["CH_internal"],
            })
        summary["PARENT_BASELINE_SUMMARY"].append({
            "parent_auto_adv_id": p["parent_auto_adv_id"],
            "test_role": p["test_role"],
            "nmID": p["nmID"],
            "search_physical_adv_id": p["search_physical_adv_id"],
            "max_cpm_configured": p["max_cpm_configured"],
            "auto_search_split_primary_day": p["auto_search_split_primary_day"],
            "legs": legs_compact,
        })
    summary["PARENT_COUNT"] = len(out.get("PARENT_BASELINES", []))
    print(json.dumps(summary, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
