"""READ_ONLY: A1 current advertising funding snapshot for growth iteration design.

Собирает GET /adv/v1/balance, GET /adv/v1/budget (active campaigns),
payment routing из balance_source.py, capacity arithmetic.
Никаких пополнений / writes.
"""

from __future__ import annotations

import argparse
import asyncio
import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from zoneinfo import ZoneInfo

from scripts.a1_promotion_funding_snapshot import (
    _bootstrap_cluster_infra,
    _build_auto_topup_state,
    _collect_wb_funding,
    _load_adv_settings,
)
from app.shared.domains.wb.utils.balance_source import (
    balance_snapshot_from_response,
    cashback_summary_from_response,
    select_topup_balance_decision,
)

MSK = ZoneInfo("Europe/Moscow")
PREV_SNAPSHOT_DATE = "2026-08-28"
PREV_WALLET = 0
PREV_NET = 21355
PREV_BONUS: int | None = None

DAILY_SCENARIOS = {
    "DAYS_AT_3754": 3753.69,
    "DAYS_AT_4900": 4900.0,
    "DAYS_AT_7500": 7500.0,
    "DAYS_AT_10000": 10000.0,
}


class _BalanceShim:
    """Minimal adapter for balance_source helpers."""

    def __init__(self, balance: int, net: int, bonus: int | None, cashbacks: list) -> None:
        self.balance = balance
        self.net = net
        self.bonus = bonus or 0
        self.cashbacks = cashbacks


def _msk_now() -> datetime:
    return datetime.now(timezone.utc).astimezone(MSK)


def _days_capacity(total_rub: float, daily: float) -> float | None:
    if daily <= 0:
        return None
    return round(total_rub / daily, 2)


def _fund_source(
    *,
    key: str,
    amount: int | float | None,
    endpoint: str,
    field: str,
    spendable: bool,
    notes: str,
    checked_at: str,
) -> dict[str, Any]:
    return {
        "source_key": key,
        "amount_rub": amount,
        "endpoint": endpoint,
        "field": field,
        "checked_at_msk": checked_at,
        "freshness": "live_wb_api_at_checked_at",
        "spendable_by_current_campaigns": spendable,
        "notes": notes,
    }


def build_payload(
    checked: datetime,
    wb_data: dict[str, Any],
    auto_topup: dict[str, Any],
) -> dict[str, Any]:
    central = wb_data["central"]
    budgets = wb_data["campaign_budgets"]
    balance = int(central.get("balance") or 0)
    net = int(central.get("net") or 0)
    bonus_raw = central.get("bonus")
    bonus_int = int(bonus_raw) if bonus_raw is not None else None
    cashbacks = central.get("cashbacks") or []
    sum_budgets = sum(int(b.get("total") or 0) for b in budgets)
    bonus_for_total = bonus_int if bonus_int is not None else 0
    total_available = balance + net + bonus_for_total + sum_budgets

    checked_str = checked.strftime("%Y-%m-%d %H:%M:%S %Z")
    shim = _BalanceShim(balance, net, bonus_int, cashbacks)
    snap = balance_snapshot_from_response(shim)
    min_balance = int(auto_topup["cluster_env"]["AUTO_BUDGET_MIN_BALANCE"])
    topup_amount = int(auto_topup["cluster_env"]["AUTO_BUDGET_TOPUP_AMOUNT"])
    try:
        topup_decision = select_topup_balance_decision(
            shim, topup_amount=topup_amount, min_required=min_balance
        )
        next_deposit_source = {
            "balance_name": topup_decision.balance_name,
            "balance_type_deposit": topup_decision.balance_type,
            "cashback_overlay": (
                {
                    "payable_rub": topup_decision.cashback.cashback_sum,
                    "percent": topup_decision.cashback.cashback_percent,
                    "expiration_date": topup_decision.cashback.expiration_date,
                }
                if topup_decision.cashback
                else None
            ),
            "rule": "balance_source.select_topup_balance_decision (lowest non-bonus pool >= threshold; bonus only if no non-bonus)",
        }
    except Exception as exc:  # noqa: BLE001
        next_deposit_source = {
            "status": "INSUFFICIENT_CENTRAL_POOL_FOR_BOT_TOPUP",
            "error": type(exc).__name__,
            "threshold_rub": min_balance,
            "topup_amount_rub": topup_amount,
        }

    cb_summary = cashback_summary_from_response(shim)
    funding_sources = [
        _fund_source(
            key="advertising_wallet",
            amount=balance,
            endpoint="GET /adv/v1/balance",
            field="balance",
            spendable=True,
            notes="Центральный пул «Счёт WB Продвижение»; пополнение РК через deposit type=0",
            checked_at=checked_str,
        ),
        _fund_source(
            key="wb_net",
            amount=net,
            endpoint="GET /adv/v1/balance",
            field="net",
            spendable=True,
            notes="Центральный пул взаимозачёта; deposit type=1",
            checked_at=checked_str,
        ),
        _fund_source(
            key="bonus_advertising",
            amount=bonus_raw if bonus_raw is not None else None,
            endpoint="GET /adv/v1/balance",
            field="bonus",
            spendable=bonus_raw is not None and int(bonus_raw or 0) > 0,
            notes="Бонусы WB; deposit type=3; API может вернуть null",
            checked_at=checked_str,
        ),
        _fund_source(
            key="active_campaign_budgets_allocated",
            amount=sum_budgets,
            endpoint="GET /adv/v1/budget",
            field="total (sum over active status=9 campaigns)",
            spendable=True,
            notes=(
                f"Уже переведено из central pools в {len(budgets)} active campaigns; "
                "немедленно списывается рекламой"
            ),
            checked_at=checked_str,
        ),
    ]
    if cb_summary.total > 0:
        funding_sources.append(
            _fund_source(
                key="promo_cashback_overlay",
                amount=cb_summary.total,
                endpoint="GET /adv/v1/balance",
                field="cashbacks[].sum",
                spendable=False,
                notes=(
                    "Не отдельный кошелёк; применяется при deposit/top-up "
                    f"(best_percent={cb_summary.best_percent}, "
                    f"earliest_exp={cb_summary.earliest_expiration_date})"
                ),
                checked_at=checked_str,
            )
        )

    prev_bonus_cmp = None if PREV_BONUS is None else PREV_BONUS
    change = {
        "reference_date": PREV_SNAPSHOT_DATE,
        "advertising_wallet_delta_rub": balance - PREV_WALLET,
        "wb_net_delta_rub": net - PREV_NET,
        "bonus_delta_rub": (
            "UNKNOWN_PREV_NULL"
            if bonus_int is None and PREV_BONUS is None
            else (bonus_int or 0) - (prev_bonus_cmp or 0)
        ),
        "note": (
            "2026-08-28 snapshot excluded campaign budget allocation; "
            "current total includes SUM(active campaign budget.total)"
        ),
    }

    capacity = {
        k: {
            "daily_spend_assumption_rub": v,
            "total_available_rub": total_available,
            "days": _days_capacity(total_available, v),
            "formula": "TOTAL_AVAILABLE_FOR_AD_SPEND / daily_spend_assumption",
        }
        for k, v in DAILY_SCENARIOS.items()
    }

    gaps: list[str] = []
    if bonus_raw is None:
        gaps.append("bonus_field_null_in_wb_api")
    gaps.append("per_campaign_payment_source_not_in_wb_api")
    gaps.append("wb_native_autoreplenishment_settings_not_in_api")
    if wb_data.get("budget_errors"):
        gaps.extend([f"budget_api_error:{e}" for e in wb_data["budget_errors"]])

    constraints: list[str] = []
    if isinstance(next_deposit_source, dict) and next_deposit_source.get("status"):
        constraints.append(
            f"Bot auto-topup may fail: no central pool >= {min_balance} ₽ "
            f"(pools: balance={balance}, net={net})"
        )
    low_budget = [b for b in budgets if int(b.get("total") or 0) < min_balance]
    if low_budget:
        constraints.append(
            f"{len(low_budget)} active campaigns below bot threshold {min_balance} ₽ "
            "(watchdog may attempt deposit)"
        )
    if max(balance, net) < topup_amount:
        constraints.append(
            f"Largest non-bonus central pool ({max(balance, net)} ₽) < top-up step ({topup_amount} ₽)"
        )

    return {
        "CHECKED_AT_MSK": checked_str,
        "STRICT_READ_ONLY": "CONFIRMED",
        "CURRENT_AD_FUNDS_AVAILABLE": {
            "total_rub": total_available,
            "formula": "balance + net + bonus + SUM(active_campaign_budget.total)",
            "components_rub": {
                "balance": balance,
                "net": net,
                "bonus": bonus_int,
                "sum_active_campaign_budgets": sum_budgets,
            },
            "guaranteed_immediately_spendable_rub": sum_budgets,
            "guaranteed_immediately_spendable_note": (
                "Campaign budget.total already inside active ads — spendable without new deposit"
            ),
        },
        "FUNDING_SOURCES": funding_sources,
        "CURRENT_PAYMENT_SOURCE": {
            "actual_ad_spend_draws_from": "GET /adv/v1/budget.total per active campaign (pre-deposited wallet)",
            "new_deposits_when_budget_low": next_deposit_source,
            "bot_watchdog_enabled_campaigns": len(auto_topup.get("watchdog_enabled_adv_settings", [])),
            "automatic_source_switching": (
                "YES for bot-initiated deposits — select_topup_balance_decision picks "
                "lowest non-bonus pool >= AUTO_BUDGET_MIN_BALANCE; may attach expiring cashback overlay"
            ),
            "campaign_type_restrictions_api": "GAP — WB API does not expose per-campaign-type funding restrictions",
            "on_current_source_exhaustion": (
                "Campaign pauses when budget.total depleted until new deposit from central pool "
                "(bot watchdog if enabled) or manual top-up; central pools are shared across campaigns"
            ),
            "wb_api_confirmed": ["GET /adv/v1/balance", "GET /adv/v1/budget"],
            "inferred_from_code": ["app/shared/domains/wb/utils/balance_source.py"],
        },
        "FUNDING_CONSTRAINT": constraints,
        "CHANGE_VS_2026_08_28": change,
        **capacity,
        "OPEN_GAPS": gaps,
        "meta": {
            "active_campaigns_count": len(budgets),
            "all_adv_ids_count": wb_data.get("all_adv_ids_count"),
            "cashbacks_detail": cashbacks,
            "auto_topup_cluster_env": auto_topup.get("cluster_env"),
        },
    }


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--output-dir", default=".tmp/a1_ad_funding_snapshot")
    args = ap.parse_args(argv)
    out = Path(args.output_dir).resolve()
    _bootstrap_cluster_infra()
    wb_cabinet_id, settings_rows = _load_adv_settings(out)

    async def _run() -> dict[str, Any]:
        out.mkdir(parents=True, exist_ok=True)
        wb_data = await _collect_wb_funding()
        auto_topup = _build_auto_topup_state(settings_rows)
        payload = build_payload(_msk_now(), wb_data, auto_topup)
        path = out / "A1-CURRENT-AD-FUNDING-SNAPSHOT.json"
        path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
        payload["output_path"] = str(path.resolve())
        return payload

    result = asyncio.run(_run())
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
