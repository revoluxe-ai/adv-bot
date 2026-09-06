"""READ_ONLY: A1 gross DRR, promo deposit usage, and cash-load evidence package.

Собирает фактические оформленные заказы магазина, gross ad spend по всем
физическим РК кабинета, durable top-up журнал (WBAutoBudgetTopUp) с разделением
promo bonus vs ordinary funds на deposit, текущий promo pool и accounting status.
Не выполняет writes в WB/PG/CH/Redis.
"""

from __future__ import annotations

import argparse
import asyncio
import csv
import json
import sys
from collections import defaultdict
from datetime import date, datetime, timedelta, timezone
from pathlib import Path
from typing import Any
from zoneinfo import ZoneInfo

import dotenv

dotenv.load_dotenv()

from scripts import ch_a1_evidence as evidence
from scripts.a1_daily_spend_control_reconciliation import (
    _campaign_inventory,
    _pg_by_adv_id,
    _write_csv,
)
from scripts.a1_promotion_funding_snapshot import (
    SHOP_ID,
    _api_model_dict,
    _bootstrap_cluster_infra,
    _cashbacks_to_list,
    _collect_wb_funding,
    _load_adv_settings,
)
from scripts.wb_a1_associated_conversions import (
    _jsonable,
    _nm_rows,
    _read_float,
    _read_int,
)
from scripts.wb_api_readonly_ops.collect.api_budget import ApiCallBudget
from scripts.wb_api_readonly_ops.collect.jsonable import jsonable
from scripts.wb_api_readonly_ops.collect.orders_sales import _paginate_supplier_rows

MSK = ZoneInfo("Europe/Moscow")
PACKAGE = "A1-PROMO-ADJUSTED-DRR"
FIXED_FROM = date(2026, 8, 30)
FIXED_TO = date(2026, 9, 5)
COLLECT_FROM = date(2026, 8, 27)
PRIORITY_NMIDS = (14166423, 85970344, 14824677, 837395782, 7974113)
HISTORICAL_PROMO_REF = {
    "checked_at_msk": "2026-09-05 08:01:45 MSK",
    "net": 69477,
    "cashback_sum": 42800,
    "cashback_percent": 50,
    "expiry_msk": "2026-09-11 00:00 MSK",
}


def _msk_now() -> datetime:
    return datetime.now(timezone.utc).astimezone(MSK)


def _iso_msk(dt: datetime) -> str:
    return dt.astimezone(MSK).isoformat()


def _closed_end_day(now: datetime | None = None) -> date:
    """Последний полностью закрытый день MSK = вчера относительно now."""
    return (now or _msk_now()).date() - timedelta(days=1)


def _open_day(now: datetime | None = None) -> date:
    return (now or _msk_now()).date()


def _day_state(day: date, closed_end: date, open_d: date) -> str:
    if day == open_d:
        return "OPEN"
    if day <= closed_end:
        return "CLOSED"
    return "FUTURE"


def _pg_database() -> str:
    import os

    return os.environ.get("POSTGRES_DBNAME") or "adv_updater"


def _is_cancelled(row: dict[str, Any]) -> bool:
    return str(row.get("isCancel")).lower() in ("true", "1", "t")


def _order_day(row: dict[str, Any]) -> str:
    return str(row.get("date") or row.get("lastChangeDate") or "")[:10]


def _load_wbcabinet(root: Path, sql_dir: Path) -> dict[str, Any]:
    staging = root / "staging"
    staging.mkdir(parents=True, exist_ok=True)
    path = staging / "wbcabinet.csv"
    st = evidence.run_pg_query(
        _pg_database(),
        (
            "SELECT id, shop_id, balance, bonus FROM public.wbcabinet "
            f"WHERE shop_id = '{SHOP_ID}'"
        ),
        path,
        sql_dir / "pg_wbcabinet_shop.sql",
        csv_output=True,
    )
    if not st["success"]:
        raise RuntimeError(f"wbcabinet query failed: {st['stderr']}")
    with path.open(encoding="utf-8", newline="") as handle:
        rows = list(csv.DictReader(handle))
    if not rows:
        raise RuntimeError(f"wbcabinet not found for shop_id={SHOP_ID}")
    row = rows[0]
    return {
        "wb_cabinet_id": int(row["id"]),
        "shop_id": row["shop_id"],
        "pg_balance": row.get("balance"),
        "pg_bonus": row.get("bonus"),
    }


def _load_topups(
    root: Path, sql_dir: Path, wb_cabinet_id: int, date_from: date
) -> list[dict[str, Any]]:
    staging = root / "staging"
    path = staging / "wbautobudgettopup.csv"
    st = evidence.run_pg_query(
        _pg_database(),
        (
            "SELECT t.id, t.adv_setting_id, t.adv_id, t.campaign_type, t.date_msk, "
            "t.idempotency_key, t.amount, t.balance_type, t.budget_before, t.budget_after, "
            "t.status, t.reason, t.request_payload, t.response_payload, "
            "t.created_at, t.updated_at "
            "FROM public.wbautobudgettopup t "
            "JOIN public.advsetting a ON t.adv_setting_id = a.id "
            f"WHERE a.wb_cabinet_id = {wb_cabinet_id} "
            f"AND t.date_msk >= '{date_from.isoformat()}' "
            "ORDER BY t.created_at"
        ),
        path,
        sql_dir / "pg_wbautobudgettopup.sql",
        csv_output=True,
    )
    if not st["success"]:
        raise RuntimeError(f"wbautobudgettopup query failed: {st['stderr']}")
    with path.open(encoding="utf-8", newline="") as handle:
        return list(csv.DictReader(handle))


def _parse_json_field(raw: Any) -> dict[str, Any]:
    if isinstance(raw, dict):
        return raw
    if not raw:
        return {}
    try:
        val = json.loads(str(raw))
        return val if isinstance(val, dict) else {}
    except json.JSONDecodeError:
        return {}


def _normalize_topup(row: dict[str, str]) -> dict[str, Any]:
    req = _parse_json_field(row.get("request_payload"))
    resp = _parse_json_field(row.get("response_payload"))
    amount = int(float(row.get("amount") or 0))
    cashback_sum = req.get("cashback_sum")
    promo = int(cashback_sum) if cashback_sum is not None else 0
    ordinary = max(amount - promo, 0)
    created = str(row.get("created_at") or "")
    return {
        "topup_id": row.get("id"),
        "adv_setting_id": row.get("adv_setting_id"),
        "adv_id": row.get("adv_id"),
        "campaign_type": row.get("campaign_type"),
        "date_msk": row.get("date_msk"),
        "timestamp_utc": created,
        "timestamp_msk": created,
        "total_deposit_rub": amount,
        "promo_bonus_rub": promo,
        "ordinary_funds_rub": ordinary,
        "cashback_percent": req.get("cashback_percent"),
        "balance_type": row.get("balance_type"),
        "balance_source_type": req.get("balance_type") or row.get("balance_type"),
        "budget_before": row.get("budget_before"),
        "budget_after": row.get("budget_after"),
        "status": row.get("status"),
        "reason": row.get("reason"),
        "idempotency_key": row.get("idempotency_key"),
        "request_payload": req,
        "response_payload": resp,
        "durable_source": "PG public.wbautobudgettopup",
    }


def _orders_store_daily(
    orders: list[dict[str, Any]],
    closed_end: date,
    open_d: date,
) -> dict[str, dict[str, Any]]:
    """Factual placed orders (оформленные) — exclude isCancel=true."""
    by_day: dict[str, dict[str, Any]] = defaultdict(
        lambda: {
            "purchase_events": 0,
            "units": 0,
            "factual_order_value": 0.0,
            "cancelled_excluded": 0,
        }
    )
    for row in orders:
        if _is_cancelled(row):
            day = _order_day(row)
            if day:
                by_day[day]["cancelled_excluded"] += 1
            continue
        day = _order_day(row)
        if not day:
            continue
        try:
            d = date.fromisoformat(day)
        except ValueError:
            continue
        if d < COLLECT_FROM or d > open_d:
            continue
        qty = _read_int(row, "quantity", "qty") or 1
        price = _read_float(row, "totalPrice", "priceWithDisc", "finishedPrice")
        bucket = by_day[day]
        bucket["purchase_events"] += 1
        bucket["units"] += qty
        bucket["factual_order_value"] += price * qty if price else price
    out: dict[str, dict[str, Any]] = {}
    d = COLLECT_FROM
    while d <= open_d:
        key = d.isoformat()
        raw = by_day.get(key)
        state = _day_state(d, closed_end, open_d)
        if raw:
            out[key] = {
                "date": key,
                "day_state": state,
                "purchase_events": raw["purchase_events"],
                "units": raw["units"],
                "factual_order_value": round(raw["factual_order_value"], 2),
                "cancellation_semantics": "exclude isCancel=true supplier order rows",
                "source": "GET /api/v1/supplier/orders",
                "cancelled_rows_excluded": raw["cancelled_excluded"],
            }
        else:
            out[key] = {
                "date": key,
                "day_state": state,
                "purchase_events": 0,
                "units": 0,
                "factual_order_value": 0.0,
                "cancellation_semantics": "exclude isCancel=true supplier order rows",
                "source": "GET /api/v1/supplier/orders",
                "cancelled_rows_excluded": 0,
            }
        d += timedelta(days=1)
    return out


def _gross_spend_daily(day_rows: list[dict[str, Any]], closed_end: date, open_d: date) -> dict[str, dict[str, Any]]:
    """Store gross spend — sum campaign-day totals (no nm/app double-count)."""
    by_day: dict[str, float] = defaultdict(float)
    campaigns_by_day: dict[str, set[int]] = defaultdict(set)
    for row in day_rows:
        day = row.get("date", "")
        if not day:
            continue
        try:
            d = date.fromisoformat(day)
        except ValueError:
            continue
        if d < COLLECT_FROM or d > open_d:
            continue
        adv_id = int(row.get("advert_id") or 0)
        by_day[day] += float(row.get("day_spend") or 0)
        if adv_id:
            campaigns_by_day[day].add(adv_id)
    out: dict[str, dict[str, Any]] = {}
    d = COLLECT_FROM
    while d <= open_d:
        key = d.isoformat()
        out[key] = {
            "date": key,
            "day_state": _day_state(d, closed_end, open_d),
            "gross_ad_spend": round(by_day.get(key, 0.0), 2),
            "campaigns_with_spend": len(campaigns_by_day.get(key, set())),
            "source": "GET /adv/v3/fullstats day.sum (campaign-day, no nm re-sum)",
            "dedupe_note": "one row per advert_id per day from _nm_rows day_rows",
        }
        d += timedelta(days=1)
    return out


def _topup_daily(normalized: list[dict[str, Any]], closed_end: date, open_d: date) -> dict[str, dict[str, Any]]:
    by_day: dict[str, dict[str, float | int]] = defaultdict(
        lambda: {"promo": 0.0, "ordinary": 0.0, "total": 0.0, "events": 0}
    )
    for row in normalized:
        if str(row.get("status")) != "success":
            continue
        day = str(row.get("date_msk") or "")[:10]
        if not day:
            continue
        bucket = by_day[day]
        bucket["promo"] += float(row.get("promo_bonus_rub") or 0)
        bucket["ordinary"] += float(row.get("ordinary_funds_rub") or 0)
        bucket["total"] += float(row.get("total_deposit_rub") or 0)
        bucket["events"] += 1
    out: dict[str, dict[str, Any]] = {}
    d = COLLECT_FROM
    while d <= open_d:
        key = d.isoformat()
        raw = by_day.get(key, {"promo": 0.0, "ordinary": 0.0, "total": 0.0, "events": 0})
        out[key] = {
            "date": key,
            "day_state": _day_state(d, closed_end, open_d),
            "promo_bonus_used_on_deposits": round(float(raw["promo"]), 2),
            "ordinary_funds_used_on_deposits": round(float(raw["ordinary"]), 2),
            "total_deposits": round(float(raw["total"]), 2),
            "topup_events_success": int(raw["events"]),
            "source": "PG wbautobudgettopup status=success",
        }
        d += timedelta(days=1)
    return out


def _drr_pct(spend: float, sales: float) -> str | float:
    if sales <= 0:
        return "GAP"
    return round(100.0 * spend / sales, 4)


def _window_aggregate(
    label: str,
    date_from: date,
    date_to: date,
    sales_daily: dict[str, dict[str, Any]],
    spend_daily: dict[str, dict[str, Any]],
    topup_daily: dict[str, dict[str, Any]],
    closed_end: date,
    accounting_status: str,
    notes: str,
) -> dict[str, Any]:
    sales = 0.0
    spend = 0.0
    promo = 0.0
    ordinary = 0.0
    days = 0
    d = date_from
    while d <= date_to:
        if d > closed_end:
            d += timedelta(days=1)
            continue
        key = d.isoformat()
        sd = sales_daily.get(key, {})
        sp = spend_daily.get(key, {})
        tp = topup_daily.get(key, {})
        sales += float(sd.get("factual_order_value") or 0)
        spend += float(sp.get("gross_ad_spend") or 0)
        promo += float(tp.get("promo_bonus_used_on_deposits") or 0)
        ordinary += float(tp.get("ordinary_funds_used_on_deposits") or 0)
        days += 1
        d += timedelta(days=1)
    gross_drr = _drr_pct(spend, sales)
    return {
        "window_label": label,
        "period_from": date_from.isoformat(),
        "period_to": date_to.isoformat(),
        "days": days,
        "factual_order_value": round(sales, 2),
        "gross_ad_spend": round(spend, 2),
        "gross_drr": gross_drr,
        "promo_bonus_used_on_deposits": round(promo, 2),
        "ordinary_funds_used_on_deposits": round(ordinary, 2),
        "promo_funded_ad_spend": "GAP",
        "cash_funded_ad_spend": "GAP",
        "promo_adjusted_drr": "GAP",
        "accounting_status": accounting_status,
        "notes": notes,
    }


def _build_promo_mechanics_md(accounting_status: str) -> str:
    return "\n".join(
        [
            "# Promo mechanics — factual semantics",
            "",
            "## Code paths (deposit-time promo co-payment)",
            "",
            "1. **Promo bonus pool used only at campaign budget deposit** — YES.",
            "   - `AutoBudgetService.ensure_budget` / `ensure_common_budget` call",
            "     `select_topup_balance_decision()` then `top_up_budget()` with optional",
            "     `cashback_sum` / `cashback_percent` on POST `/adv/v1/budget/deposit`.",
            "   - Paths: `app/modules/auto_budget_manager/service.py` (~L357-L420),",
            "     `app/core/mp/wb/api/adapter/promotion_client/finance/adapter.py` (~L81-L103).",
            "",
            "2. **Percent caps share of a specific top-up** — YES.",
            "   - `pick_cashback_for_topup()`: `payable = min(topup_amount * percent/100, cashback_sum)`.",
            "   - Path: `app/shared/domains/wb/utils/balance_source.py` (~L150-L172).",
            "",
            "3. **Ordinary funding pays the rest** — YES.",
            "   - Non-bonus source (`balance` or `net`) selected via `_select_non_bonus_source()`",
            "     when cashback overlay applies; deposit `amount` is total, cashback is co-pay portion.",
            "",
            "4. **Promo bonus is NOT a standalone spend wallet** — YES.",
            "   - Cashbacks live in GET `/adv/v1/balance` `cashbacks[]`; consumed via deposit body,",
            "     not debited per ad impression.",
            "",
            "5. **WB ad spend after top-up does NOT retain source provenance** — YES (inferred).",
            "   - fullstats `sum` reports gross spend; no API field marks bonus-funded vs cash-funded rubles.",
            "   - Durable journal records promo at **deposit** (`WBAutoBudgetTopUp.request_payload`).",
            "",
            "## Accounting status for this package",
            "",
            f"**{accounting_status}** — promo consumed at top-up time; same-calendar-day",
            "`gross_ad_spend - promo_used_on_deposits` is **not** valid cash-funded spend.",
            "",
            "## Forbidden simplification",
            "",
            "Do NOT treat `promo_percent × advertising_spend` as fact.",
            "50% cashback is co-payment on budget **deposit**, not 50% of every spend ruble.",
            "",
        ]
    )


async def _wb_collect(
    closed_end: date,
    open_d: date,
    pg_rows: list[dict[str, str]],
) -> tuple[list[dict[str, Any]], list[dict[str, Any]], list[dict[str, Any]], list[int]]:
    from app.core.di.app_container import AppContainer
    from app.core.di.di_manager import DIManager
    from app.core.mp.wb.api.adapter.promotion_client.fullstats.chunked import (
        run_chunked_single_range,
    )

    campaigns: list[dict[str, Any]] = []
    fullstats_raw: list[dict[str, Any]] = []
    orders_raw: list[dict[str, Any]] = []

    async with await DIManager.create(AppContainer) as container:  # type: ignore[attr-defined]
        factory = (
            container.module_resources.wb_manager_hub_factory_container.wb_manager_hub_factory()
        )
        hub = factory.get_wb_manager_hub(SHOP_ID)
        dm = hub.wb_data_manager
        pm = dm.promotion_manager
        budget = ApiCallBudget(max_seconds=1800.0, max_api_calls=2500)
        reports_manager = getattr(dm, "reports_manager", None)

        async def fetch_orders(df: str) -> list[object]:
            if reports_manager is not None:
                return list(await reports_manager.get_supplier_orders(date_from=df, flag=0) or [])
            return list(await dm.get_supplier_orders(date_from=df, flag=0) or [])

        orders_result = await _paginate_supplier_rows(
            fetch=fetch_orders,
            initial_date_from=COLLECT_FROM.isoformat(),
            budget=budget,
            max_pages=1500,
        )
        orders_raw = [jsonable(r) for r in orders_result.rows if isinstance(jsonable(r), dict)]

        budget.consume()
        cabinet_adv_ids = list(await pm._client.promotion_count_adapter.get_cabinet_adv_ids() or [])
        budget.consume()
        camps_raw = list(await pm.get_adverts_v2_by_ids(cabinet_adv_ids) or [])
        for item in camps_raw:
            row = jsonable(item)
            if isinstance(row, dict):
                campaigns.append(row)

        client = pm._client
        adapter = client.fullstats_adapter

        async def fetcher(chunk: list[int], b: date, e: date) -> list[Any]:
            return await adapter._request_chunk(chunk, b, e)

        items = await run_chunked_single_range(
            cabinet_adv_ids, COLLECT_FROM, open_d, fetcher
        )
        for item in items:
            fullstats_raw.append(_jsonable(item.to_dict()))

    return campaigns, fullstats_raw, orders_raw, cabinet_adv_ids


def _campaign_promo_reconciliation(
    normalized: list[dict[str, Any]],
    spend_by_adv: dict[int, float],
    budgets: list[dict[str, Any]],
    inventory: dict[int, dict[str, Any]],
) -> list[dict[str, Any]]:
    promo_by_adv: dict[int, float] = defaultdict(float)
    ordinary_by_adv: dict[int, float] = defaultdict(float)
    deposit_by_adv: dict[int, float] = defaultdict(float)
    for row in normalized:
        if str(row.get("status")) != "success":
            continue
        adv_id = int(row.get("adv_id") or 0)
        if not adv_id:
            continue
        promo_by_adv[adv_id] += float(row.get("promo_bonus_rub") or 0)
        ordinary_by_adv[adv_id] += float(row.get("ordinary_funds_rub") or 0)
        deposit_by_adv[adv_id] += float(row.get("total_deposit_rub") or 0)
    budget_by_adv = {int(b.get("adv_id") or 0): b for b in budgets}
    adv_ids = sorted(
        set(spend_by_adv) | set(promo_by_adv) | set(budget_by_adv) | set(inventory)
    )
    rows: list[dict[str, Any]] = []
    for adv_id in adv_ids:
        if not adv_id:
            continue
        dep = deposit_by_adv.get(adv_id, 0.0)
        promo = promo_by_adv.get(adv_id, 0.0)
        ordinary = ordinary_by_adv.get(adv_id, 0.0)
        promo_share = round(100.0 * promo / dep, 2) if dep > 0 else "GAP"
        b = budget_by_adv.get(adv_id, {})
        inv = inventory.get(adv_id, {})
        rows.append(
            {
                "adv_id": adv_id,
                "campaign_name": inv.get("name") or "GAP",
                "gross_spend_window": round(spend_by_adv.get(adv_id, 0.0), 2),
                "deposit_total_success": round(dep, 2),
                "promo_amount_deposits": round(promo, 2),
                "ordinary_amount_deposits": round(ordinary, 2),
                "promo_share_of_funding_pct": promo_share,
                "current_campaign_budget_total": b.get("total") if b else "GAP",
                "opening_campaign_budget": "GAP",
                "closing_campaign_budget": b.get("total") if b else "GAP",
                "priority5_nm": "YES" if any(
                    n in PRIORITY_NMIDS for n in (inv.get("nm_ids") or [])
                ) else "NO",
            }
        )
    return rows


def run_collect(output_dir: Path) -> dict[str, Any]:
    """Собрать evidence package и вернуть manifest summary."""
    checked_at = _msk_now()
    closed_end = _closed_end_day(checked_at)
    open_d = _open_day(checked_at)
    accounting_status = "CASH_FLOW_ONLY"

    root = output_dir.resolve()
    root.mkdir(parents=True, exist_ok=True)
    raw_dir = root / "raw"
    raw_dir.mkdir(parents=True, exist_ok=True)
    sql_dir = root / "staging" / "sql"
    sql_dir.mkdir(parents=True, exist_ok=True)

    _bootstrap_cluster_infra()
    cabinet = _load_wbcabinet(root, sql_dir)
    wb_cabinet_id = cabinet["wb_cabinet_id"]

    wb_cabinet_id_expected = 401
    if wb_cabinet_id != wb_cabinet_id_expected:
        gaps_verify = [
            f"WB_CABINET_ID_MISMATCH: expected {wb_cabinet_id_expected}, got {wb_cabinet_id}"
        ]
    else:
        gaps_verify = []

    settings_rows = _load_adv_settings(root)[1]
    pg_by_adv = _pg_by_adv_id(settings_rows)

    topup_raw = _load_topups(root, sql_dir, wb_cabinet_id, COLLECT_FROM)
    seen_keys: set[str] = set()
    topup_raw_deduped: list[dict[str, str]] = []
    for row in topup_raw:
        key = row.get("idempotency_key") or row.get("id") or ""
        if key in seen_keys:
            continue
        seen_keys.add(key)
        topup_raw_deduped.append(row)

    normalized = [_normalize_topup(r) for r in topup_raw_deduped]

    wb_funding = asyncio.run(_collect_wb_funding())
    central = wb_funding["central"]
    campaign_budgets = wb_funding["campaign_budgets"]

    wb_payload = asyncio.run(_wb_collect(closed_end, open_d, settings_rows))
    campaigns, fullstats_raw, orders_raw, cabinet_adv_ids = wb_payload

    with (raw_dir / "campaigns_v2.jsonl").open("w", encoding="utf-8") as handle:
        for row in campaigns:
            handle.write(json.dumps(_jsonable(row), ensure_ascii=False) + "\n")
    with (raw_dir / "fullstats_v3_raw.jsonl").open("w", encoding="utf-8") as handle:
        for row in fullstats_raw:
            handle.write(json.dumps(_jsonable(row), ensure_ascii=False) + "\n")
    with (raw_dir / "supplier_orders_raw.jsonl").open("w", encoding="utf-8") as handle:
        for row in orders_raw:
            handle.write(json.dumps(_jsonable(row), ensure_ascii=False) + "\n")
    with (raw_dir / "wbautobudgettopup_raw.jsonl").open("w", encoding="utf-8") as handle:
        for row in topup_raw_deduped:
            handle.write(json.dumps(row, ensure_ascii=False, default=str) + "\n")

    _, day_rows = _nm_rows(fullstats_raw)
    inventory = _campaign_inventory(campaigns, pg_by_adv)

    sales_daily = _orders_store_daily(orders_raw, closed_end, open_d)
    spend_daily = _gross_spend_daily(day_rows, closed_end, open_d)
    topup_daily = _topup_daily(normalized, closed_end, open_d)

    balance_snapshot = {
        "checked_at_msk": _iso_msk(checked_at),
        "shop_id": SHOP_ID,
        "wb_cabinet_id": wb_cabinet_id,
        "wb_cabinet_id_verified": wb_cabinet_id == wb_cabinet_id_expected,
        "balance": central.get("balance"),
        "net": central.get("net"),
        "bonus": central.get("bonus"),
        "cashbacks": central.get("cashbacks") or _cashbacks_to_list(central.get("cashbacks")),
        "endpoint": "GET /adv/v1/balance",
        "historical_reference": HISTORICAL_PROMO_REF,
        "promo_pool_change": {
            "current_cashback_total": sum(
                int(c.get("sum") or 0) for c in (central.get("cashbacks") or [])
            ),
            "historical_cashback_total": HISTORICAL_PROMO_REF["cashback_sum"],
            "delta_rub": "GAP_WITHOUT_DURABLE_HISTORICAL_SNAPSHOT",
            "cause": "Only point-in-time balance API + Owner reference; no time-series cashback ledger",
        },
    }

    (root / "02_CURRENT_BALANCE_SNAPSHOT.json").write_text(
        json.dumps(balance_snapshot, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    (root / "01_PROMO_MECHANICS.md").write_text(
        _build_promo_mechanics_md(accounting_status), encoding="utf-8"
    )

    raw_cols = list(topup_raw_deduped[0].keys()) if topup_raw_deduped else ["id"]
    _write_csv(root / "03_TOPUP_EVENTS_RAW.csv", topup_raw_deduped, raw_cols)

    norm_cols = [
        "topup_id", "adv_setting_id", "adv_id", "campaign_type", "date_msk",
        "timestamp_msk", "total_deposit_rub", "promo_bonus_rub", "ordinary_funds_rub",
        "cashback_percent", "balance_type", "balance_source_type",
        "budget_before", "budget_after", "status", "reason", "idempotency_key", "durable_source",
    ]
    _write_csv(root / "04_TOPUP_EVENTS_NORMALIZED.csv", normalized, norm_cols)

    budget_rows = [
        {
            "adv_id": b.get("adv_id"),
            "total": b.get("total"),
            "source": "GET /adv/v1/budget",
            "checked_at_msk": _iso_msk(checked_at),
        }
        for b in campaign_budgets
    ]
    _write_csv(
        root / "05_CAMPAIGN_BUDGET_BALANCES.csv",
        budget_rows,
        ["adv_id", "total", "source", "checked_at_msk"],
    )

    _write_csv(
        root / "06_GROSS_AD_SPEND_DAILY.csv",
        list(spend_daily.values()),
        [
            "date", "day_state", "gross_ad_spend", "campaigns_with_spend",
            "source", "dedupe_note",
        ],
    )

    _write_csv(
        root / "07_FACTUAL_SALES_DAILY.csv",
        list(sales_daily.values()),
        [
            "date", "day_state", "purchase_events", "units", "factual_order_value",
            "cancellation_semantics", "source", "cancelled_rows_excluded",
        ],
    )

    drr_daily: list[dict[str, Any]] = []
    d = COLLECT_FROM
    while d <= open_d:
        key = d.isoformat()
        sd = sales_daily[key]
        sp = spend_daily[key]
        tp = topup_daily[key]
        sales_val = float(sd.get("factual_order_value") or 0)
        spend_val = float(sp.get("gross_ad_spend") or 0)
        state = sd.get("day_state", "")
        gaps_row: list[str] = []
        if state == "OPEN":
            gaps_row.append("OPEN_DAY_NOT_IN_CLOSED_DRR_WINDOWS")
        drr_daily.append(
            {
                "date": key,
                "day_state": state,
                "factual_order_value": sales_val,
                "gross_ad_spend": spend_val,
                "gross_drr": _drr_pct(spend_val, sales_val) if state != "OPEN" else "OPEN_PARTIAL",
                "promo_bonus_used_on_deposits": tp.get("promo_bonus_used_on_deposits"),
                "ordinary_funds_used_on_deposits": tp.get("ordinary_funds_used_on_deposits"),
                "total_deposits": tp.get("total_deposits"),
                "opening_campaign_budget_total": "GAP",
                "closing_campaign_budget_total": sum(
                    int(b.get("total") or 0) for b in campaign_budgets
                ),
                "promo_funded_ad_spend": "GAP",
                "cash_funded_ad_spend": "GAP",
                "promo_adjusted_drr": "GAP",
                "accounting_status": accounting_status,
                "source_sales": sd.get("source"),
                "source_spend": sp.get("source"),
                "source_promo": tp.get("source"),
                "checked_at_msk": _iso_msk(checked_at),
                "gaps": ";".join(gaps_row) if gaps_row else "",
            }
        )
        d += timedelta(days=1)

    drr_cols = [
        "date", "day_state", "factual_order_value", "gross_ad_spend", "gross_drr",
        "promo_bonus_used_on_deposits", "ordinary_funds_used_on_deposits", "total_deposits",
        "opening_campaign_budget_total", "closing_campaign_budget_total",
        "promo_funded_ad_spend", "cash_funded_ad_spend", "promo_adjusted_drr",
        "accounting_status", "source_sales", "source_spend", "source_promo",
        "checked_at_msk", "gaps",
    ]
    _write_csv(root / "08_DRR_DAILY.csv", drr_daily, drr_cols)

    last3_from = closed_end - timedelta(days=2)
    last7_from = closed_end - timedelta(days=6)
    window_rows = [
        _window_aggregate(
            "FIXED_20260830_20260905",
            FIXED_FROM,
            FIXED_TO,
            sales_daily,
            spend_daily,
            topup_daily,
            closed_end,
            accounting_status,
            "Independent re-check of Web chat window; closed days only",
        ),
        _window_aggregate(
            "LAST_3_CLOSED",
            last3_from,
            closed_end,
            sales_daily,
            spend_daily,
            topup_daily,
            closed_end,
            accounting_status,
            f"Last 3 fully closed days ending {closed_end.isoformat()}",
        ),
        _window_aggregate(
            "LAST_7_CLOSED",
            last7_from,
            closed_end,
            sales_daily,
            spend_daily,
            topup_daily,
            closed_end,
            accounting_status,
            f"Rolling 7 fully closed days ending {closed_end.isoformat()}",
        ),
    ]
    win_cols = [
        "window_label", "period_from", "period_to", "days",
        "factual_order_value", "gross_ad_spend", "gross_drr",
        "promo_bonus_used_on_deposits", "ordinary_funds_used_on_deposits",
        "promo_funded_ad_spend", "cash_funded_ad_spend", "promo_adjusted_drr",
        "accounting_status", "notes",
    ]
    _write_csv(root / "09_DRR_WINDOWS.csv", window_rows, win_cols)

    spend_by_adv: dict[int, float] = defaultdict(float)
    for row in day_rows:
        adv_id = int(row.get("advert_id") or 0)
        day = str(row.get("date") or "")
        if not adv_id or not day:
            continue
        try:
            dday = date.fromisoformat(day)
        except ValueError:
            continue
        if dday < FIXED_FROM or dday > closed_end:
            continue
        spend_by_adv[adv_id] += float(row.get("day_spend") or 0)

    recon_rows = _campaign_promo_reconciliation(
        normalized, spend_by_adv, campaign_budgets, inventory
    )
    _write_csv(
        root / "10_CAMPAIGN_PROMO_RECONCILIATION.csv",
        recon_rows,
        [
            "adv_id", "campaign_name", "gross_spend_window", "deposit_total_success",
            "promo_amount_deposits", "ordinary_amount_deposits", "promo_share_of_funding_pct",
            "current_campaign_budget_total", "opening_campaign_budget", "closing_campaign_budget",
            "priority5_nm",
        ],
    )

    fixed = window_rows[0]
    accounting_md = "\n".join(
        [
            "# Accounting reconciliation",
            "",
            f"**Status: {accounting_status}**",
            "",
            "## What we know",
            "",
            f"- Gross ad spend (fullstats campaign-day, cabinet-wide {len(cabinet_adv_ids)} campaigns)",
            f"- Factual placed orders (supplier orders, cancellations excluded)",
            f"- Promo bonus actually used on successful deposits (WBAutoBudgetTopUp, status=success)",
            f"- Ordinary funds on same deposits (deposit amount minus cashback_sum)",
            "",
            "## What we cannot honestly claim",
            "",
            "- `PROMO_ADJUSTED_AD_COST = GROSS_AD_SPEND - PROMO_BONUS_USED` for same calendar period",
            "- Daily `promo_funded_ad_spend` / `cash_funded_ad_spend` split on spend",
            "- Historical opening/closing campaign wallet time series (only current budget snapshot)",
            "",
            "## Deposit flow vs spend timing",
            "",
            "Promo is consumed at **top-up** time; ad spend may occur later.",
            "Without spend-source provenance in fullstats, deposit-day promo usage",
            "does not map to same-day ad spend.",
            "",
            "## Window metrics (closed days)",
            "",
            f"- FIXED 2026-08-30..2026-09-05: sales={fixed['factual_order_value']} ₽, "
            f"spend={fixed['gross_ad_spend']} ₽, gross_drr={fixed['gross_drr']}%",
            f"- Web reference: sales≈561502, spend≈27949, gross_drr≈4.98%",
            "",
        ]
    )
    (root / "11_ACCOUNTING_RECONCILIATION.md").write_text(accounting_md, encoding="utf-8")

    critical_gaps = list(gaps_verify)
    critical_gaps.extend(
        [
            "PROMO_ADJUSTED_DRR_NOT_EMITTED (CASH_FLOW_ONLY)",
            "SPEND_SOURCE_ATTRIBUTION_UNAVAILABLE",
            "HISTORICAL_CAMPAIGN_BUDGET_OPEN_CLOSE_DAILY_GAP",
            "TOPUP_JOURNAL_COVERS_BOT_AUTO_DEPOSITS_ONLY (manual deposits may be missing)",
        ]
    )
    if not topup_raw_deduped:
        critical_gaps.append("NO_TOPUP_EVENTS_IN_WINDOW")

    dq = "\n".join(
        [
            "# Data Quality and Gaps",
            "",
            f"- shop_id: `{SHOP_ID}`",
            f"- wb_cabinet_id: `{wb_cabinet_id}` (verified expected 401: {wb_cabinet_id == 401})",
            f"- last_fully_closed_day: `{closed_end.isoformat()}`",
            f"- open_day: `{open_d.isoformat()}`",
            f"- cabinet_campaigns: {len(campaigns)}",
            f"- fullstats_adv_ids_queried: {len(cabinet_adv_ids)}",
            f"- supplier_orders_raw_rows: {len(orders_raw)}",
            f"- topup_events_raw: {len(topup_raw_deduped)} (deduped by idempotency_key)",
            f"- accounting_status: {accounting_status}",
            "",
            "## Critical gaps",
            "",
        ]
        + [f"- {g}" for g in critical_gaps]
    )
    (root / "12_DATA_QUALITY_AND_GAPS.md").write_text(dq, encoding="utf-8")

    qa = "\n".join(
        [
            "# Master QA Report (collector draft)",
            "",
            f"Package `{PACKAGE}` at {_iso_msk(checked_at)}.",
            f"Accounting: {accounting_status}. promo_adjusted_drr: NOT EMITTED.",
            f"FIXED window gross_drr={fixed['gross_drr']}% vs Web 4.98%.",
            "MASTER should rewrite.",
        ]
    )
    (root / "13_MASTER_QA_REPORT.md").write_text(qa, encoding="utf-8")

    human = "\n".join(
        [
            "# Human Summary",
            "",
            "## Scale vs efficiency (do not equate low DRR with 'good')",
            "",
            f"- **Sales scale (FIXED window)**: {fixed['factual_order_value']:,.0f} ₽ factual placed orders",
            f"- **Gross ad load**: {fixed['gross_ad_spend']:,.0f} ₽ → gross DRR **{fixed['gross_drr']}%**",
            f"- **Promo on deposits (FIXED)**: {fixed['promo_bonus_used_on_deposits']:,.0f} ₽",
            f"- **Own-money on deposits (FIXED)**: {fixed['ordinary_funds_used_on_deposits']:,.0f} ₽",
            "",
            f"- **LAST_3_CLOSED** gross DRR: {window_rows[1]['gross_drr']}% "
            f"(sales {window_rows[1]['factual_order_value']:,.0f} ₽)",
            f"- **LAST_7_CLOSED** gross DRR: {window_rows[2]['gross_drr']}% "
            f"(sales {window_rows[2]['factual_order_value']:,.0f} ₽)",
            "",
            "## Promo pool (current snapshot)",
            "",
            f"- Net: {central.get('net')} ₽; cashbacks: {balance_snapshot['cashbacks']}",
            "",
            "## promo_adjusted_drr",
            "",
            "**Not emitted** — spend does not retain promo vs cash provenance (CASH_FLOW_ONLY).",
            "",
            f"Open day {open_d.isoformat()} reported separately; excluded from closed DRR windows.",
        ]
    )
    (root / "14_HUMAN_SUMMARY.md").write_text(human, encoding="utf-8")

    manifest = {
        "package": PACKAGE,
        "artifact_class": "A1_PROMO_ADJUSTED_DRR",
        "primary_zip_basename": f"{PACKAGE}.zip",
        "shop_id": SHOP_ID,
        "wb_cabinet_id": wb_cabinet_id,
        "created_at_msk": _iso_msk(checked_at),
        "last_fully_closed_day": closed_end.isoformat(),
        "open_day": open_d.isoformat(),
        "accounting_status": accounting_status,
        "promo_adjusted_drr_emitted": False,
        "fixed_window": fixed,
        "counts": {
            "campaigns": len(campaigns),
            "cabinet_adv_ids": len(cabinet_adv_ids),
            "orders_raw": len(orders_raw),
            "topup_events": len(topup_raw_deduped),
            "topup_success": sum(1 for r in normalized if r.get("status") == "success"),
        },
        "critical_gaps": critical_gaps,
    }
    (root / "00_MANIFEST.json").write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8"
    )

    findings = evidence.secret_scan(root)
    if findings:
        raise SystemExit(f"Secret scan failed: {findings[:3]}")

    archive, digest = evidence.archive_directory(root)
    return {
        "EXECUTION_STATUS": "COMPLETE",
        "PACKAGE": PACKAGE,
        "SHOP_ID": SHOP_ID,
        "WB_CABINET_ID": wb_cabinet_id,
        "LAST_FULLY_CLOSED_DAY": closed_end.isoformat(),
        "ACCOUNTING_STATUS": accounting_status,
        "FIXED_WINDOW": fixed,
        "ZIP_ABSOLUTE_PATH": str(archive.resolve()),
        "ZIP_SHA256": digest,
        "PRIMARY_ARTIFACT": archive.name,
        "CRITICAL_GAPS": critical_gaps,
    }


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="A1 promo-adjusted DRR / cash ad cost READ_ONLY collector."
    )
    parser.add_argument(
        "--output-dir",
        default=".tmp/a1_promo_adjusted_drr",
        help="Output directory (will be zipped)",
    )
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    out = Path(args.output_dir).resolve()
    result = run_collect(out)
    print(json.dumps(result, ensure_ascii=False, indent=2))
    print(f"PRIMARY_SHA256={result['ZIP_SHA256']}")
    print("ops-script: success; holding for output copy")
    return 0


if __name__ == "__main__":
    sys.exit(main())
