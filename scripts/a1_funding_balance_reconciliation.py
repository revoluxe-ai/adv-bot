"""READ_ONLY: фактический баланс финансирования рекламы A1 (WB Promotion).

Собирает GET /adv/v1/balance, GET /adv/v1/budget по active РК,
строит reconciliation без double-counting и runway-арифметику.
Никаких writes.
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
    ACTIVE_STATUSES,
    SHOP_ID,
    WB_CABINET_ID_EXPECTED,
    _api_model_dict,
    _bootstrap_cluster_infra,
    _build_auto_topup_state,
    _cashbacks_to_list,
    _collect_wb_funding,
    _load_adv_settings,
)

MSK = ZoneInfo("Europe/Moscow")
DAILY_BASELINE_RUB = 4389.24
RUNWAY_SCENARIOS = (4000.0, 4500.0, 5000.0)
RUNWAY_END_DATE = "2026-08-31"


def _msk_now() -> datetime:
    return datetime.now(timezone.utc).astimezone(MSK)


def _fund_item(
    *,
    value_rub: int | float | None,
    endpoint: str,
    field: str,
    meaning: str,
    spendable: bool,
    notes: str = "",
) -> dict[str, Any]:
    return {
        "value_rub": value_rub,
        "endpoint": endpoint,
        "field": field,
        "meaning": meaning,
        "directly_spendable_for_ads": spendable,
        "notes": notes,
    }


def _infer_budget_in_total_balance() -> str:
    """Отношение бюджета РК к центральному пулу (по контракту WB deposit API)."""
    return (
        "Campaign budget (GET /adv/v1/budget.total) — средства, уже переведённые "
        "из центральных пулов (balance/net/bonus) через POST /adv/v1/budget/deposit. "
        "При пополнении central net/balance уменьшается, campaign total растёт. "
        "Это разные срезы одного promotion-контура, не независимые кошельки."
    )


def _build_double_counting_relation(
    central: dict[str, Any],
    sum_campaign_budgets: int,
) -> dict[str, Any]:
    balance = int(central.get("balance") or 0)
    net = int(central.get("net") or 0)
    bonus = int(central.get("bonus") or 0)
    naive_sum_net_plus_budgets = net + sum_campaign_budgets
    correct_total = balance + net + bonus + sum_campaign_budgets
    return {
        "campaign_budgets_already_deducted_from_central_pools": "YES",
        "campaign_budgets_are_separate_additional_funds": "NO",
        "can_sum_promotion_wallet_plus_wb_net_plus_campaign_budgets": "YES_WITH_FORMULA",
        "wrong_formula_example": (
            "Нельзя трактовать net как «весь доступный остаток» без учёта "
            "уже размещённых в РК budget.total; также нельзя повторно использовать "
            "оценку net+budgets как третью строку, если она уже и есть итог."
        ),
        "correct_formula": (
            "TOTAL_AVAILABLE_FOR_AD_SPEND = "
            "balance + net + bonus + SUM(active_campaign_budget.total)"
        ),
        "components_rub": {
            "balance": balance,
            "net": net,
            "bonus": bonus,
            "sum_active_campaign_budgets": sum_campaign_budgets,
        },
        "naive_net_plus_budgets_rub": naive_sum_net_plus_budgets,
        "note_on_47146_estimate": (
            "При balance=0 и bonus=0 формула net+SUM(budgets) совпадает с корректным "
            "итогом, но это не «отдельная третья сумма» — это и есть total. "
            "Пересечение возникает, если net ошибочно принять за gross до аллокации "
            "или сложить net с budgets, уже включёнными в отображаемый net в UI."
        ),
        "explanation": _infer_budget_in_total_balance(),
    }


def _runway_section(total_available: float) -> dict[str, Any]:
    runway_days = total_available / DAILY_BASELINE_RUB if DAILY_BASELINE_RUB else None
    days_to_end_aug = 3  # 28,29,30,31 from snapshot on 28th -> spend through 31 = 4 days? 
    # User asked: сколько останется к концу 31.08 при расходе X/день
    # From 28.08 evening snapshot, days remaining: 28 (partial spent), 29, 30, 31 = up to 4 days
    # Use calendar: from checked_at date inclusive through 31.08
    checked = _msk_now().date()
    end = datetime.strptime(RUNWAY_END_DATE, "%Y-%m-%d").date()
    days_remaining = max((end - checked).days + 1, 0)
    scenario_projections: dict[str, Any] = {}
    for daily in RUNWAY_SCENARIOS:
        projected_spend = daily * days_remaining
        remaining = total_available - projected_spend
        scenario_projections[f"{int(daily)}_rub_per_day"] = {
            "days_in_window": days_remaining,
            "projected_spend_through_end_date": round(projected_spend, 2),
            "remaining_at_end_of_period_rub": round(remaining, 2),
        }
    return {
        "daily_baseline_rub": DAILY_BASELINE_RUB,
        "daily_baseline_source": "store full-contour ad spend 2026-08-27 closed day",
        "runway_days_arithmetic": (
            round(runway_days, 2) if runway_days is not None else None
        ),
        "runway_formula": "non_double_counted_available_balance / 4389.24",
        "projection_window": {
            "from_date_msk": checked.isoformat(),
            "through_date_msk": RUNWAY_END_DATE,
            "days_counted": days_remaining,
        },
        "scenarios_through_end_date": scenario_projections,
        "reaches_2026_09_01_without_topup": (
            "YES" if runway_days is not None and runway_days >= days_remaining else "NO"
            if runway_days is not None
            else "UNKNOWN"
        ),
    }


def _build_campaign_table(
    budgets: list[dict[str, Any]],
    settings_rows: list[dict[str, str]],
) -> list[dict[str, Any]]:
    settings_by_adv: dict[str, dict[str, str]] = {}
    for row in settings_rows:
        adv_id = str(row.get("adv_id") or "")
        if adv_id:
            settings_by_adv[adv_id] = row

    rows: list[dict[str, Any]] = []
    for item in sorted(budgets, key=lambda x: int(x.get("adv_id") or 0)):
        adv_id = int(item.get("adv_id") or 0)
        setting = settings_by_adv.get(str(adv_id), {})
        rows.append(
            {
                "adv_id": adv_id,
                "name": item.get("name"),
                "status": item.get("status"),
                "current_campaign_budget_rub": int(item.get("total") or 0),
                "budget_endpoint": "GET /adv/v1/budget",
                "budget_field": "total",
                "funding_source": "UNKNOWN_PER_CAMPAIGN_API",
                "funding_source_notes": (
                    "WB API не возвращает per-campaign источник (balance/net/bonus). "
                    "Bot watchdog при top-up выбирает lowest non-bonus pool ≥ threshold "
                    "(balance_source.py)."
                ),
                "bot_watchdog_enabled": setting.get("auto_budget_watchdog_enabled"),
                "included_in_total_available_formula": "YES",
                "double_count_risk_with_central_net": "NO",
            }
        )
    return rows


def _build_gaps(
    central: dict[str, Any],
    auto_topup: dict[str, Any],
    budget_errors: list[str],
) -> list[dict[str, Any]]:
    gaps: list[dict[str, Any]] = []
    if auto_topup.get("wb_cabinet_native_autoreplenishment_api") == "NOT_AVAILABLE_IN_API":
        gaps.append(
            {
                "kind": "API_GAP",
                "missing": "WB native autoreplenishment per campaign (enabled/source/threshold/amount)",
                "ui_evidence_needed": (
                    "Seller UI → Promotion → campaign budget settings: autoreplenishment toggle, "
                    "source account, threshold, replenishment amount."
                ),
                "api_confirmed": [
                    "GET /adv/v1/balance (balance, net, bonus, cashbacks)",
                    "GET /adv/v1/budget (total per adv_id)",
                ],
                "guaranteed_lower_bound_possible": True,
            }
        )
    if central.get("bonus") is None:
        gaps.append(
            {
                "kind": "API_GAP",
                "missing": "bonus field returned as null/unset",
                "ui_evidence_needed": "Promotion balance screen: bonus line if shown",
                "api_confirmed": ["balance", "net"],
                "guaranteed_lower_bound_possible": True,
            }
        )
    for err in budget_errors:
        gaps.append({"kind": "BUDGET_API_ERROR", "detail": err})
    return gaps


def _render_md(payload: dict[str, Any]) -> str:
    checked = payload["checked_at"]
    total = payload["TOTAL_AVAILABLE_FOR_AD_SPEND"]["value_rub"]
    runway = payload["RUNWAY_TO_2026_09_01"]
    lines = [
        "# A1 — FACTUAL ADVERTISING FUNDING BALANCE",
        "",
        f"**checked_at (MSK):** {checked}",
        f"**shop_id:** `{payload['shop_id']}` · **wb_cabinet_id:** {payload['wb_cabinet_id']}",
        f"**mode:** {payload['mode']}",
        "",
        "## Central pools (unallocated)",
        "",
        "| Pool | ₽ | Spendable |",
        "|------|---|-----------|",
    ]
    for key in ("PROMOTION_WALLET", "WB_NET", "OTHER_AVAILABLE_FUNDS"):
        block = payload.get(key)
        if isinstance(block, list):
            for item in block:
                lines.append(
                    f"| {item['field']} | {item['value_rub']} | "
                    f"{'YES' if item['directly_spendable_for_ads'] else 'NO'} |"
                )
        elif isinstance(block, dict) and "value_rub" in block:
            lines.append(
                f"| {block['field']} | {block['value_rub']} | "
                f"{'YES' if block['directly_spendable_for_ads'] else 'NO'} |"
            )

    lines.extend([
        "",
        "## Active campaign budgets",
        "",
        f"**SUM_ACTIVE_CAMPAIGN_BUDGETS:** {payload['ACTIVE_CAMPAIGN_BUDGETS']['sum_rub']} ₽ "
        f"({payload['ACTIVE_CAMPAIGN_BUDGETS']['count']} campaigns, status 9)",
        "",
        "## Double-counting",
        "",
        f"- Campaign budgets deducted from central: "
        f"**{payload['DOUBLE_COUNTING_RELATION']['campaign_budgets_already_deducted_from_central_pools']}**",
        f"- **Formula:** `{payload['DOUBLE_COUNTING_RELATION']['correct_formula']}`",
        f"- **TOTAL_AVAILABLE_FOR_AD_SPEND:** **{total} ₽**",
        f"- **GUARANTEED_LOWER_BOUND:** **{payload['GUARANTEED_LOWER_BOUND']['value_rub']} ₽** "
        f"({payload['GUARANTEED_LOWER_BOUND']['basis']})",
        "",
        "## Runway (arithmetic)",
        "",
        f"- Baseline: **{runway['daily_baseline_rub']} ₽/day** (27.08 store spend)",
        f"- RUNWAY_DAYS: **{runway['runway_days_arithmetic']}**",
        f"- Reaches 01.09 without topup (arithmetic): **{runway['reaches_2026_09_01_without_topup']}**",
        "",
    ])
    for label, data in runway["scenarios_through_end_date"].items():
        lines.append(
            f"- {label}: spend **{data['projected_spend_through_end_date']} ₽** → "
            f"remain **{data['remaining_at_end_of_period_rub']} ₽**"
        )
    if payload["GAPS"]:
        lines.extend(["", "## GAPS", ""])
        for gap in payload["GAPS"]:
            lines.append(f"- **{gap.get('kind')}**: {gap.get('missing', gap.get('detail', ''))}")
    return "\n".join(lines)


async def run_reconciliation(
    output_dir: Path,
    wb_cabinet_id: int,
    settings_rows: list[dict[str, str]],
) -> dict[str, Any]:
    """Собрать funding reconciliation и сохранить JSON + MD."""
    output_dir.mkdir(parents=True, exist_ok=True)
    wb_data = await _collect_wb_funding()
    auto_topup = _build_auto_topup_state(settings_rows)
    central_raw = wb_data["central"]
    budgets = wb_data["campaign_budgets"]

    balance = int(central_raw.get("balance") or 0)
    net = int(central_raw.get("net") or 0)
    bonus_raw = central_raw.get("bonus")
    bonus = int(bonus_raw) if bonus_raw is not None else 0
    cashbacks = central_raw.get("cashbacks") or []
    sum_budgets = sum(int(b.get("total") or 0) for b in budgets)

    checked_msk = _msk_now()
    double_rel = _build_double_counting_relation(central_raw, sum_budgets)
    total_available = balance + net + bonus + sum_budgets
    guaranteed_lower = sum_budgets  # allocated budgets are immediately spendable

    payload: dict[str, Any] = {
        "checked_at": checked_msk.strftime("%Y-%m-%d %H:%M:%S %Z"),
        "checked_at_utc": datetime.now(timezone.utc).isoformat(),
        "shop_id": SHOP_ID,
        "wb_cabinet_id": wb_cabinet_id,
        "mode": "STRICT_READ_ONLY",
        "PROMOTION_WALLET": _fund_item(
            value_rub=balance,
            endpoint="GET /adv/v1/balance",
            field="balance",
            meaning="Счёт WB Продвижение (центральный нераспределённый пул)",
            spendable=True,
            notes="Используется для POST /adv/v1/budget/deposit type=0",
        ),
        "WB_NET": _fund_item(
            value_rub=net,
            endpoint="GET /adv/v1/balance",
            field="net",
            meaning="Баланс WB Продвижение / взаимозачёт (центральный нераспределённый пул)",
            spendable=True,
            notes="Используется для POST /adv/v1/budget/deposit type=1",
        ),
        "OTHER_AVAILABLE_FUNDS": [
            _fund_item(
                value_rub=bonus_raw if bonus_raw is not None else None,
                endpoint="GET /adv/v1/balance",
                field="bonus",
                meaning="Бонусы WB Продвижение",
                spendable=True,
                notes="type=3 при deposit; API может вернуть null",
            ),
            *[
                _fund_item(
                    value_rub=cb.get("sum"),
                    endpoint="GET /adv/v1/balance",
                    field="cashbacks[].sum",
                    meaning=(
                        f"Promo cashback (percent={cb.get('percent')}, "
                        f"exp={cb.get('expiration_date')})"
                    ),
                    spendable=False,
                    notes="Cashback применяется при top-up, не отдельный spendable pool",
                )
                for cb in cashbacks
            ],
        ],
        "ACTIVE_CAMPAIGN_BUDGETS": {
            "count": len(budgets),
            "sum_rub": sum_budgets,
            "status_filter": sorted(ACTIVE_STATUSES),
            "endpoint": "GET /adv/v1/budget",
            "field": "total",
            "campaigns": _build_campaign_table(budgets, settings_rows),
        },
        "DOUBLE_COUNTING_RELATION": double_rel,
        "TOTAL_AVAILABLE_FOR_AD_SPEND": {
            "value_rub": total_available,
            "formula": double_rel["correct_formula"],
            "components_rub": double_rel["components_rub"],
        },
        "GUARANTEED_LOWER_BOUND": {
            "value_rub": guaranteed_lower,
            "basis": (
                "SUM(active campaign budget.total) — подтверждено API, "
                "немедленно доступно для списания рекламы без нового deposit"
            ),
        },
        "RUNWAY_TO_2026_09_01": _runway_section(float(total_available)),
        "AUTO_TOPUP_STATE": auto_topup,
        "GAPS": _build_gaps(central_raw, auto_topup, wb_data["budget_errors"]),
        "meta": {
            "all_adv_ids_count": wb_data["all_adv_ids_count"],
            "active_adv_ids_count": wb_data["active_adv_ids_count"],
            "budget_api_errors": wb_data["budget_errors"],
            "wb_cabinet_id_expected": WB_CABINET_ID_EXPECTED,
        },
    }

    json_path = output_dir / "A1_FUNDING_BALANCE_RECONCILIATION.json"
    md_path = output_dir / "A1_FUNDING_BALANCE_RECONCILIATION.md"
    json_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    md_path.write_text(_render_md(payload), encoding="utf-8")
    payload["output_paths"] = {
        "json": str(json_path.resolve()),
        "md": str(md_path.resolve()),
    }
    return payload


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="A1 factual advertising funding balance reconciliation (READ_ONLY)."
    )
    parser.add_argument("--output-dir", default=".tmp/a1_funding_balance_reconciliation")
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    out = Path(args.output_dir).resolve()
    _bootstrap_cluster_infra()
    wb_cabinet_id, settings_rows = _load_adv_settings(out)
    result = asyncio.run(run_reconciliation(out, wb_cabinet_id, settings_rows))
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
