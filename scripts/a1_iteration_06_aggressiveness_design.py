"""READ_ONLY: A1 Iteration-06 aggressiveness matched-group design (prep only).

DESIGN / PREP — no aggressiveness writes, no campaign mutations.
"""

from __future__ import annotations

import argparse
import asyncio
import csv
import hashlib
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
from scripts.wb_a1_associated_conversions import _read_float, _read_int
from scripts.wb_api_readonly_ops.collect.ads import _flatten_fullstats
from scripts.wb_api_readonly_ops.collect.api_budget import ApiCallBudget
from scripts.wb_api_readonly_ops.collect.orders_sales import _paginate_supplier_rows

SHOP_ID = "5339e9ad-cbfe-50fc-8d77-b9f337a80417"
MSK = ZoneInfo("Europe/Moscow")
PACKAGE = "A1-ITERATION-06-AGGRESSIVENESS-DESIGN"
CHECK_DATE = date(2026, 9, 2)
RAND_SEED = "A1-AGGR-ITER06-20260902"
PROPOSED_START = "2026-09-03 00:00 MSK"

ITER04_EXPECTED: dict[int, tuple[int, int]] = {
    17728892: (200, 150),
    17906286: (0, 450),
    20987867: (500, 200),
    21542370: (300, 50),
    21604339: (0, 350),
    25174753: (200, 300),
    25183231: (250, 200),
    25338885: (150, 450),
    37236815: (100, 400),
    37096258: (200, 100),
    37289966: (250, 100),
}
H1_PHYSICAL = {17906286, 21604339, 20646357, 21604374}
DEFERRED_ADV = 34210859
BULK_SKUS = {837395782, 195764899}

PRE_CAP_DAYS = ("2026-08-27", "2026-08-28", "2026-08-29", "2026-08-30")
TRANSITION_DAY = "2026-08-31"
POST_CAP_DAY = "2026-09-01"
ALL_DAYS = PRE_CAP_DAYS + (TRANSITION_DAY, POST_CAP_DAY)

PG_FIELDS = [
    "id", "adv_id", "_search_adv_id", "type", "name", "nmids", "active_status", "bot_active",
    "auto_budget_watchdog_enabled", "auto_budget_daily_limit", "search_auto_budget_daily_limit",
    "use_common_budget", "common_budget_daily_limit", "aggressiveness", "strategy",
    "automatic_version", "auto_adv_target_status", "auction_adv_target_status",
]
NAME_SEARCH = re.compile(r"<!-\[(\d+)\]-!>")


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


def _load_pg(root: Path) -> list[dict[str, str]]:
    staging = root / "staging"
    staging.mkdir(parents=True, exist_ok=True)
    out = staging / "pg.csv"
    cols = ", ".join(f"a.{c}" for c in PG_FIELDS)
    q = (
        f"SELECT {cols} FROM public.advsetting a "
        f"JOIN public.wbcabinet c ON a.wb_cabinet_id = c.id "
        f"WHERE c.shop_id = '{SHOP_ID}'"
    )
    st = evidence.run_pg_query(_pg_db(), q, out, root / "sql" / "pg.sql", csv_output=True)
    if not st["success"]:
        raise RuntimeError(st["stderr"])
    with out.open(encoding="utf-8", newline="") as f:
        return list(csv.DictReader(f))


def _write_csv(path: Path, rows: list[dict[str, Any]], cols: list[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=cols, extrasaction="ignore")
        w.writeheader()
        for r in rows:
            w.writerow({c: r.get(c, "") for c in cols})


def _int_lim(v: Any) -> int:
    try:
        return int(float(v or 0))
    except (TypeError, ValueError):
        return 0


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


def _order_day(r: dict[str, Any]) -> str:
    return str(r.get("date") or "")[:10]


def _cancelled(r: dict[str, Any]) -> bool:
    return str(r.get("isCancel")).lower() in ("true", "1", "t")


def _gkey(r: dict[str, Any]) -> str:
    g = str(r.get("gNumber") or "").strip()
    return g or f"srid:{r.get('srid')}"


def _window(days: tuple[str, ...]) -> str:
    if days == PRE_CAP_DAYS:
        return "PRE_CAP_HISTORY"
    if days == (TRANSITION_DAY,):
        return "TRANSITION_DAY"
    return "POST_CAP_CLOSED"


def _supplier_metrics(rows: list[dict[str, Any]]) -> dict[str, Any]:
    groups: dict[str, list] = defaultdict(list)
    for r in rows:
        groups[_gkey(r)].append(r)
    units = len(rows)
    events = len(groups)
    bulk_units = sum(len(g) for g in groups.values() if len(g) >= 2)
    stp = round(sum(_read_float(r, "totalPrice") for r in rows), 2)
    return {
        "UNITS": units,
        "PURCHASE_EVENTS": events,
        "TOTAL_PRICE_VALUE": stp,
        "BULK_UNIT_SHARE": round(100 * bulk_units / units, 2) if units else 0,
        "units_per_event": round(units / events, 2) if events else 0,
    }


def _aggr_effective(row: dict[str, str]) -> str:
    ver = str(row.get("automatic_version") or "").strip()
    agg = _int_lim(row.get("aggressiveness"))
    bot = str(row.get("bot_active")).lower() in ("true", "t", "1")
    if not bot:
        return "NO"
    if ver not in ("3", "3.0"):
        return "NO"
    if agg < 1 or agg > 3:
        return "UNCERTAIN"
    # V3 rollout aggressiveness participates in SelectionPolicy.from_aggressiveness
    return "YES"


def _confounder_risk(nmid: int, row: dict[str, str], bulk_share_post: float) -> tuple[str, list[str]]:
    reasons: list[str] = []
    if nmid in BULK_SKUS:
        reasons.append("known_bulk_concentration_sku")
    if bulk_share_post >= 50:
        reasons.append("high_bulk_unit_share_post_cap")
    if str(row.get("strategy") or "").upper() not in ("", "MIN_CPO", "MAX_CONV"):
        reasons.append(f"strategy={row.get('strategy')}")
    reasons.extend(["price_history=GAP", "stock_history=GAP", "promo_history=GAP"])
    if nmid in BULK_SKUS or bulk_share_post >= 50:
        return "HIGH", reasons
    if len([r for r in reasons if "GAP" not in r]) > 0:
        return "MEDIUM", reasons
    return "LOW", reasons


def _adv_nm_map(campaigns: list[dict[str, Any]]) -> dict[int, set[int]]:
    out: dict[int, set[int]] = defaultdict(set)
    for c in campaigns:
        aid = _read_int(c, "id", "advertId")
        for nm in c.get("nm_settings") or c.get("nmSettings") or []:
            if isinstance(nm, dict):
                nid = _read_int(nm, "nm_id", "nmId", "nmID")
                if nid:
                    out[aid].add(nid)
    return out


def _randomize_pair(pair_id: str, unit_a: int, unit_b: int) -> dict[str, Any]:
    key = f"{RAND_SEED}:{pair_id}:{min(unit_a, unit_b)}:{max(unit_a, unit_b)}"
    digest = hashlib.sha256(key.encode()).hexdigest()
    flip = int(digest[:8], 16) % 2 == 0
    first, second = (unit_a, unit_b) if unit_a <= unit_b else (unit_b, unit_a)
    if flip:
        control, test = first, second
    else:
        control, test = second, first
    return {
        "PAIR_ID": pair_id,
        "CONTROL_adv_id": control,
        "CONTROL_aggressiveness": 3,
        "TEST_adv_id": test,
        "TEST_aggressiveness": 1,
        "randomization_seed": RAND_SEED,
        "randomization_hash": digest[:16],
    }


def _match_distance(a: dict[str, Any], b: dict[str, Any]) -> float:
    """Weighted L1 on normalized pre-test features (post-cap weighted 2x)."""
    weights = {
        "cap_sum": 3.0,
        "spend_post": 2.5,
        "spend_pre": 1.0,
        "clicks_post": 2.0,
        "cpc_post": 1.5,
        "ctr_post": 1.0,
        "purchase_events_post": 2.0,
        "total_price_post": 2.0,
        "units_per_event_post": 1.0,
        "bulk_share_post": 1.5,
    }
    dist = 0.0
    for k, w in weights.items():
        va = float(a.get(k) or 0)
        vb = float(b.get(k) or 0)
        scale = max(abs(va), abs(vb), 1.0)
        dist += w * abs(va - vb) / scale
    # category: same strategy bonus
    if a.get("strategy") != b.get("strategy"):
        dist += 2.0
    return dist


def build(
    checked: datetime,
    pg_rows: list[dict[str, str]],
    orders: list[dict[str, Any]],
    fullstats: list[dict[str, Any]],
    campaigns: list[dict[str, Any]],
    fullstats_meta: dict[str, int] | None = None,
) -> dict[str, Any]:
    fullstats_meta = fullstats_meta or {}
    gaps = ["KEYWORD_DISTRIBUTION=GAP (no keyword-level bid collector in readonly pipeline)",
            "price_stock_promo_historical=GAP",
            "stock_availability=GAP"]
    if not fullstats:
        gaps.append("fullstats_empty_in_design_job=VERIFY_AGAINST_ITER05")
    pg_by_adv: dict[int, dict[str, str]] = {}
    for row in pg_rows:
        try:
            aid = int(row.get("adv_id") or 0)
        except (TypeError, ValueError):
            continue
        if aid:
            pg_by_adv[aid] = row

    limits_ok = all(
        _int_lim(pg_by_adv.get(aid, {}).get("auto_budget_daily_limit")) == exp[0]
        and _int_lim(pg_by_adv.get(aid, {}).get("search_auto_budget_daily_limit")) == exp[1]
        for aid, exp in ITER04_EXPECTED.items()
    )

    # physical adv -> parent auto
    phys_parent: dict[int, int] = {}
    candidates_raw: list[dict[str, Any]] = []
    excluded_h1 = list(H1_PHYSICAL)
    excluded_342 = DEFERRED_ADV

    for auto_id, (exp_a, exp_s) in ITER04_EXPECTED.items():
        if auto_id in (17906286, 21604339):
            continue
        row = pg_by_adv.get(auto_id, {})
        if str(row.get("bot_active")).lower() not in ("true", "t", "1"):
            continue
        sid = _resolved_search(row)
        nmids = _parse_nmids(row.get("nmids") or "")
        nmid = nmids[0] if nmids else 0
        phys_parent[auto_id] = auto_id
        if sid:
            phys_parent[sid] = auto_id
        if auto_id == excluded_342 or sid == excluded_342:
            continue
        if auto_id in H1_PHYSICAL or (sid and sid in H1_PHYSICAL):
            continue

        agg_eff = _aggr_effective(row)
        cur_agg = _int_lim(row.get("aggressiveness"))
        cand = {
            "parent_adv_setting_id": row.get("id"),
            "parent_auto_adv_id": auto_id,
            "search_physical_adv_id": sid or "",
            "nmID": nmid,
            "CURRENT_AGGRESSIVENESS": cur_agg,
            "AGGRESSIVENESS_EFFECTIVE": agg_eff,
            "strategy": row.get("strategy") or "",
            "automatic_version": row.get("automatic_version") or "",
            "daily_auto_limit": exp_a,
            "daily_search_limit": exp_s,
            "cap_sum": exp_a + exp_s,
            "active_status": row.get("active_status"),
        }
        candidates_raw.append(cand)

    # orders by nmid
    orders_by_nm: dict[int, list[dict[str, Any]]] = defaultdict(list)
    for r in orders:
        if _cancelled(r):
            continue
        day = _order_day(r)
        if day not in ALL_DAYS:
            continue
        nmid = _read_int(r, "nmId", "nm_id")
        if nmid:
            orders_by_nm[nmid].append(r)

    # fullstats by physical adv
    fs_day: dict[tuple[int, str], dict[str, float]] = defaultdict(
        lambda: {"spend": 0, "views": 0, "clicks": 0, "orders": 0, "gmv": 0}
    )
    for row in fullstats:
        aid = _read_int(row, "advertId", "advert_id")
        day = str(row.get("date") or "")[:10]
        if not aid or day not in ALL_DAYS:
            continue
        b = fs_day[(aid, day)]
        b["spend"] += _read_float(row, "sum", "spend")
        b["views"] += _read_int(row, "views")
        b["clicks"] += _read_int(row, "clicks")
        b["orders"] += _read_int(row, "orders")
        b["gmv"] += _read_float(row, "sum_price")

    def _ad_window(parent_auto: int, sid: int | None, days: tuple[str, ...]) -> dict[str, Any]:
        legs = [parent_auto] + ([sid] if sid else [])
        spend = views = clicks = attr_o = attr_g = 0.0
        for leg in legs:
            if not leg:
                continue
            for d in days:
                b = fs_day.get((leg, d), {})
                spend += b.get("spend", 0)
                views += b.get("views", 0)
                clicks += b.get("clicks", 0)
                attr_o += b.get("orders", 0)
                attr_g += b.get("gmv", 0)
        cpc = round(spend / clicks, 4) if clicks else 0
        ctr = round(100 * clicks / views, 4) if views else 0
        return {
            "ad_spend": round(spend, 2),
            "views": int(views),
            "clicks": int(clicks),
            "CTR": ctr,
            "CPC": cpc,
            "ATTRIBUTED_ORDERS": int(attr_o),
            "ATTRIBUTED_GMV": round(attr_g, 2),
        }

    candidates: list[dict[str, Any]] = []
    for c in candidates_raw:
        nmid = int(c["nmID"] or 0)
        nm_rows = orders_by_nm.get(nmid, [])
        pre_rows = [r for r in nm_rows if _order_day(r) in PRE_CAP_DAYS]
        trans_rows = [r for r in nm_rows if _order_day(r) == TRANSITION_DAY]
        post_rows = [r for r in nm_rows if _order_day(r) == POST_CAP_DAY]
        sid = c["search_physical_adv_id"] or None
        sid_int = int(sid) if sid else None
        pre_sup = _supplier_metrics(pre_rows)
        trans_sup = _supplier_metrics(trans_rows)
        post_sup = _supplier_metrics(post_rows)
        tot_sup = _supplier_metrics(nm_rows)
        pre_ad = _ad_window(c["parent_auto_adv_id"], sid_int, PRE_CAP_DAYS)
        trans_ad = _ad_window(c["parent_auto_adv_id"], sid_int, (TRANSITION_DAY,))
        post_ad = _ad_window(c["parent_auto_adv_id"], sid_int, (POST_CAP_DAY,))
        total_ad = _ad_window(c["parent_auto_adv_id"], sid_int, ALL_DAYS)
        conf_risk, conf_reasons = _confounder_risk(nmid, pg_by_adv.get(c["parent_auto_adv_id"], {}),
                                                     post_sup["BULK_UNIT_SHARE"])
        spend_series = {
            d: round(
                sum(fs_day.get((leg, d), {}).get("spend", 0) for leg in [c["parent_auto_adv_id"], sid_int] if leg),
                2,
            )
            for d in ALL_DAYS
        }
        profile = {
            **c,
            "windows": {
                "PRE_CAP_HISTORY": {"supplier": pre_sup, "advertising": pre_ad},
                "TRANSITION_DAY": {"supplier": trans_sup, "advertising": trans_ad},
                "POST_CAP_CLOSED": {"supplier": post_sup, "advertising": post_ad},
            },
            "period_total": {"supplier": tot_sup, "advertising": total_ad, "spend_per_day": spend_series},
            "CONFOUNDER_RISK": conf_risk,
            "CONFOUNDER_NOTES": conf_reasons,
            "KEYWORD_DISTRIBUTION": "GAP",
            # matching features
            "spend_pre": pre_ad["ad_spend"],
            "spend_post": post_ad["ad_spend"],
            "clicks_post": post_ad["clicks"],
            "cpc_post": post_ad["CPC"],
            "ctr_post": post_ad["CTR"],
            "purchase_events_post": post_sup["PURCHASE_EVENTS"],
            "total_price_post": post_sup["TOTAL_PRICE_VALUE"],
            "units_per_event_post": post_sup["units_per_event"],
            "bulk_share_post": post_sup["BULK_UNIT_SHARE"],
        }
        candidates.append(profile)

    eligible = [c for c in candidates if c["AGGRESSIVENESS_EFFECTIVE"] == "YES" and c["CURRENT_AGGRESSIVENESS"] == 3]
    uncertain = [c for c in candidates if c["AGGRESSIVENESS_EFFECTIVE"] == "UNCERTAIN"]
    ineffective = [c for c in candidates if c["AGGRESSIVENESS_EFFECTIVE"] == "NO"]

    # Greedy pair matching among LOW/MEDIUM confounders first
    pool = sorted(
        [c for c in eligible if c["CONFOUNDER_RISK"] != "HIGH"],
        key=lambda x: -float(x["period_total"]["advertising"]["ad_spend"]),
    )
    high_risk = [c for c in eligible if c["CONFOUNDER_RISK"] == "HIGH"]

    pairs: list[dict[str, Any]] = []
    used: set[int] = set()
    pair_idx = 1
    while len(pool) >= 2:
        best = None
        best_dist = 1e9
        for i, a in enumerate(pool):
            if a["parent_auto_adv_id"] in used:
                continue
            for j, b in enumerate(pool):
                if i >= j or b["parent_auto_adv_id"] in used:
                    continue
                d = _match_distance(a, b)
                if d < best_dist:
                    best_dist = d
                    best = (a, b)
        if not best:
            break
        a, b = best
        used.add(a["parent_auto_adv_id"])
        used.add(b["parent_auto_adv_id"])
        pid = f"PAIR_{pair_idx:02d}"
        pair_idx += 1
        metrics = [
            "cap_sum", "spend_post", "spend_pre", "clicks_post", "cpc_post", "ctr_post",
            "purchase_events_post", "total_price_post", "units_per_event_post", "bulk_share_post",
        ]
        cmp_table = []
        for m in metrics:
            va, vb = a.get(m, 0), b.get(m, 0)
            diff = round(float(va) - float(vb), 4) if va != "GAP" else "GAP"
            pct = round(100 * abs(float(va) - float(vb)) / max(abs(float(va)), abs(float(vb)), 1), 2)
            cmp_table.append({"metric": m, "UNIT_A": va, "UNIT_B": vb, "diff": diff, "abs_pct_gap": pct})
        mq = "HIGH" if best_dist < 8 else ("MEDIUM" if best_dist < 15 else "LOW")
        pairs.append({
            "PAIR_ID": pid,
            "UNIT_A": a["parent_auto_adv_id"],
            "UNIT_B": b["parent_auto_adv_id"],
            "UNIT_A_nmID": a["nmID"],
            "UNIT_B_nmID": b["nmID"],
            "MATCH_DISTANCE": round(best_dist, 3),
            "MATCH_QUALITY": mq,
            "match_rationale": "minimized weighted L1 on cap/spend/traffic/supplier post-cap features; same V3 aggressiveness=3",
            "comparison_table": cmp_table,
            "randomization": _randomize_pair(pid, a["parent_auto_adv_id"], b["parent_auto_adv_id"]),
            "freeze_contract": {
                "daily_limits": "UNCHANGED",
                "strategy": "UNCHANGED",
                "campaign_activity": "UNCHANGED",
                "keyword_set": "UNCHANGED (except normal V3 runtime)",
                "experimental_variable": "TEST aggressiveness 3→1; CONTROL stays 3",
            },
        })

    primary_set = pairs[:3]  # up to 3 best pairs
    match_quality = "HIGH" if primary_set and all(p["MATCH_QUALITY"] == "HIGH" for p in primary_set) else (
        "MEDIUM" if primary_set and any(p["MATCH_QUALITY"] in ("HIGH", "MEDIUM") for p in primary_set) else "LOW"
    )
    if not primary_set:
        match_quality = "LOW"

    blocking = [c["parent_auto_adv_id"] for c in high_risk]
    readiness = "READY" if len(primary_set) >= 2 and limits_ok and all(
        p["MATCH_QUALITY"] in ("HIGH", "MEDIUM") for p in primary_set[:2]
    ) else "NOT_READY"

    # observation design
    min_obs_days = 7
    early_stop = [
        "technical_failure (watchdog/cap pipeline broken)",
        "severe_traffic_choke (clicks→0 with spend>0 on multiple units)",
        "runaway_spend (OVERSHOOT >150% cap without pause)",
        "major_confounder (documented price/stock/promo intervention)",
    ]

    aggr_state = {
        str(c["parent_auto_adv_id"]): {
            "CURRENT_AGGRESSIVENESS": c["CURRENT_AGGRESSIVENESS"],
            "AGGRESSIVENESS_EFFECTIVE": c["AGGRESSIVENESS_EFFECTIVE"],
            "automatic_version": c["automatic_version"],
            "strategy": c["strategy"],
        }
        for c in candidates
    }

    return {
        "CHECKED_AT_MSK": checked.strftime("%Y-%m-%d %H:%M:%S %Z"),
        "DESIGN_MODE": "READ_ONLY_PREP",
        "AGGRESSIVENESS_TEST": "NOT_EXECUTED",
        "PRESERVED_STATE": {
            "ITERATION_04_TECHNICAL_OBSERVATION": "PASS",
            "OBSERVATION_GATE": "MAY_BE_LIFTED",
            "ITERATION_04_CAUSAL_RESULT": "OPEN",
            "CAP_DESIGN": "CURRENTLY_ACCEPTABLE",
            "CAP_OVERSHOOT": "MONITOR / NON-BLOCKING",
            "NOMINAL_PORTFOLIO_CAP_RUB": 4900,
            "LIMITS_MATCH": "YES" if limits_ok else "NO",
        },
        "CANDIDATE_COUNT": len(candidates_raw),
        "ELIGIBLE_COUNT": len(eligible),
        "EXCLUDED_H1": excluded_h1,
        "EXCLUDED_34210859": excluded_342,
        "INEFFECTIVE_AGGRESSIVENESS": [c["parent_auto_adv_id"] for c in ineffective],
        "UNCERTAIN_AGGRESSIVENESS": [c["parent_auto_adv_id"] for c in uncertain],
        "HIGH_CONFOUNDER_EXCLUDED_FROM_MATCHING": blocking,
        "CURRENT_AGGRESSIVENESS_STATE": aggr_state,
        "CANDIDATE_UNIVERSE": candidates,
        "PRIMARY_MATCHED_SET": primary_set,
        "MATCH_QUALITY": match_quality,
        "RANDOMIZED_ASSIGNMENT": [p["randomization"] for p in primary_set],
        "KEYWORD_DISTRIBUTION_STATE": "GAP",
        "BLOCKING_CONFOUNDERS": blocking,
        "PROPOSED_START": PROPOSED_START,
        "PROPOSED_EXECUTION_METHOD": (
            "Midnight-boundary PG aggressiveness update on TEST parent adv_setting rows only; "
            "CONTROL unchanged; limits/strategy/activity frozen; shop-runner V3 tick applies ladder"
        ),
        "MIN_OBSERVATION_DAYS": min_obs_days,
        "EARLY_STOP_CRITERIA": early_stop,
        "PRIMARY_OUTCOME_METRIC": "PURCHASE_EVENTS / AD_SPEND",
        "SECONDARY_OUTCOMES": [
            "UNITS / AD_SPEND", "TOTAL_PRICE_VALUE / AD_SPEND",
            "PURCHASE_EVENTS", "UNITS", "TOTAL_PRICE_VALUE",
            "BULK_UNIT_SHARE", "units_per_event",
            "traffic_mechanism (clicks, CPC, CTR, keyword distribution when available)",
        ],
        "ITERATION_06_READINESS": readiness,
        "OPEN_GAPS": gaps,
        "FULLSTATS_ROWS": fullstats_meta.get("row_count", 0),
        "FULLSTATS_ADV_IDS_REQUESTED": fullstats_meta.get("adv_ids_requested", 0),
    }


async def fetch_data(root: Path) -> tuple[list, list, list, int, int]:
    import datetime as dt
    from app.configs.app_config import AppConfig
    from app.core.di.wb_manager_hub.wb_manager_hub_factory import WBManagerHubFactory
    from app.core.mp.wb.api.httpx_client_handler import HttpxClientHandler
    from app.core.redis_manager_v2.redis_client import RedisClient
    from app.modules.common_slaves.wildberries.super_cabinet_manager import get_access_for_wb_cabinet
    from redis.asyncio import Redis
    from scripts.wb_api_readonly_ops.collect.jsonable import jsonable

    app_config = AppConfig.create()
    rc = app_config.infrastructure.redis
    redis_raw: Redis[str] = Redis(
        host=rc.host, port=rc.port, db=rc.db, password=rc.password, decode_responses=True,
    )
    await redis_raw.ping()
    redis_wrap = RedisClient(redis_client=redis_raw)
    httpx = HttpxClientHandler()
    await httpx.init()
    try:
        await get_access_for_wb_cabinet(SHOP_ID)
        hub = WBManagerHubFactory(httpx_client_handler=httpx, redis_client_wrapper=redis_wrap).get_wb_manager_hub(SHOP_ID)
        dm = hub.wb_data_manager
        pm = dm.promotion_manager
        budget = ApiCallBudget(max_seconds=1200.0, max_api_calls=1200)
        rm = getattr(dm, "reports_manager", None)

        async def fetch_ord(df: str) -> list[object]:
            if rm:
                return list(await rm.get_supplier_orders(date_from=df, flag=0) or [])
            return list(await dm.get_supplier_orders(date_from=df, flag=0) or [])

        orders_res = await _paginate_supplier_rows(
            fetch=fetch_ord, initial_date_from="2026-08-27", budget=budget, max_pages=800,
        )
        budget.consume()
        adv_ids = list(await pm._client.promotion_count_adapter.get_cabinet_adv_ids() or [])
        budget.consume()
        camps_raw = list(await pm.get_adverts_v2_by_ids(adv_ids) or [])
        campaigns = [jsonable(x) for x in camps_raw if isinstance(jsonable(x), dict)]
        dates = [date(2026, 8, d) for d in range(27, 32)] + [date(2026, 9, 1)]
        budget.consume()
        stats_raw = await pm.get_full_adv_stat(adv_ids, dates)
        fullstats = _flatten_fullstats(list(stats_raw or []))
        return orders_res.rows, campaigns, fullstats, len(fullstats), len(adv_ids)
    finally:
        await httpx.shutdown()
        await redis_raw.aclose()


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--output-dir", default=".tmp/a1_iteration_06_aggr_design")
    args = ap.parse_args(argv)
    root = Path(args.output_dir).resolve()
    root.mkdir(parents=True, exist_ok=True)
    _bootstrap()
    pg = _load_pg(root)

    async def _run() -> dict[str, Any]:
        orders, campaigns, fullstats, fs_rows, fs_adv = await fetch_data(root)
        checked = datetime.now(MSK)
        payload = build(
            checked, pg, orders, fullstats, campaigns,
            fullstats_meta={"row_count": fs_rows, "adv_ids_requested": fs_adv},
        )
        pkg = root / PACKAGE
        pkg.mkdir(parents=True, exist_ok=True)
        (pkg / f"{PACKAGE}.json").write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
        cu = payload.get("CANDIDATE_UNIVERSE", [])
        if cu:
            flat_cols = list(cu[0].keys())
            _write_csv(pkg / "CANDIDATE_UNIVERSE.csv", cu, flat_cols)
        ps = payload.get("PRIMARY_MATCHED_SET", [])
        if ps:
            rows = []
            for p in ps:
                rows.append({**p, **p.get("randomization", {})})
            _write_csv(pkg / "PRIMARY_MATCHED_SET.csv", rows, list(rows[0].keys()))
        payload["CSV_DIR"] = str(pkg.resolve())
        return payload

    out = asyncio.run(_run())
    # trim large nested for stdout
    summary = {k: v for k, v in out.items() if k != "CANDIDATE_UNIVERSE"}
    summary["CANDIDATE_UNIVERSE_COUNT"] = len(out.get("CANDIDATE_UNIVERSE", []))
    print(json.dumps(summary, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
