"""READ_ONLY: cap-input data package from saved collect_v2 (no new collect).

Строит A1-DAILY-SPEND-CAP-INPUT-DATA-AUTHORITATIVE из authoritative reissue source zip.
PG-only поля (limits, bot_*) → NOT_AVAILABLE_IN_CURRENT_COLLECT если нет в collect.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
import zipfile
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from zoneinfo import ZoneInfo

import dotenv

dotenv.load_dotenv()

from scripts.a1_daily_spend_control_reconciliation import (
    ACTIVE_STATUSES,
    H1_AUTO,
    H1_SEARCH,
    SHOP_ID,
    TARGET_DAYS,
    _aggregate_fullstats,
    _campaign_inventory,
    _write_csv,
)
from scripts.a1_daily_spend_control_reissue import (
    _funnel_store_daily,
    _orders_by_nm_day,
    _orders_store_daily,
)
from scripts.wb_api_readonly_ops.collect_layout import (
    COLLECT_V2_CAMPAIGNS_JSONL,
    COLLECT_V2_FULLSTATS_JSONL,
    COLLECT_V2_FUNNEL_JSONL,
    COLLECT_V2_ORDERS_JSONL,
    LEGACY_ORDERS_JSONL,
    read_jsonl_from_zip,
)

MSK = ZoneInfo("Europe/Moscow")
PACKAGE_NAME = "A1-DAILY-SPEND-CAP-INPUT-DATA-AUTHORITATIVE"
SOURCE_REISSUE_ZIP = (
    "A1-DAILY-SPEND-CONTROL-AND-20260829-RECONCILIATION-AUTHORITATIVE-REISSUE.zip"
)
NA = "NOT_AVAILABLE_IN_CURRENT_COLLECT"


def _sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _leg_type(bid_type: Any) -> str:
    bt = str(bid_type or "").lower()
    if bt == "unified":
        return "Auto"
    if bt == "manual":
        return "Search"
    return "standalone"


def _build_store_csv(orders_daily: dict[str, dict[str, Any]], funnel_daily: dict[str, dict[str, Any]], store_spend: dict[str, float]) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for day in TARGET_DAYS:
        od = orders_daily.get(day, {})
        fd = funnel_daily.get(day, {})
        rows.append(
            {
                "date": day,
                "day_state": "OPEN_PARTIAL" if day == "2026-08-30" else "CLOSED",
                "factual_orders": od.get("factual_orders"),
                "factual_units": od.get("factual_units"),
                "factual_order_value_rub": od.get("factual_order_value_rub"),
                "factual_orders_source": "raw/orders.jsonl | GET /api/v1/supplier/orders",
                "funnel_order_count": fd.get("funnel_order_count"),
                "funnel_order_sum": fd.get("funnel_order_sum"),
                "funnel_add_to_cart": fd.get("funnel_add_to_cart"),
                "funnel_source": "raw/funnel/funnel.jsonl | POST /api/analytics/v3/sales-funnel/products/history",
                "store_total_ad_spend_rub": round(float(store_spend.get(day, 0)), 2),
                "ad_spend_source": "raw/ads/fullstats.jsonl | GET /adv/v3/fullstats",
            }
        )
    return rows


def _active_campaign_spend_rows(
    stats: dict[tuple[int, str], dict[str, Any]],
    inventory: dict[int, dict[str, Any]],
) -> list[dict[str, Any]]:
    spending_ids: set[int] = set()
    for (adv_id, day), row in stats.items():
        if day in TARGET_DAYS and float(row.get("spend") or 0) > 0:
            spending_ids.add(adv_id)
    active_ids = {aid for aid, inv in inventory.items() if inv.get("wb_status") in ACTIVE_STATUSES}
    target_ids = sorted(active_ids | spending_ids)

    attr_orders: dict[int, dict[str, int]] = defaultdict(lambda: defaultdict(int))
    attr_gmv: dict[int, dict[str, float]] = defaultdict(lambda: defaultdict(float))
    spend_by: dict[int, dict[str, float]] = defaultdict(lambda: defaultdict(float))
    for (adv_id, day), row in stats.items():
        if day not in TARGET_DAYS:
            continue
        spend_by[adv_id][day] += float(row.get("spend") or 0)
        attr_orders[adv_id][day] += int(row.get("orders") or 0)
        attr_gmv[adv_id][day] += float(row.get("sum_price") or 0)

    rows: list[dict[str, Any]] = []
    for adv_id in target_ids:
        inv = inventory.get(adv_id, {})
        nm_ids = inv.get("nm_ids") or []
        rows.append(
            {
                "adv_id": adv_id,
                "primary_nm_id": nm_ids[0] if nm_ids else "",
                "nm_ids": ";".join(str(x) for x in nm_ids),
                "leg_type": _leg_type(inv.get("bid_type")),
                "paired_adv_id": NA,
                "wb_status": inv.get("wb_status"),
                "bid_type": inv.get("bid_type"),
                "payment_type": inv.get("payment_type"),
                "spend_2026_08_27": round(spend_by[adv_id].get("2026-08-27", 0), 2),
                "spend_2026_08_28": round(spend_by[adv_id].get("2026-08-28", 0), 2),
                "spend_2026_08_29": round(spend_by[adv_id].get("2026-08-29", 0), 2),
                "spend_2026_08_30_partial": round(spend_by[adv_id].get("2026-08-30", 0), 2),
                "attributed_orders_29": attr_orders[adv_id].get("2026-08-29", 0),
                "attributed_gmv_29": round(attr_gmv[adv_id].get("2026-08-29", 0), 2),
                "attributed_source": "raw/ads/fullstats.jsonl (WB attributed, not causal)",
            }
        )
    return rows


def _sku_factual_sales_29(
    inventory: dict[int, dict[str, Any]],
    orders_nm: dict[tuple[int, str], dict[str, Any]],
    active_ids: set[int],
) -> list[dict[str, Any]]:
    day = "2026-08-29"
    nm_to_advs: dict[int, list[int]] = defaultdict(list)
    for adv_id in active_ids:
        inv = inventory.get(adv_id, {})
        for nmid in inv.get("nm_ids") or []:
            nm_to_advs[int(nmid)].append(adv_id)

    rows: list[dict[str, Any]] = []
    for nmid in sorted(nm_to_advs):
        nm = orders_nm.get((nmid, day), {})
        rows.append(
            {
                "nm_id": nmid,
                "linked_adv_ids": ";".join(str(a) for a in sorted(set(nm_to_advs[nmid]))),
                "factual_orders": int(nm.get("factual_orders") or 0),
                "factual_units": int(nm.get("factual_units") or 0),
                "factual_order_value_rub": round(float(nm.get("factual_order_value_rub") or 0), 2),
                "source": "raw/orders.jsonl | GET /api/v1/supplier/orders",
                "causal_claim": "FORBIDDEN",
            }
        )
    return rows


def _spend_control_fields(inventory: dict[int, dict[str, Any]], active_ids: set[int]) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for adv_id in sorted(active_ids):
        inv = inventory.get(adv_id, {})
        rows.append(
            {
                "adv_id": adv_id,
                "paired_adv_id": NA,
                "bot_linked": NA,
                "watchdog_enabled": NA,
                "auto_budget_daily_limit": NA,
                "search_auto_budget_daily_limit": NA,
                "use_common_budget": NA,
                "common_budget_daily_limit": NA,
                "active_status": NA,
                "bot_active": NA,
                "strategy": NA,
                "aggressiveness": NA,
                "wb_status": inv.get("wb_status"),
                "bid_type": inv.get("bid_type"),
                "collect_source": "raw/ads/campaigns.jsonl",
                "pg_fields_note": "advsetting not in collect_v2; limits/bot fields unavailable",
            }
        )
    return rows


def _daily_limit_code_facts_md() -> str:
    return """# DAILY_LIMIT_CODE_FACTS (file/symbol evidence only)

## Auto leg daily spend cap

| Fact | Evidence |
|------|----------|
| Field | `advsetting.auto_budget_daily_limit` |
| Model | `app/modules/common_slaves/wildberries/models/models.py` (`AdvSetting`) |
| Enforcement | `AutoAdvActiveControlService._auto_campaign_handler` |
| Path | `app/modules/shop_runner/service_manager/services/auto_adv_active_control/auto_adv_active_control_service.py` |
| Condition | `0 < auto_limit <= spend_today` → pause auto (`pause_auto_campaign`) |

## Search leg daily spend cap

| Fact | Evidence |
|------|----------|
| Field | `advsetting.search_auto_budget_daily_limit` |
| Enforcement | `AutoAdvActiveControlService._search_campaign_handler` |
| Path | `auto_adv_active_control_service.py` (~L1020–L1037) |
| Condition | `0 < search_limit <= spend_today` → pause auction (`pause_auction_campaign`) |

## Common budget (Auto+Search pair)

| Fact | Evidence |
|------|----------|
| Flag | `advsetting.use_common_budget` |
| Limit field | `advsetting.common_budget_daily_limit` |
| Enforcement | `_auto_campaign_handler` + `_search_campaign_handler` when `adv.use_common_budget` |
| Path | `auto_adv_active_control_service.py` (~L619–L648, ~L942+) |
| Condition | `combined_spend = spend_auto + spend_search`; pause when `0 < common_limit <= combined_spend` |

## Standalone daily cap

| Fact | Evidence |
|------|----------|
| Auto standalone | `auto_budget_daily_limit` on standalone `advsetting` row |
| Search standalone | `search_auto_budget_daily_limit` on row where search campaign is the auction leg |
| Applicable | YES — same handlers per leg when `use_common_budget` is false |

## Watchdog scheduler

| Fact | Evidence |
|------|----------|
| Entry | `WBShop.run()` → `CoroutinesManager.auto_budget_watchdog` |
| Decorator | `@while_coroutine_decorator(60, 60)` |
| Path | `app/modules/shop_runner/service_manager/manager.py` (~L902–L903) |
| Tick interval | ~60 seconds |

## Timezone / daily reset

| Fact | Evidence |
|------|----------|
| TZ constant | `MSK_TZ = timezone(timedelta(hours=3))` |
| Path | `auto_adv_active_control_service.py` (~L81) |
| Day window | `start_of_day` / `end_of_day` built from `datetime.now(MSK_TZ).date()` (~L231–L233) |
| Reset | implicit at 00:00 MSK (no separate cron) |

## Spend measurement

| Fact | Evidence |
|------|----------|
| Source | ClickHouse `default_db.full_adv_wb_stat`, `argMax(spend, version)` |
| SQL | `app/modules/shop_runner/wb_stat_manager/clickhouse_manager/sql/get_spend_by_last_days.sql` |
| Helper | `AutoAdvActiveControlService._get_spend_for_adv` |

## Known overshoot mechanism

| Fact | Evidence |
|------|----------|
| Tick gap | pause evaluated on ~60s watchdog interval |
| Ordering | top-up in `try`, pause in `finally` same tick (`manager.py` ~L903–L910) |
| CH lag | spend from CH may trail live WB spend before pause |
| Top-up step | fixed `AUTO_BUDGET_TOPUP_AMOUNT` may execute near limit before pause (`auto_budget_manager/service.py`) |
"""


def _h1_evidence_md(
    inventory: dict[int, dict[str, Any]],
    stats: dict[tuple[int, str], dict[str, Any]],
) -> str:
    lines = ["# H1_CURRENT_EVIDENCE", "", "Status interpretation: FORBIDDEN (facts only).", ""]

    def spend(adv_id: int) -> dict[str, float]:
        out: dict[str, float] = {}
        for day in TARGET_DAYS:
            out[day] = float(stats.get((adv_id, day), {}).get("spend") or 0)
        return out

    for adv_id in H1_AUTO:
        inv = inventory.get(adv_id, {})
        sp = spend(adv_id)
        lines.extend(
            [
                f"## Auto {adv_id}",
                "",
                f"- present_in_collect_campaigns: **{adv_id in inventory}**",
                f"- wb_status: **{inv.get('wb_status', 'MISSING')}**",
                f"- spend_27: **{sp.get('2026-08-27', 0):.2f}**",
                f"- spend_28: **{sp.get('2026-08-28', 0):.2f}**",
                f"- spend_29: **{sp.get('2026-08-29', 0):.2f}**",
                f"- spend_30_partial: **{sp.get('2026-08-30', 0):.2f}**",
                f"- auto_budget_daily_limit: **{NA}**",
                f"- search_auto_budget_daily_limit: **{NA}**",
                f"- common_budget_daily_limit: **{NA}**",
                "",
            ]
        )

    for adv_id in H1_SEARCH:
        inv = inventory.get(adv_id, {})
        sp = spend(adv_id)
        lines.extend(
            [
                f"## Search {adv_id}",
                "",
                f"- present_in_collect_campaigns: **{adv_id in inventory}**",
                f"- wb_status: **{inv.get('wb_status', 'MISSING')}**",
                f"- spend_27: **{sp.get('2026-08-27', 0):.2f}**",
                f"- spend_28: **{sp.get('2026-08-28', 0):.2f}**",
                f"- spend_29: **{sp.get('2026-08-29', 0):.2f}**",
                f"- spend_30_partial: **{sp.get('2026-08-30', 0):.2f}**",
                f"- auto_budget_daily_limit: **{NA}**",
                f"- search_auto_budget_daily_limit: **{NA}**",
                f"- common_budget_daily_limit: **{NA}**",
                "",
            ]
        )
    return "\n".join(lines)


def _file_hashes(pkg_dir: Path) -> dict[str, str]:
    out: dict[str, str] = {}
    for path in sorted(pkg_dir.rglob("*")):
        if path.is_file() and path.name != "PACKAGE_MANIFEST.json":
            rel = path.relative_to(pkg_dir).as_posix()
            out[rel] = _sha256_file(path)
    return out


def _write_archive(pkg_dir: Path, zip_path: Path) -> str:
    with zipfile.ZipFile(zip_path, "w", compression=zipfile.ZIP_DEFLATED) as zf:
        for path in sorted(pkg_dir.rglob("*")):
            if path.is_file():
                zf.write(path, arcname=path.relative_to(pkg_dir).as_posix())
    return _sha256_file(zip_path)


def build_cap_input_package(
    *,
    collect_zip: Path,
    output_dir: Path,
    source_reissue_zip: Path | None = None,
) -> dict[str, Any]:
    """Собрать cap-input package из collect_v2 zip."""
    checked_msk = datetime.now(timezone.utc).astimezone(MSK)

    with zipfile.ZipFile(collect_zip) as zf:
        orders, orders_path = read_jsonl_from_zip(
            zf, COLLECT_V2_ORDERS_JSONL, legacy=LEGACY_ORDERS_JSONL
        )
        funnel, funnel_path = read_jsonl_from_zip(zf, COLLECT_V2_FUNNEL_JSONL)
        fullstats, _ = read_jsonl_from_zip(zf, COLLECT_V2_FULLSTATS_JSONL)
        campaigns, _ = read_jsonl_from_zip(zf, COLLECT_V2_CAMPAIGNS_JSONL)

    orders_daily, orders_meta = _orders_store_daily(orders)
    funnel_daily = _funnel_store_daily(funnel)
    orders_nm = _orders_by_nm_day(orders)
    stats = _aggregate_fullstats(fullstats)
    inventory = _campaign_inventory(campaigns, {})
    active_ids = {aid for aid, inv in inventory.items() if inv.get("wb_status") in ACTIVE_STATUSES}

    store_spend: dict[str, float] = defaultdict(float)
    for (_adv, day), row in stats.items():
        if day in TARGET_DAYS:
            store_spend[day] += float(row.get("spend") or 0)

    store_rows = _build_store_csv(orders_daily, funnel_daily, dict(store_spend))
    campaign_rows = _active_campaign_spend_rows(stats, inventory)
    sku_rows = _sku_factual_sales_29(inventory, orders_nm, active_ids)
    control_rows = _spend_control_fields(inventory, active_ids)

    gate_errors: list[str] = []
    if len(orders) <= 0:
        gate_errors.append("orders_rows_zero")
    if orders_path != COLLECT_V2_ORDERS_JSONL:
        gate_errors.append(f"orders_path_not_canonical:{orders_path}")
    day29 = next((r for r in store_rows if r["date"] == "2026-08-29"), {})
    if not day29.get("factual_orders"):
        gate_errors.append("29_08_factual_orders_missing")
    package_status = "AUTHORITATIVE" if not gate_errors else "BLOCKED"

    pkg_dir = output_dir / PACKAGE_NAME
    pkg_dir.mkdir(parents=True, exist_ok=True)

    _write_csv(pkg_dir / "STORE_DAILY_RESULT.csv", store_rows, list(store_rows[0].keys()))
    _write_csv(
        pkg_dir / "ACTIVE_CAMPAIGN_SPEND.csv",
        campaign_rows,
        list(campaign_rows[0].keys()) if campaign_rows else ["adv_id"],
    )
    _write_csv(
        pkg_dir / "SKU_FACTUAL_SALES_20260829.csv",
        sku_rows,
        list(sku_rows[0].keys()) if sku_rows else ["nm_id"],
    )
    _write_csv(
        pkg_dir / "CURRENT_SPEND_CONTROL_FIELDS.csv",
        control_rows,
        list(control_rows[0].keys()) if control_rows else ["adv_id"],
    )
    (pkg_dir / "DAILY_LIMIT_CODE_FACTS.md").write_text(_daily_limit_code_facts_md(), encoding="utf-8")
    (pkg_dir / "H1_CURRENT_EVIDENCE.md").write_text(_h1_evidence_md(inventory, stats), encoding="utf-8")

    provenance = [
        "# SOURCE_PROVENANCE",
        "",
        f"- package: `{PACKAGE_NAME}`",
        f"- shop_id: `{SHOP_ID}`",
        f"- collect_zip: `{collect_zip.resolve()}`",
        f"- collect_layout: collect_v2",
        f"- orders_member: `{orders_path}`",
        f"- funnel_member: `{funnel_path}`",
        f"- source_reissue_zip: `{source_reissue_zip.resolve() if source_reissue_zip else NA}`",
        f"- built_at_msk: {checked_msk.strftime('%Y-%m-%d %H:%M:%S %Z')}",
        "- no_new_collect: true",
        "- no_production_mutations: true",
        f"- pg_limit_fields: {NA}",
    ]
    (pkg_dir / "SOURCE_PROVENANCE.md").write_text("\n".join(provenance), encoding="utf-8")

    file_hashes = _file_hashes(pkg_dir)
    payload: dict[str, Any] = {
        "package": PACKAGE_NAME,
        "PACKAGE_STATUS": package_status,
        "checked_at_msk": checked_msk.strftime("%Y-%m-%d %H:%M:%S %Z"),
        "shop_id": SHOP_ID,
        "mode": "STRICT_READ_ONLY",
        "ORDERS_ROWS": len(orders),
        "ACTIVE_CAMPAIGNS_COUNT": len(active_ids),
        "29_08_FACTUAL_ORDERS": day29.get("factual_orders"),
        "29_08_FACTUAL_ORDER_VALUE": day29.get("factual_order_value_rub"),
        "29_08_TOTAL_AD_SPEND": round(float(store_spend.get("2026-08-29", 0)), 2),
        "integrity_gate_errors": gate_errors,
        "file_sha256": file_hashes,
        "STORE_DAILY_RESULT": store_rows,
        "ACTIVE_CAMPAIGN_SPEND": campaign_rows,
        "SKU_FACTUAL_SALES_20260829": sku_rows,
        "CURRENT_SPEND_CONTROL_FIELDS": control_rows,
        "orders_loader": orders_meta,
    }
    (pkg_dir / f"{PACKAGE_NAME}.json").write_text(
        json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8"
    )

    manifest = {
        "package": PACKAGE_NAME,
        "PACKAGE_STATUS": package_status,
        "file_sha256": file_hashes,
        "integrity_gate_errors": gate_errors,
    }
    (pkg_dir / "PACKAGE_MANIFEST.json").write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8"
    )

    zip_path = output_dir / f"{PACKAGE_NAME}.zip"
    archive_sha = _write_archive(pkg_dir, zip_path)

    payload["FINAL_ARCHIVE_SHA256"] = archive_sha
    payload["ABSOLUTE_ARCHIVE_PATH"] = str(zip_path.resolve())
    (pkg_dir / f"{PACKAGE_NAME}.json").write_text(
        json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    _write_archive(pkg_dir, zip_path)
    payload["output_dir"] = str(pkg_dir.resolve())
    return payload


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Build A1 daily spend cap input data package.")
    parser.add_argument("--output-dir", default=".tmp/a1_daily_spend_control")
    parser.add_argument(
        "--collect-zip",
        type=Path,
        default=Path(".tmp/a1_daily_spend_control/source/wb_readonly_research.zip"),
    )
    parser.add_argument(
        "--source-reissue-zip",
        type=Path,
        default=Path(f".tmp/a1_daily_spend_control/{SOURCE_REISSUE_ZIP}"),
    )
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    out = Path(args.output_dir).resolve()
    result = build_cap_input_package(
        collect_zip=args.collect_zip.resolve(),
        output_dir=out,
        source_reissue_zip=args.source_reissue_zip.resolve()
        if args.source_reissue_zip.exists()
        else None,
    )
    sys.stdout.reconfigure(encoding="utf-8")
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0 if result.get("PACKAGE_STATUS") == "AUTHORITATIVE" else 1


if __name__ == "__main__":
    sys.exit(main())
