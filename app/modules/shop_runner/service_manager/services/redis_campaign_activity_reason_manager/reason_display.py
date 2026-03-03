"""Mapping from reason codes to human-readable text for the bot UI."""

from __future__ import annotations

from app.modules.shop_runner.service_manager.services.redis_campaign_activity_reason_manager.enums import (
    AuctionReasonCode,
    AutoReasonCode,
)

REASON_CODE_TO_DISPLAY_TEXT: dict[str, str] = {
    # Common
    AutoReasonCode.COMMON_LIMIT_0.value: "Общий лимит не задан",
    AutoReasonCode.COMMON_SPEND_EXCEEDED.value: "Общий лимит исчерпан",
    AuctionReasonCode.COMMON_LIMIT_0.value: "Общий лимит не задан",
    AuctionReasonCode.COMMON_SPEND_EXCEEDED.value: "Общий лимит исчерпан",
    # Auto
    AutoReasonCode.AUTO_LIMIT_0.value: "Лимит Авто не задан",
    AutoReasonCode.AUTO_SPEND_EXCEEDED.value: "Лимит Авто исчерпан",
    AutoReasonCode.COST_DATA_INSUFFICIENT.value: "Недостаточно данных по себестоимости",
    AutoReasonCode.COST_RULE_FAILED.value: "Правило по себестоимости не выполнено",
    AutoReasonCode.TIME_SCHEDULE.value: "Вне расписания показов",
    AutoReasonCode.REC_SYSTEM_MODE_OFF.value: "Режим раскрутки выключен",
    AutoReasonCode.BUDGET_OK_COST_OK.value: "Бюджет и себестоимость в норме, запущена",
    # Auction
    AuctionReasonCode.COMMON_OK.value: "Общий бюджет в норме, запущена",
    AuctionReasonCode.SEARCH_SPEND_EXCEEDED.value: "Лимит Аукциона исчерпан",
    AuctionReasonCode.SEARCH_LIMIT_OK.value: "Лимит Аукциона в норме, запущена",
    AuctionReasonCode.SEARCH_LIMIT_0.value: "Лимит Аукциона не задан",
    AuctionReasonCode.TIME_SCHEDULE.value: "Вне расписания показов",
}


def reason_code_to_display_text(reason_code_value: str) -> str:
    """Return human-readable text for a reason code value. Fallback to the raw value."""
    return REASON_CODE_TO_DISPLAY_TEXT.get(reason_code_value, reason_code_value)
