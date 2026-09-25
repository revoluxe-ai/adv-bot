"""READ_ONLY: client management scope reconciliation (WB + PG + economics).

Сверяет переданный список nmID с фактическими WB-кампаниями, PG AdvSetting,
bot/V3 признаками, spend-окнами и фактической экономикой SKU. Без production writes.
"""

from __future__ import annotations

import argparse
import ast
import csv
import json
import os
import re
from collections import Counter, defaultdict
from datetime import date, datetime, timedelta, timezone
from pathlib import Path
from typing import Any
from zoneinfo import ZoneInfo

from scripts import a1_current_performance_drr_snapshot as perf
from scripts import a1_promo_adjusted_drr_collect as promo
from scripts import ch_a1_evidence as evidence
from scripts.wb_a1_associated_conversions import _read_float, _read_int

SHOP_ID = "5586b2ff-449c-4151-9518-60f46d32b7d9"
WB_CABINET_ID = 573
TARGET_NMIDS = (
    143023475,
    751657528,
    234375724,
    214754056,
    1256595631,
    266109990,
)
MSK = ZoneInfo("Europe/Moscow")
WB_STATUS = {4: "READY", 7: "DONE", 8: "REFUSED", 9: "ACTIVE", 11: "PAUSED"}

EXT_PG_COLS = (
    "id",
    "adv_id",
    "_search_adv_id",
    "type",
    "name",
    "nmids",
    "active_status",
    "bot_active",
    "automatic_version",
    "aggressiveness",
    "plan_for_sales_for_day",
    "target_price_for_order",
    "max_price_for_order",
    "auto_budget_watchdog_enabled",
    "use_common_budget",
    "common_budget_daily_limit",
    "individual_keywords_target_place_mode",
    "auto_update_target_place",
    "target_position_mode",
    "strategy",
    "auto_update_strategy",
    "rec_system_mode",
)


def _pg_db() -> str:
    return os.environ.get("POSTGRES_DBNAME") or "adv_updater"


def _patch_scope() -> None:
    """Переиспользовать A1 performance pipeline для кабинета 573."""
    evidence.SHOP_ID = SHOP_ID
    promo.SHOP_ID = SHOP_ID
    perf.SHOP_ID = SHOP_ID
    promo.WB_CABINET_ID_EXPECTED = WB_CABINET_ID


def _msk_now() -> datetime:
    return datetime.now(timezone.utc).astimezone(MSK)


def _parse_nmids(raw: str) -> set[int]:
    try:
        val = ast.literal_eval(raw.replace("null", "None"))
        if isinstance(val, list):
            return {int(x) for x in val}
    except (ValueError, SyntaxError):
        pass
    return {int(x) for x in re.findall(r"\d+", raw or "")}


def _load_extended_pg(root: Path) -> list[dict[str, str]]:
    """Дополнительный PG snapshot с control-полями для bot reconciliation."""
    sql_dir = root / "sql"
    staging = root / "staging"
    staging.mkdir(parents=True, exist_ok=True)
    path = staging / "advsetting_extended.csv"
    cols = ", ".join(EXT_PG_COLS)
    st = evidence.run_pg_query(
        _pg_db(),
        f"SELECT {cols} FROM public.advsetting WHERE wb_cabinet_id = {WB_CABINET_ID}",
        path,
        sql_dir / "pg_advsetting_extended.sql",
        csv_output=True,
    )
    if not st.get("success"):
        return []
    with path.open(encoding="utf-8", newline="") as handle:
        return list(csv.DictReader(handle))


def _load_keyword_stats(root: Path, setting_ids: set[int]) -> dict[int, dict[str, Any]]:
    if not setting_ids:
        return {}
    sql_dir = root / "sql"
    staging = root / "staging"
    path = staging / "keywordsetting_scope.csv"
    ids_sql = ", ".join(str(i) for i in sorted(setting_ids))
    st = evidence.run_pg_query(
        _pg_db(),
        (
            "SELECT adv_setting_id, hard_status, strategy_mode::text AS strategy_mode "
            f"FROM public.keywordsetting WHERE adv_setting_id IN ({ids_sql})"
        ),
        path,
        sql_dir / "pg_keywordsetting_scope.sql",
        csv_output=True,
    )
    if not st.get("success"):
        return {}
    by_id: dict[int, dict[str, Any]] = defaultdict(
        lambda: {"total": 0, "OFF": 0, "MIN_CPA": 0, "OPTIMUM": 0, "MAX_CONVERSION": 0, "active_count": 0}
    )
    with path.open(encoding="utf-8", newline="") as handle:
        for row in csv.DictReader(handle):
            sid = int(row["adv_setting_id"])
            by_id[sid]["total"] += 1
            mode = (row.get("strategy_mode") or "").upper()
            hs = str(row.get("hard_status") or "")
            if mode in by_id[sid]:
                by_id[sid][mode] += 1
            if hs not in ("", "0", "false", "False"):
                by_id[sid]["active_count"] += 1
    return dict(by_id)


def _campaign_nmids(c: dict[str, Any]) -> set[int]:
    out: set[int] = set()
    for ns in c.get("nm_settings") or c.get("nmSettings") or []:
        if isinstance(ns, dict):
            nid = _read_int(ns, "nm_id", "nmId", "nmID")
            if nid:
                out.add(nid)
    return out


def _wb_state(status: int | None) -> str:
    if status in (9, 11):
        return "ACTIVE" if status == 9 else "PAUSED"
    if status == 7:
        return "DONE"
    if status == 4:
        return "READY"
    return "OTHER"


def _owner(pg: dict[str, str] | None, wb_status: int | None) -> str:
    if pg and str(pg.get("bot_active")).lower() in ("true", "t", "1"):
        return "BOT_OWNED"
    return "MANUAL"


def _has_v3(pg: dict[str, str] | None) -> bool:
    if not pg:
        return False
    return str(pg.get("automatic_version") or "").strip() in ("3", "V3", "v3")


def _sku_orders(orders_raw: list[dict[str, Any]], nmid: int, start: date, end: date) -> tuple[int, float]:
    orders = gmv = 0
    for row in orders_raw:
        if _read_int(row, "nmId", "nmID") != nmid:
            continue
        raw = str(row.get("date") or row.get("lastChangeDate") or "")[:10]
        try:
            d = date.fromisoformat(raw)
        except ValueError:
            continue
        if d < start or d > end:
            continue
        if str(row.get("isCancel")).lower() in ("true", "1"):
            continue
        orders += 1
        gmv += float(_read_float(row, "finishedPrice", "priceWithDisc") or 0)
    return orders, round(gmv, 2)


def _build_report(root: Path, perf_summary: dict[str, Any]) -> dict[str, Any]:
    closed_end = date.fromisoformat(perf_summary["LAST_FULLY_CLOSED_DAY"])
    w3 = (closed_end - timedelta(days=2), closed_end)
    w7 = (closed_end - timedelta(days=6), closed_end)
    today = _msk_now().date()

    campaigns: list[dict[str, Any]] = []
    raw_path = root / "raw" / "campaigns_v2.jsonl"
    if raw_path.is_file():
        for line in raw_path.read_text(encoding="utf-8").splitlines():
            if line.strip():
                campaigns.append(json.loads(line))

    orders_raw: list[dict[str, Any]] = []
    ord_path = root / "raw" / "supplier_orders_raw.jsonl"
    if ord_path.is_file():
        for line in ord_path.read_text(encoding="utf-8").splitlines():
            if line.strip():
                orders_raw.append(json.loads(line))

    ext_pg = _load_extended_pg(root)
    pg_by_adv: dict[str, dict[str, str]] = {}
    pg_by_id: dict[int, dict[str, str]] = {}
    for row in ext_pg:
        if row.get("adv_id"):
            pg_by_adv[str(row["adv_id"])] = row
        if row.get("id"):
            pg_by_id[int(row["id"])] = row

    kw_stats = _load_keyword_stats(root, set(pg_by_id))

    spend_by_adv: dict[int, dict[str, float]] = defaultdict(lambda: {"today": 0.0, "d3": 0.0, "d7": 0.0})
    fs_path = root / "raw" / "fullstats_v3_raw.jsonl"
    if fs_path.is_file():
        for line in fs_path.read_text(encoding="utf-8").splitlines():
            if not line.strip():
                continue
            st = json.loads(line)
            aid = _read_int(st, "advertId", "advert_id", "id")
            if not aid:
                continue
            for day_row in st.get("days") or []:
                ds = str(day_row.get("date") or "")[:10]
                try:
                    d = date.fromisoformat(ds)
                except ValueError:
                    continue
                spend = float(_read_float(day_row, "sum") or 0)
                if d == today:
                    spend_by_adv[aid]["today"] += spend
                if w3[0] <= d <= w3[1]:
                    spend_by_adv[aid]["d3"] += spend
                if w7[0] <= d <= w7[1]:
                    spend_by_adv[aid]["d7"] += spend

    per_nmid: dict[int, Any] = {}
    scope_gap: list[dict[str, Any]] = []
    bot_connected: list[int] = []
    not_connected: list[int] = []

    for nmid in TARGET_NMIDS:
        touching = [c for c in campaigns if nmid in _campaign_nmids(c)]
        camp_rows = []
        spend_3d = spend_7d = 0.0
        bot_campaigns: list[int] = []
        manual_campaigns: list[int] = []
        active_spenders: list[int] = []
        adv_settings: list[dict[str, Any]] = []

        for c in touching:
            aid = _read_int(c, "advertId", "id")
            st = _read_int(c, "status")
            pg = pg_by_adv.get(str(aid)) if aid else None
            sp = spend_by_adv.get(aid or 0, {})
            spend_3d += sp.get("d3", 0)
            spend_7d += sp.get("d7", 0)
            if sp.get("d7", 0) > 0 or sp.get("today", 0) > 0:
                active_spenders.append(aid)
            own = _owner(pg, st)
            if own == "BOT_OWNED":
                bot_campaigns.append(aid)
            else:
                manual_campaigns.append(aid)
            camp_rows.append(
                {
                    "adv_id": aid,
                    "wb_status": st,
                    "wb_status_label": WB_STATUS.get(st or 0, str(st)),
                    "wb_state": _wb_state(st),
                    "campaign_type": c.get("type") or c.get("advertType"),
                    "payment_model": c.get("payment_type") or c.get("paymentType"),
                    "placements": c.get("placement") or c.get("placements"),
                    "spend_today": round(sp.get("today", 0), 2),
                    "spend_3d": round(sp.get("d3", 0), 2),
                    "spend_7d": round(sp.get("d7", 0), 2),
                    "control_owner": own,
                    "adv_setting_id": pg.get("id") if pg else None,
                    "search_adv_id": pg.get("_search_adv_id") if pg else None,
                    "automatic_version": pg.get("automatic_version") if pg else None,
                    "bot_active": pg.get("bot_active") if pg else None,
                }
            )

        pg_rows = [r for r in ext_pg if nmid in _parse_nmids(r.get("nmids") or "")]
        has_adv = "YES" if pg_rows else "NO"
        has_v3 = "YES" if any(_has_v3(r) for r in pg_rows) else "NO"
        if has_adv == "YES" and any(str(r.get("bot_active")).lower() in ("true", "t", "1") for r in pg_rows):
            bot_connected.append(nmid)
        else:
            not_connected.append(nmid)

        for pr in pg_rows:
            sid = int(pr["id"])
            adv_settings.append(
                {
                    **{k: pr.get(k) for k in EXT_PG_COLS},
                    "keywordsetting": kw_stats.get(sid, {}),
                    "has_v3": _has_v3(pr),
                }
            )

        o3, g3 = _sku_orders(orders_raw, nmid, w3[0], w3[1])
        o7, g7 = _sku_orders(orders_raw, nmid, w7[0], w7[1])
        cpo7 = round(spend_7d / o7, 2) if o7 else "N/A"
        drr7 = round(100 * spend_7d / g7, 2) if g7 else "N/A"

        has_active = any(r["wb_state"] == "ACTIVE" for r in camp_rows)
        has_wb = "YES" if camp_rows else "NO"
        bot_active_any = "YES" if any(str(r.get("bot_active")).lower() in ("true", "t", "1") for r in pg_rows) else "NO"

        per_nmid[nmid] = {
            "campaigns": camp_rows,
            "HAS_ADV_SETTING": has_adv,
            "HAS_V3": has_v3,
            "BOT_CONTROLLED_CAMPAIGNS": bot_campaigns,
            "MANUAL_CAMPAIGNS": manual_campaigns,
            "CURRENT_ACTIVE_SPENDERS": active_spenders,
            "adv_settings": adv_settings,
            "factual_economics": {
                "orders_3d": o3,
                "orders_7d": o7,
                "gmv_3d": g3,
                "gmv_7d": g7,
                "gross_ad_spend_3d": round(spend_3d, 2),
                "gross_ad_spend_7d": round(spend_7d, 2),
                "sku_cpo_7d": cpo7,
                "sku_drr_7d_pct": drr7,
            },
        }

        scope_gap.append(
            {
                "NMID": nmid,
                "CLIENT_SCOPE": "YES",
                "HAS_WB_CAMPAIGN": has_wb,
                "HAS_ACTIVE_CAMPAIGN": "YES" if has_active else "NO",
                "HAS_ADV_SETTING": has_adv,
                "BOT_ACTIVE": bot_active_any,
                "V3": has_v3,
                "CURRENT_CONTROL_OWNER": "BOT" if bot_active_any == "YES" else "MANUAL",
                "CURRENT_STATE": "ACTIVE_SPEND" if active_spenders else ("PAUSED_OR_IDLE" if has_wb else "NO_CAMPAIGN"),
                "SHOULD_BE_MANAGED_NOW": "TBD_OPERATOR",
                "GAP": "NONE" if has_adv == "YES" and has_wb == "YES" else "SCOPE_OR_PG_GAP",
            }
        )

    shop_spend_rank: list[dict[str, Any]] = []
    for aid, sp in sorted(spend_by_adv.items(), key=lambda x: -x[1]["d7"]):
        if sp["d7"] <= 0 and sp["today"] <= 0:
            continue
        pg = pg_by_adv.get(str(aid), {})
        nm = sorted(_parse_nmids(pg.get("nmids") or ""))[:5]
        in_scope = any(n in TARGET_NMIDS for n in nm)
        shop_spend_rank.append(
            {
                "adv_id": aid,
                "nmids_sample": nm,
                "in_client_scope": in_scope,
                "spend_today": round(sp["today"], 2),
                "spend_3d": round(sp["d3"], 2),
                "spend_7d": round(sp["d7"], 2),
                "bot_active": pg.get("bot_active"),
            }
        )

    store_7d = (perf_summary.get("WINDOWS") or {}).get("CURRENT_7D") or {}
    store_drr = store_7d.get("gross_drr")

    return {
        "CHECKED_AT_MSK": _msk_now().isoformat(),
        "SHOP_ID": SHOP_ID,
        "WB_CABINET_ID": WB_CABINET_ID,
        "MANAGEMENT_SCOPE": list(TARGET_NMIDS),
        "BOT_COVERAGE": {
            "TOTAL_MANAGED_SCOPE_SKUS": len(TARGET_NMIDS),
            "SKUS_CONNECTED_TO_BOT": bot_connected,
            "SKUS_NOT_CONNECTED_TO_BOT": not_connected,
        },
        "STORE_CONTEXT": {
            "target_store_drr_pct": 10,
            "current_7d_store_drr_pct": round(float(store_drr) * 100, 4) if store_drr else "GAP",
            "LAST_FULLY_CLOSED_DAY": perf_summary.get("LAST_FULLY_CLOSED_DAY"),
        },
        "PER_NMID": per_nmid,
        "SCOPE_GAP_TABLE": scope_gap,
        "ACTIVE_STORE_AD_SPEND_RANK_7D": shop_spend_rank[:40],
        "CRITICAL_GAPS": perf_summary.get("CRITICAL_GAPS") or [],
        "OPERATIONAL_RECONCILE": _operational_notes(per_nmid),
        "ALL_PRODUCTION_WRITES": 0,
    }


def _operational_notes(per_nmid: dict[int, Any]) -> dict[str, Any]:
    """Флаги расхождений с известными операционными решениями (read-only)."""

    def _pg_flag(nmid: int, field: str) -> Any:
        rows = per_nmid.get(nmid, {}).get("adv_settings") or []
        return rows[0].get(field) if rows else "GAP"

    return {
        "143023475": {
            "CURRENT_FACT": {
                "individual_keywords_target_place_mode": _pg_flag(143023475, "individual_keywords_target_place_mode"),
                "common_budget_daily_limit": _pg_flag(143023475, "common_budget_daily_limit"),
                "bot_active": _pg_flag(143023475, "bot_active"),
                "HAS_V3": per_nmid.get(143023475, {}).get("HAS_V3"),
            },
            "INTENDED_STATE": "bot/V3; individual_keywords_target_place_mode=TRUE; common_budget=1000",
            "DISCREPANCY": (
                "YES"
                if str(_pg_flag(143023475, "individual_keywords_target_place_mode")).lower()
                in ("false", "f", "0", "")
                else "CHECK_PG"
            ),
            "NEXT_ACTION": "INVESTIGATE PG vs Excel; no auto-write",
        },
        "266109990": {
            "CURRENT_FACT": {
                "individual_keywords_target_place_mode": _pg_flag(266109990, "individual_keywords_target_place_mode"),
                "common_budget_daily_limit": _pg_flag(266109990, "common_budget_daily_limit"),
            },
            "INTENDED_STATE": "bot/V3; individual=TRUE; common_budget=150",
            "DISCREPANCY": "COMPARE_TO_EXCEL",
            "NEXT_ACTION": "CONFIRM runtime PG matches Excel",
        },
        "751657528": {
            "CURRENT_FACT": {
                "active_spenders": per_nmid.get(751657528, {}).get("CURRENT_ACTIVE_SPENDERS"),
                "campaigns": [c.get("adv_id") for c in per_nmid.get(751657528, {}).get("campaigns") or []],
            },
            "INTENDED_STATE": "Client approved re-test under store 10% DRR; do not auto-start 39924731",
            "DISCREPANCY": "POLICY",
            "NEXT_ACTION": "MANUAL_CPC_TEST on best contour (see camp rows); no execute",
        },
        "234375724": {
            "CURRENT_FACT": {"campaigns": per_nmid.get(234375724, {}).get("campaigns")},
            "INTENDED_STATE": "Reuse strong economics; evaluate CPC 38636700",
            "DISCREPANCY": "TBD",
            "NEXT_ACTION": "CONNECT_TO_BOT or MANUAL_CPC_TEST after contour pick",
        },
        "214754056": {
            "CURRENT_FACT": per_nmid.get(214754056, {}).get("factual_economics"),
            "INTENDED_STATE": "HOLD if demand thin",
            "DISCREPANCY": "TBD",
            "NEXT_ACTION": "BOT_HOLD",
        },
        "1256595631": {
            "CURRENT_FACT": {
                "active_spenders": per_nmid.get(1256595631, {}).get("CURRENT_ACTIVE_SPENDERS"),
            },
            "INTENDED_STATE": "KEEP_OFF independent red; pink via glue",
            "DISCREPANCY": "POLICY",
            "NEXT_ACTION": "KEEP_OFF unless glue strategy revived",
        },
        "CONTROL_PLAN": [
            "1) Close PG gaps for bot-connected SKUs (143023475 individual mode).",
            "2) Rank shop spenders outside scope — resolve manual conflicts.",
            "3) Bounded re-test 751657528 under store DRR headroom (no auto-start).",
            "4) Reconnect 234375724 best campaign to bot if PG row exists.",
            "EXECUTE NOTHING.",
        ],
    }


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output-dir", required=True)
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    _patch_scope()
    out = Path(args.output_dir)
    perf_summary = perf.run_collect(out)
    report = _build_report(out, perf_summary)
    primary = out / "management_scope_reconcile.json"
    primary.write_text(json.dumps(report, ensure_ascii=False, indent=2, default=str), encoding="utf-8")
    print(f"PRIMARY_ARTIFACT={primary}")
    print("ARTIFACT_CLASS=CLIENT_MANAGEMENT_SCOPE_RECONCILE")
    print("ALL_PRODUCTION_WRITES=0")


if __name__ == "__main__":
    main()
