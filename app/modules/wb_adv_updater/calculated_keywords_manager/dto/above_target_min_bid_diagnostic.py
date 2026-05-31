"""Диагностика правила МС (above target at min bid) для UI и debug.

Зеркалит фактический outcome ``apply_above_target_min_bid_cooldown`` без изменения
бизнес-логики блокировки.
"""

from __future__ import annotations

from enum import StrEnum

from pydantic import BaseModel

from app.modules.wb_adv_updater.calculated_keywords_manager.dto.states import (
    KeywordStatus,
    KeywordStatusReason,
)


class AboveTargetMinBidDiagnosticState(StrEnum):
    """Состояние контура МС для отображения в карточке ключа."""

    INACTIVE = "inactive"
    PASS_BY_COST = "pass_by_cost"
    BLOCKED = "blocked"
    TEMPORARY_RECHECK = "temporary_recheck"
    NO_DATA = "no_data"


class AboveTargetMinBidDiagnostic(BaseModel):
    """Снимок inputs/gates и результата apply для правила МС."""

    state: AboveTargetMinBidDiagnosticState
    current_position: int | None = None
    target_place: int | None = None
    position_condition_pass: bool | None = None
    current_cpm: int | None = None
    min_bid: int | None = None
    min_bid_condition_pass: bool | None = None
    pay_for_order: float | None = None
    resolved_target_cost: float | None = None
    cost_gate_evaluated: bool = False
    cost_condition_pass: bool | None = None
    cooldown_display_tag: str | None = None
    cooldown_elapsed_hours: float | None = None
    reason_no_data: str | None = None
    resulting_status: KeywordStatus
    resulting_reason: KeywordStatusReason
