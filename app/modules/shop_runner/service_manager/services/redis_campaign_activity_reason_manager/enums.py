"""Enums for campaign activity reason: command and reason codes (shared by service and bot).

StrEnum does not support inheritance in Python, so AutoReasonCode and AuctionReasonCode
are standalone; common semantics (common_limit_0, common_spend_exceeded) are duplicated.
"""

from __future__ import annotations

from enum import StrEnum


class CampaignActivityCommand(StrEnum):
    """Command issued by the activity module: started or pause."""

    STARTED = "started"
    PAUSE = "pause"


class AutoReasonCode(StrEnum):
    """Reason codes for Auto campaign (includes common + auto-specific)."""

    COMMON_LIMIT_0 = "common_limit_0"
    COMMON_SPEND_EXCEEDED = "common_spend_exceeded"
    AUTO_LIMIT_0 = "auto_limit_0"
    AUTO_SPEND_EXCEEDED = "auto_spend_exceeded"
    COST_DATA_INSUFFICIENT = "cost_data_insufficient"
    COST_RULE_FAILED = "cost_rule_failed"
    TIME_SCHEDULE = "time_schedule"
    REC_SYSTEM_MODE_OFF = "rec_system_mode_off"
    BUDGET_OK_COST_OK = "budget_ok_cost_ok"
    INSUFFICIENT_BALANCE = "insufficient_balance_auto"
    # Shared value с AuctionReasonCode; INC-PAUSE-02 пишет pause на Search-lane.
    # Auto enum оставлен для parse_reason_code / legacy Redis Auto-lane.
    EMPTY_KEYWORDS = "empty_keywords"
    # INC-AUTO-SHELF-PAUSE-01: terminal Auto pause when shelf test epoch
    # exhausted without resolve-CPO plan-fit (Redis mirror; PG is SoT).
    SHELF_EXHAUSTED_NO_PLAN = "shelf_exhausted_no_plan"


class AuctionReasonCode(StrEnum):
    """Reason codes for Auction (search) campaign (includes common + auction-specific)."""

    COMMON_LIMIT_0 = "common_limit_0"
    COMMON_SPEND_EXCEEDED = "common_spend_exceeded"
    COMMON_OK = "common_ok"
    SEARCH_SPEND_EXCEEDED = "search_spend_exceeded"
    SEARCH_LIMIT_OK = "search_limit_ok"
    SEARCH_LIMIT_0 = "search_limit_0"
    TIME_SCHEDULE = "time_schedule"
    INSUFFICIENT_BALANCE = "insufficient_balance_auction"
    # Spec pause-on-empty-keywords (INC-PAUSE-02): пауза Search при пустых ключах
    EMPTY_KEYWORDS = "empty_keywords"


CampaignReasonCode = AutoReasonCode | AuctionReasonCode


def parse_reason_code(value: str) -> CampaignReasonCode | None:
    """Parse string from Redis into AutoReasonCode or AuctionReasonCode. Returns None if unknown."""
    try:
        return AutoReasonCode(value)
    except ValueError:
        pass
    try:
        return AuctionReasonCode(value)
    except ValueError:
        return None
