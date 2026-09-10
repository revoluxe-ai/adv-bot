"""READ_ONLY: post-import V3 runtime verification (PG + Redis V3 caches + WB live).

Проверка AdvSetting, live WB по auto/search adv_id, последний V3 tick report,
keyword PG distribution и сопоставление с Redis audit. Без PG/Redis/WB writes.
"""

from __future__ import annotations

import argparse
import asyncio
import json
import os
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from zoneinfo import ZoneInfo

import dotenv

dotenv.load_dotenv()

from scripts.set_path import add_project_root_to_path

add_project_root_to_path()

MSK = ZoneInfo("Europe/Moscow")

PG_FIELDS = (
    "id",
    "adv_id",
    "_search_adv_id",
    "automatic_version",
    "bot_active",
    "active_status",
    "aggressiveness",
    "plan_for_sales_for_day",
    "target_price_for_order",
    "max_price_for_order",
    "strategy",
    "auto_update_strategy",
    "auto_budget_watchdog_enabled",
    "use_common_budget",
    "common_budget_daily_limit",
    "auto_budget_daily_limit",
    "search_auto_budget_daily_limit",
    "rec_system_mode",
    "keyword_calibration_max_step",
    "last_update",
    "name",
    "nmids",
)


def _msk_now() -> datetime:
    return datetime.now(timezone.utc).astimezone(MSK)


def _norm_bool(val: Any) -> str:
    return str(val).strip().lower() in ("true", "t", "1", "yes")


def _norm_num(val: Any, expected: Any) -> bool:
    try:
        return float(val) == float(expected)
    except (TypeError, ValueError):
        return str(val) == str(expected)


def _config_match(pg: dict[str, Any], expected: dict[str, Any]) -> tuple[str, list[str]]:
    mismatches: list[str] = []
    for key, exp in expected.items():
        got = pg.get(key)
        if key in (
            "bot_active",
            "auto_budget_watchdog_enabled",
            "use_common_budget",
        ):
            ok = _norm_bool(got) == _norm_bool(exp)
        else:
            ok = _norm_num(got, exp)
        if not ok:
            mismatches.append(f"{key}: got={got!r} expected={exp!r}")
    return ("PASS" if not mismatches else "FAIL"), mismatches


async def _pg_bundle(adv_setting_id: int) -> dict[str, Any]:
    import asyncpg

    conn = await asyncpg.connect(
        host=os.environ["POSTGRES_MASTER_HOST"],
        port=int(os.environ.get("POSTGRES_PORT", 5432)),
        user=os.environ["POSTGRES_USER"],
        password=os.environ["POSTGRES_PASSWORD"],
        database=os.environ.get("POSTGRES_DBNAME", "adv_updater"),
    )
    cols = ", ".join(PG_FIELDS)
    row = await conn.fetchrow(
        f"SELECT {cols} FROM advsetting WHERE id = $1",
        adv_setting_id,
    )
    kws = await conn.fetch(
        """
        SELECT id, text, hard_status, strategy_mode::text AS strategy_mode,
               target_place, relevant, updated_at
        FROM keywordsetting
        WHERE adv_setting_id = $1
        ORDER BY id
        """,
        adv_setting_id,
    )
    await conn.close()
    adv = dict(row) if row else {}
    keywords = [dict(r) for r in kws]
    return {
        "adv": adv,
        "keyword_count": len(keywords),
        "strategy_mode_distribution": dict(Counter(k["strategy_mode"] for k in keywords)),
        "hard_status_distribution": dict(Counter(str(k["hard_status"]) for k in keywords)),
        "keywords_sample": keywords[:5],
    }


async def _redis_json(key: str) -> Any:
    import redis.asyncio as redis

    r = redis.Redis(
        host=os.environ.get("REDIS_HOST", "redis-service.prod-adv-bot.svc.cluster.local"),
        port=int(os.environ.get("REDIS_PORT", 6379)),
        decode_responses=True,
    )
    val = await r.get(key)
    await r.aclose()
    if not val:
        return None
    try:
        return json.loads(val)
    except json.JSONDecodeError:
        return val


async def _redis_v3_caches(auto_adv_id: int) -> dict[str, Any]:
    from app.modules.common_slaves.wildberries.models import AdvSetting
    from app.modules.shop_runner.service_manager.services.auto_updater_v3.keyword_decision_trace.redis import (
        KeywordDecisionTraceRedisCache,
    )
    from app.modules.shop_runner.service_manager.services.auto_updater_v3.v3_keyword_changes_report.redis import (
        V3KeywordChangesRedisCache,
    )
    from app.modules.shop_runner.service_manager.services.auto_updater_v3.v3_tick_report_redis import (
        V3TickReportRedisCache,
    )

    adv = AdvSetting()
    adv.adv_id = auto_adv_id
    tick = await V3TickReportRedisCache(adv).get()
    kw = await V3KeywordChangesRedisCache(adv).get()
    trace = await KeywordDecisionTraceRedisCache(adv).get()
    return {
        "V3TickReport": tick.model_dump(mode="json") if tick else None,
        "V3KeywordChanges": kw.model_dump(mode="json") if kw else None,
        "KeywordDecisionTrace": trace.model_dump(mode="json") if trace else None,
    }


def _camp_dict(item: Any) -> dict[str, Any]:
    return item.to_dict() if hasattr(item, "to_dict") else dict(item)


def _nm_bids(campaign: dict[str, Any], nmid: int) -> dict[str, Any]:
    for ns in campaign.get("nm_settings") or []:
        if not isinstance(ns, dict):
            continue
        if int(ns.get("nm_id") or 0) != nmid:
            continue
        bk = ns.get("bids_kopecks") or {}
        return {
            "search_rub": round(int(bk.get("search") or 0) / 100, 2),
            "rec_rub": round(int(bk.get("recommendations") or 0) / 100, 2),
        }
    return {}


def _wb_status_label(status: Any) -> str:
    mapping = {9: "ACTIVE", 11: "PAUSE", 7: "DONE", 4: "READY"}
    try:
        return mapping.get(int(status), str(status))
    except (TypeError, ValueError):
        return str(status)


async def _wb_live(
    shop_id: str, auto_adv_id: int, search_adv_id: int, nmid: int
) -> dict[str, Any]:
    from app.core.di.app_container import AppContainer
    from app.core.di.di_manager import DIManager

    today = _msk_now().date()
    out: dict[str, Any] = {}
    async with await DIManager.create(AppContainer) as container:
        pm = (
            container.module_resources.wb_manager_hub_factory_container.wb_manager_hub_factory()
            .get_wb_manager_hub(shop_id)
            .wb_data_manager.promotion_manager
        )
        for adv_id in (auto_adv_id, search_adv_id):
            items = await pm.get_adverts_v2_by_ids([adv_id])
            c = _camp_dict(items[0]) if items else {}
            budget: Any = None
            try:
                bal = await pm.get_campaign_budget(adv_id)
                budget = getattr(bal, "total", None)
            except Exception as exc:  # noqa: BLE001
                budget = {"error": type(exc).__name__}
            spend_today: Any = None
            stats: Any = None
            try:
                rows = list(await pm.get_full_adv_stat([adv_id], [today]) or [])
                spend_today = round(
                    sum(float(getattr(r, "sum", 0) or 0) for r in rows), 2
                )
                stats = {
                    "impressions": sum(int(getattr(r, "views", 0) or 0) for r in rows),
                    "clicks": sum(int(getattr(r, "clicks", 0) or 0) for r in rows),
                }
            except Exception as exc:  # noqa: BLE001
                spend_today = {"error": type(exc).__name__}
            settings = c.get("settings") or {}
            out[str(adv_id)] = {
                "wb_status": c.get("status"),
                "wb_status_label": _wb_status_label(c.get("status")),
                "bid_type": c.get("bid_type"),
                "payment_type": settings.get("payment_type") or c.get("payment_type"),
                "placements": {
                    "search": settings.get("placement_search"),
                    "recommendations": settings.get("placement_recommendations"),
                },
                "bids_for_nmid": _nm_bids(c, nmid),
                "budget_rub": budget,
                "spend_today": spend_today,
                "stats_today": stats,
            }
    return out


def _tick_in_window(tick_at: datetime | None, start: datetime, end: datetime) -> bool:
    if tick_at is None:
        return False
    if tick_at.tzinfo is None:
        tick_at = tick_at.replace(tzinfo=MSK)
    t = tick_at.astimezone(MSK)
    return start <= t <= end


def _keyword_persistence(
    pg_kw: dict[str, Any], redis_kw_changes: dict[str, Any] | None
) -> tuple[str, list[str]]:
    """Сравнить последний Redis audit с PG; не считать Redis источником истины."""
    gaps: list[str] = []
    if not redis_kw_changes:
        return "UNRESOLVED", ["no V3KeywordChanges Redis snapshot"]
    applied = redis_kw_changes.get("applied_actions") or []
    if not applied:
        return "PASS", ["no applied_actions in latest audit (nothing durable expected)"]
    # Если audit сообщает applied, но PG не отражает — GAP (грубая проверка по count).
    pg_modes = pg_kw.get("strategy_mode_distribution") or {}
    off_count = int(pg_modes.get("OFF", 0) or 0)
    planned_off = sum(
        1
        for a in applied
        if isinstance(a, dict) and str(a.get("action_type", "")).upper() in ("OFF", "FORCE_OFF")
    )
    if planned_off > 0 and off_count == 0:
        gaps.append("redis reports OFF applies but PG has zero OFF strategy_mode")
    return ("GAP" if gaps else "PASS"), gaps


def _summarize_v3(tick: dict[str, Any] | None) -> dict[str, Any]:
    if not tick:
        return {}
    return {
        "tick_at": tick.get("tick_at"),
        "sales_state": tick.get("sales_state"),
        "fact_cpa": tick.get("fact_cpa"),
        "resolve": tick.get("resolve"),
        "max_pay_for_order": tick.get("max_pay_for_order"),
        "aggression_before": tick.get("aggression_score_before"),
        "aggression_after": tick.get("aggression_score_after"),
        "net_up": tick.get("net_up"),
        "net_down": tick.get("net_down"),
        "net_force_off": tick.get("net_force_off"),
        "net_on": tick.get("net_on"),
        "calibration_effective_steps": tick.get("calibration_effective_steps"),
        "calibration_applied_steps": tick.get("calibration_applied_steps"),
        "calibration_direct": tick.get("calibration_direct"),
        "hard_status_counts": tick.get("hard_status_counts"),
        "phases": tick.get("phases"),
    }


async def _collect(args: argparse.Namespace) -> dict[str, Any]:
    import_start = datetime.fromisoformat(args.import_window_start).replace(tzinfo=MSK)
    import_end = datetime.fromisoformat(args.import_window_end).replace(tzinfo=MSK)
    expected = json.loads(args.expected_config_json)

    checked = _msk_now()
    pg = await _pg_bundle(args.adv_setting_id)
    adv_row = pg.get("adv") or {}

    match_status, mismatches = _config_match(adv_row, expected)

    redis_v3: dict[str, Any]
    try:
        redis_v3 = await _redis_v3_caches(args.auto_adv_id)
    except Exception as exc:  # noqa: BLE001
        redis_v3 = {"error": str(exc)[:500]}

    extra_keys = [
        f"ChangePlanFact:{args.auto_adv_id}",
        f"stats_freshness_state:shop:{args.shop_id}:adv:{args.adv_setting_id}",
        f"last:fact:{args.shop_id}:{args.auto_adv_id}",
        f"last:fact:{args.shop_id}:{args.search_adv_id}",
        f"zero:fact:{args.shop_id}:{args.auto_adv_id}:{checked.date().isoformat()}",
    ]
    redis_extra: dict[str, Any] = {}
    for k in extra_keys:
        redis_extra[k] = await _redis_json(k)

    wb: dict[str, Any]
    try:
        wb = await _wb_live(
            args.shop_id, args.auto_adv_id, args.search_adv_id, args.nmid
        )
    except Exception as exc:  # noqa: BLE001
        wb = {"error": str(exc)[:500]}

    tick_raw = redis_v3.get("V3TickReport") if isinstance(redis_v3, dict) else None
    tick_at_str = tick_raw.get("tick_at") if isinstance(tick_raw, dict) else None
    tick_at: datetime | None = None
    if tick_at_str:
        tick_at = datetime.fromisoformat(str(tick_at_str).replace("Z", "+00:00"))

    kw_changes = (
        redis_v3.get("V3KeywordChanges") if isinstance(redis_v3, dict) else None
    )
    persist_status, persist_notes = _keyword_persistence(pg, kw_changes)

    combined_spend = None
    cpf = redis_extra.get(f"ChangePlanFact:{args.auto_adv_id}")
    if isinstance(cpf, dict):
        combined_spend = cpf.get("combined_spend") or cpf.get("combined_spend_rub")

    report = {
        "checked_at_msk": checked.isoformat(),
        "shop_id": args.shop_id,
        "nmid": args.nmid,
        "adv_setting_id": args.adv_setting_id,
        "auto_adv_id": args.auto_adv_id,
        "search_adv_id": args.search_adv_id,
        "import_window_msk": {
            "start": import_start.isoformat(),
            "end": import_end.isoformat(),
        },
        "expected_config": expected,
        "pg_config": {k: adv_row.get(k) for k in PG_FIELDS if k in adv_row},
        "automatic_version": adv_row.get("automatic_version"),
        "config_match": match_status,
        "config_mismatches": mismatches,
        "keyword_pg_state": {
            "count": pg.get("keyword_count"),
            "strategy_mode_distribution": pg.get("strategy_mode_distribution"),
            "hard_status_distribution": pg.get("hard_status_distribution"),
        },
        "wb_live": wb,
        "first_v3_tick_in_window": (
            tick_at.isoformat() if tick_at and _tick_in_window(tick_at, import_start, import_end) else None
        ),
        "latest_v3_tick": tick_at.isoformat() if tick_at else None,
        "v3_state": _summarize_v3(tick_raw if isinstance(tick_raw, dict) else None),
        "v3_keyword_changes": kw_changes,
        "keyword_persistence": persist_status,
        "keyword_persistence_notes": persist_notes,
        "redis_extra": redis_extra,
        "common_budget_state": {
            "use_common_budget": adv_row.get("use_common_budget"),
            "common_budget_daily_limit": adv_row.get("common_budget_daily_limit"),
            "combined_spend_redis": combined_spend,
        },
        "activity_changes": {
            "note": "pause/start/top-up from activity-control require shop-runner logs if not in Redis extras",
            "change_plan_fact": cpf,
        },
        "errors": [],
        "open_gaps": [
            "first_v3_tick_in_window only set if latest Redis tick falls inside import window; historical ticks need log scrape",
        ],
        "all_production_writes": 0,
    }
    if isinstance(redis_v3, dict) and redis_v3.get("error"):
        report["errors"].append(f"redis_v3: {redis_v3['error']}")
    if wb.get("error"):
        report["errors"].append(f"wb_live: {wb['error']}")
    return report


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    default_expected = json.dumps(
        {
            "bot_active": True,
            "aggressiveness": 1,
            "plan_for_sales_for_day": 1,
            "target_price_for_order": 45,
            "max_price_for_order": 55,
            "auto_budget_watchdog_enabled": True,
            "use_common_budget": True,
            "common_budget_daily_limit": 60,
            "auto_budget_daily_limit": 0,
            "search_auto_budget_daily_limit": 0,
        },
        ensure_ascii=False,
    )
    p = argparse.ArgumentParser(description="V3 post-import verify (READ_ONLY)")
    p.add_argument("--shop-id", required=True)
    p.add_argument("--nmid", type=int, required=True)
    p.add_argument("--adv-setting-id", type=int, required=True)
    p.add_argument("--auto-adv-id", type=int, required=True)
    p.add_argument("--search-adv-id", type=int, required=True)
    p.add_argument(
        "--import-window-start",
        default="2026-09-10T21:41:00",
        help="MSK naive ISO start",
    )
    p.add_argument(
        "--import-window-end",
        default="2026-09-10T21:55:00",
        help="MSK naive ISO end",
    )
    p.add_argument("--expected-config-json", default=default_expected)
    p.add_argument("--output-dir", type=Path, required=True)
    return p.parse_args(argv)


def main() -> None:
    args = parse_args()
    report = asyncio.run(_collect(args))
    args.output_dir.mkdir(parents=True, exist_ok=True)
    primary = args.output_dir / "v3_post_import_verify.json"
    primary.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    manifest = {
        "primary": primary.name,
        "collector": "scripts/a1_v3_post_import_verify_collect.py",
        "shop_id": report.get("shop_id"),
        "adv_setting_id": report.get("adv_setting_id"),
    }
    (args.output_dir / "MANIFEST.json").write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    print(json.dumps(report, ensure_ascii=False))
    raise SystemExit(0)


if __name__ == "__main__":
    main()
