"""Mapping from reason codes to human-readable text for the bot UI."""

from __future__ import annotations

from app.modules.shop_runner.service_manager.services.redis_campaign_activity_reason_manager.enums import (
    AuctionReasonCode,
    AutoReasonCode,
)

REASON_CODE_TO_DISPLAY_TEXT: dict[str, str] = {
    # Common
    AutoReasonCode.COMMON_LIMIT_0.value: "Об лим не задан",
    AutoReasonCode.COMMON_SPEND_EXCEEDED.value: "Об лим исч",
    AutoReasonCode.COMMON_TOTAL_EXCEEDED.value: "Об абс лим исч",
    AutoReasonCode.COMMON_TOTAL_UNKNOWN.value: "Об абс лим: расх н/д, пауза",
    AuctionReasonCode.COMMON_LIMIT_0.value: "Об лим не зад",
    AuctionReasonCode.COMMON_SPEND_EXCEEDED.value: "Об лим исч",
    AuctionReasonCode.COMMON_TOTAL_EXCEEDED.value: "Об абс лим исч",
    AuctionReasonCode.COMMON_TOTAL_UNKNOWN.value: "Об абс лим: расх н/д, пауза",
    # Auto
    AutoReasonCode.AUTO_LIMIT_0.value: "Лим Авто не зад",
    AutoReasonCode.AUTO_SPEND_EXCEEDED.value: "Лим Авто исч",
    AutoReasonCode.AUTO_TOTAL_EXCEEDED.value: "Абс лим Авто исч",
    AutoReasonCode.AUTO_TOTAL_UNKNOWN.value: "Абс лим Авто: расх н/д, пауза",
    AutoReasonCode.COST_DATA_INSUFFICIENT.value: "Н/д по себес",
    AutoReasonCode.COST_RULE_FAILED.value: "Прав по себес не вып",
    AutoReasonCode.TIME_SCHEDULE.value: "Вне расп пок",
    AutoReasonCode.REC_SYSTEM_MODE_OFF.value: "Режим раскр вык",
    AutoReasonCode.BUDGET_OK_COST_OK.value: "Бюд и себес в норме, зап",
    AutoReasonCode.INSUFFICIENT_BALANCE.value: "Недостаточно средств",
    AutoReasonCode.EMPTY_KEYWORDS.value: "Нет акт ключей",
    AutoReasonCode.SHELF_EXHAUSTED_NO_PLAN.value: "Полки: нет ставки под план",
    # Auction
    AuctionReasonCode.COMMON_OK.value: "Об бюд в норме, зап",
    AuctionReasonCode.SEARCH_SPEND_EXCEEDED.value: "Лимит Аук исч",
    AuctionReasonCode.SEARCH_LIMIT_OK.value: "Лим Аук в норме, запущ",
    AuctionReasonCode.SEARCH_LIMIT_0.value: "Лим Аук не зад",
    AuctionReasonCode.SEARCH_TOTAL_EXCEEDED.value: "Абс лим Аук исч",
    AuctionReasonCode.SEARCH_TOTAL_UNKNOWN.value: "Абс лим Аук: расх н/д, пауза",
    AuctionReasonCode.TIME_SCHEDULE.value: "Вне рас пок",
    # Тот же UI-label, что у Auto enum value (shared string empty_keywords)
    AuctionReasonCode.EMPTY_KEYWORDS.value: "Нет акт ключей",
}


def reason_code_to_display_text(reason_code_value: str) -> str:
    """Return human-readable text for a reason code value. Fallback to the raw value."""
    return REASON_CODE_TO_DISPLAY_TEXT.get(reason_code_value, reason_code_value)
