"""RaisePlanOnPromobonuses: тексты Telegram-тумблера."""

from __future__ import annotations

from app.shared.domains.wb.utils.promo_plan_multiplier import (
    PROMO_AUTO_BUDGET_LABEL,
    PROMO_MAX_CPO_LABEL,
    PROMO_TARGET_BUDGET_LABEL,
    PROMO_TARGET_CPO_LABEL,
    PROPO_SEARCH_BUDGET_LABEL,
)


def format_raise_plan_on_promobonuses_toggle_message(*, enabled: bool) -> str:
    """Текст уведомления при переключении RaisePlanOnPromobonuses."""
    if enabled:
        return (
            "RaisePlanOnPromobonuses включено. "
            f"При usable promo применяются {PROMO_MAX_CPO_LABEL}, "
            f"{PROMO_TARGET_CPO_LABEL}, {PROMO_AUTO_BUDGET_LABEL}, "
            f"{PROPO_SEARCH_BUDGET_LABEL}, {PROMO_TARGET_BUDGET_LABEL}."
        )
    return "RaisePlanOnPromobonuses отключено."
