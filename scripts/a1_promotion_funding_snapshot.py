"""READ_ONLY snapshot: WB Promotion central funds + per-campaign budgets (A1).

GET /adv/v1/balance и GET /adv/v1/budget для active campaigns;
auto-topup state из PG advsetting + cluster env (bot watchdog).
Никаких writes.
"""

from __future__ import annotations

import argparse
import asyncio
import csv
import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import dotenv

dotenv.load_dotenv()

from scripts import ch_a1_evidence as evidence

SHOP_ID = evidence.SHOP_ID
WB_CABINET_ID_EXPECTED = 401
ACTIVE_STATUSES = {9}


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


def _load_adv_settings(root: Path) -> tuple[int, list[dict[str, str]]]:
    sql_dir = root / "sql"
    staging = root / "staging"
    staging.mkdir(parents=True, exist_ok=True)
    cabinet_path = staging / "wbcabinet.csv"
    st = evidence.run_pg_query(
        _pg_database(),
        f"SELECT id, shop_id, balance, bonus FROM public.wbcabinet WHERE id = {WB_CABINET_ID_EXPECTED}",
        cabinet_path,
        sql_dir / "pg_wbcabinet.sql",
        csv_output=True,
    )
    if not st["success"]:
        raise RuntimeError(f"wbcabinet query failed: {st['stderr']}")
    wb_cabinet_id = WB_CABINET_ID_EXPECTED
    setting_path = staging / "advsetting.csv"
    st2 = evidence.run_pg_query(
        _pg_database(),
        (
            "SELECT id, adv_id, _search_adv_id, name, active_status, bot_active, "
            "auto_budget_watchdog_enabled, auto_budget_daily_limit, "
            "search_auto_budget_daily_limit, use_common_budget, "
            "common_budget_daily_limit, max_balance_adding_for_day "
            f"FROM public.advsetting WHERE wb_cabinet_id = {wb_cabinet_id}"
        ),
        setting_path,
        sql_dir / "pg_advsetting.sql",
        csv_output=True,
    )
    if not st2["success"]:
        raise RuntimeError(f"advsetting query failed: {st2['stderr']}")
    with setting_path.open(encoding="utf-8", newline="") as handle:
        rows = list(csv.DictReader(handle))
    return wb_cabinet_id, rows


def _cashbacks_to_list(raw: Any) -> list[dict[str, Any]]:
    if not raw:
        return []
    items: list[dict[str, Any]] = []
    for item in raw:
        if hasattr(item, "to_dict"):
            d = item.to_dict()
        elif isinstance(item, dict):
            d = item
        else:
            d = {
                "sum": getattr(item, "sum_", getattr(item, "sum", None)),
                "percent": getattr(item, "percent", None),
                "expiration_date": getattr(item, "expiration_date", None),
            }
        items.append(
            {
                "sum": d.get("sum", d.get("sum_")),
                "percent": d.get("percent"),
                "expiration_date": d.get("expiration_date"),
            }
        )
    return items


async def _collect_wb_funding() -> dict[str, Any]:
    from app.core.di.app_container import AppContainer
    from app.core.di.di_manager import DIManager

    async with await DIManager.create(AppContainer) as container:  # type: ignore[attr-defined]
        factory = container.module_resources.wb_manager_hub_factory_container.wb_manager_hub_factory()
        hub = factory.get_wb_manager_hub(SHOP_ID)
        pm = hub.wb_data_manager.promotion_manager
        finance = pm._client.finance_adapter

        balance_resp = await finance.get_campaign_balance()
        central = {
            "balance": getattr(balance_resp, "balance", None),
            "net": getattr(balance_resp, "net", None),
            "bonus": getattr(balance_resp, "bonus", None),
            "cashbacks": _cashbacks_to_list(getattr(balance_resp, "cashbacks", None)),
            "labels": {
                "balance": "Счёт WB Продвижение",
                "net": "Баланс WB Продвижение / взаимозачёт",
                "bonus": "Бонусы",
            },
        }

        adv_ids = list(await pm._client.promotion_count_adapter.get_cabinet_adv_ids() or [])
        campaigns_raw = list(await pm.get_adverts_v2_by_ids(adv_ids) or [])

        active_ids: list[int] = []
        campaign_meta: dict[int, dict[str, Any]] = {}
        for item in campaigns_raw:
            adv_id = int(getattr(item, "id", 0) or 0)
            status_raw = getattr(item, "status", None)
            status_val = int(
                status_raw.value if hasattr(status_raw, "value") else status_raw or 0
            )
            name = ""
            settings_block = getattr(item, "settings", None)
            if settings_block is not None:
                name = str(getattr(settings_block, "name", "") or "")
            campaign_meta[adv_id] = {"status": status_val, "name": name}
            if status_val in ACTIVE_STATUSES:
                active_ids.append(adv_id)

        budgets: list[dict[str, Any]] = []
        errors: list[str] = []
        for adv_id in sorted(active_ids):
            try:
                b = await finance.get_campaign_budget(adv_id)
                budgets.append(
                    {
                        "adv_id": adv_id,
                        "name": campaign_meta.get(adv_id, {}).get("name"),
                        "status": campaign_meta.get(adv_id, {}).get("status"),
                        "cash": getattr(b, "cash", None) if b else None,
                        "netting": getattr(b, "netting", None) if b else None,
                        "total": getattr(b, "total", None) if b else None,
                    }
                )
            except Exception as exc:  # noqa: BLE001
                errors.append(f"budget adv_id={adv_id}: {type(exc).__name__}: {exc}")

        return {
            "central": central,
            "campaign_budgets": budgets,
            "budget_errors": errors,
            "all_adv_ids_count": len(adv_ids),
            "active_adv_ids_count": len(active_ids),
        }


def _build_auto_topup_state(settings_rows: list[dict[str, str]]) -> dict[str, Any]:
    min_balance = int(os.environ.get("AUTO_BUDGET_MIN_BALANCE", "500"))
    topup_amount = int(os.environ.get("AUTO_BUDGET_TOPUP_AMOUNT", "1000"))
    enabled_rows: list[dict[str, Any]] = []
    for row in settings_rows:
        if str(row.get("auto_budget_watchdog_enabled")).lower() not in ("true", "t", "1"):
            continue
        enabled_rows.append(
            {
                "adv_setting_id": row.get("id"),
                "adv_id": row.get("adv_id"),
                "search_adv_id": row.get("_search_adv_id"),
                "name": row.get("name"),
                "bot_active": row.get("bot_active"),
                "active_status": row.get("active_status"),
                "auto_budget_watchdog_enabled": row.get("auto_budget_watchdog_enabled"),
                "auto_budget_daily_limit": row.get("auto_budget_daily_limit"),
                "search_auto_budget_daily_limit": row.get(
                    "search_auto_budget_daily_limit"
                ),
                "use_common_budget": row.get("use_common_budget"),
                "common_budget_daily_limit": row.get("common_budget_daily_limit"),
                "max_balance_adding_for_day": row.get("max_balance_adding_for_day"),
                "bot_topup_threshold_rub": min_balance,
                "bot_topup_amount_rub": topup_amount,
                "bot_balance_source_rule": (
                    "select lowest non-bonus WB pool >= threshold "
                    "(balance/net/bonus via balance_source.py)"
                ),
            }
        )
    return {
        "source": "PG advsetting + cluster env (adv-bot auto_budget_watchdog)",
        "wb_cabinet_native_autoreplenishment_api": "NOT_AVAILABLE_IN_API",
        "cluster_env": {
            "AUTO_BUDGET_MIN_BALANCE": min_balance,
            "AUTO_BUDGET_TOPUP_AMOUNT": topup_amount,
        },
        "watchdog_enabled_adv_settings": enabled_rows,
    }


def _estimate_gaps(
    central: dict[str, Any],
    budgets: list[dict[str, Any]],
    auto_topup: dict[str, Any],
) -> list[dict[str, Any]]:
    gaps: list[dict[str, Any]] = []
    threshold = int(auto_topup["cluster_env"]["AUTO_BUDGET_MIN_BALANCE"])
    topup = int(auto_topup["cluster_env"]["AUTO_BUDGET_TOPUP_AMOUNT"])
    pools = {
        "balance": int(central.get("balance") or 0),
        "net": int(central.get("net") or 0),
        "bonus": int(central.get("bonus") or 0),
    }
    max_pool = max(pools.values())
    if max_pool < topup:
        gaps.append(
            {
                "kind": "CENTRAL_POOL_BELOW_TOPUP_STEP",
                "max_pool_rub": max_pool,
                "topup_amount_rub": topup,
                "pools": pools,
            }
        )
    for row in budgets:
        total = row.get("total")
        if total is None:
            gaps.append({"kind": "BUDGET_UNKNOWN", "adv_id": row.get("adv_id")})
            continue
        if int(total) < threshold:
            gaps.append(
                {
                    "kind": "CAMPAIGN_BUDGET_BELOW_BOT_THRESHOLD",
                    "adv_id": row.get("adv_id"),
                    "total_rub": int(total),
                    "threshold_rub": threshold,
                }
            )
    return gaps


async def run_snapshot(
    output_dir: Path,
    wb_cabinet_id: int,
    settings_rows: list[dict[str, str]],
) -> dict[str, Any]:
    """Собрать funding snapshot и сохранить JSON."""
    output_dir.mkdir(parents=True, exist_ok=True)
    wb_data = await _collect_wb_funding()
    auto_topup = _build_auto_topup_state(settings_rows)
    budgets = wb_data["campaign_budgets"]
    central = wb_data["central"]

    totals = {
        "active_campaigns": len(budgets),
        "sum_total_rub": sum(int(b.get("total") or 0) for b in budgets),
        "sum_cash_rub": sum(int(b.get("cash") or 0) for b in budgets),
        "sum_netting_rub": sum(int(b.get("netting") or 0) for b in budgets),
    }
    lowest = sorted(budgets, key=lambda x: int(x.get("total") or 0))[:15]

    result = {
        "snapshot_at": datetime.now(timezone.utc).isoformat(),
        "shop_id": SHOP_ID,
        "wb_cabinet_id": wb_cabinet_id,
        "mode": "STRICT_READ_ONLY",
        "CENTRAL_PROMOTION_FUNDS": central,
        "CAMPAIGN_BUDGETS_TOTAL": totals,
        "LOWEST_BUDGET_CAMPAIGNS": lowest,
        "AUTO_TOPUP_STATE": auto_topup,
        "ESTIMATED_FUNDING_GAPS": _estimate_gaps(central, budgets, auto_topup),
        "meta": {
            "all_adv_ids_count": wb_data["all_adv_ids_count"],
            "active_adv_ids_count": wb_data["active_adv_ids_count"],
            "budget_api_errors": wb_data["budget_errors"],
        },
    }
    out_path = output_dir / "A1_PROMOTION_FUNDING_SNAPSHOT.json"
    out_path.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
    result["output_path"] = str(out_path.resolve())
    return result


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="A1 promotion funding READ_ONLY snapshot.")
    parser.add_argument("--output-dir", default=".tmp/a1_promotion_funding")
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    out = Path(args.output_dir).resolve()
    _bootstrap_cluster_infra()
    wb_cabinet_id, settings_rows = _load_adv_settings(out)
    result = asyncio.run(run_snapshot(out, wb_cabinet_id, settings_rows))
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
