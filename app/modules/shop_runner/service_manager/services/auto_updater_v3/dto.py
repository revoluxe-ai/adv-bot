"""Mode-level candidate metrics for AutoUpdater v3."""

from __future__ import annotations

from enum import Enum

from pydantic import BaseModel

from app.modules.common_slaves.wildberries.models.enums import KeywordStrategyMode


class AggressionTargetMode(str, Enum):
    MIN_CPA = "MIN_CPA"
    OPTIMUM = "OPTIMUM"
    MAX_CONVERSION = "MAX_CONVERSION"


class ModeCandidate(BaseModel):
    """Forecast slice for one aggression target mode."""

    mode: AggressionTargetMode
    bid: float | None = None
    position: int | None = None
    predicted_clicks: float | None = None
    predicted_orders: float | None = None
    predicted_spend: float | None = None
    predicted_cpa: float | None = None
    """CPO заказа на точке CH: к→к × корзина→заказ РК 7д, bid точки."""
    pay_for_cart: float | None = None
    """Руб/корзина на точке CH (``PositionProfilePoint.pay_for_cart``)."""
    predicted_conversion: float | None = None
    conversion_score: float | None = None
    economy_score: float | None = None
    volume_score: float | None = None
    confidence_score: float | None = None
    risk_score: float | None = None
    is_valid: bool = True
    invalid_reason: str | None = None


class V3ActionType(str, Enum):
    UP = "UP"
    DOWN = "DOWN"
    FORCE_OFF = "FORCE_OFF"
    REBALANCE_TRANSFER = "REBALANCE_TRANSFER"
    DO_NOTHING = "DO_NOTHING"


class V3SelectionLog(BaseModel):
    """Structured metadata for observability (orchestrator logs, не влияет на apply)."""

    pool_size: int | None = None
    pool_size_after_rec: int | None = None
    rec_tier: str | None = None
    state_cost: float | None = None
    pay_for_order: float | None = None
    from_mode: str | None = None
    to_mode: str | None = None
    move_kind: str | None = None
    imputed: bool | None = None
    mechanism: str | None = None
    skipped_mode_aliases: list[str] | None = None


class V3Action(BaseModel):
    """Single planned change for one cycle."""

    action: V3ActionType
    keyword_setting_id: int | None = None
    from_keyword_setting_id: int | None = None
    to_keyword_setting_id: int | None = None
    target_strategy_mode: KeywordStrategyMode | None = None
    reason: str = ""
    selection_log: V3SelectionLog | None = None

    model_config = {"extra": "forbid"}


def aggression_target_for_stored_mode(
    mode: KeywordStrategyMode,
) -> AggressionTargetMode | None:
    """Map stored ladder mode to candidate bucket (active modes only)."""
    if mode == KeywordStrategyMode.OFF:
        return None
    if mode == KeywordStrategyMode.MIN_CPA:
        return AggressionTargetMode.MIN_CPA
    if mode == KeywordStrategyMode.OPTIMUM:
        return AggressionTargetMode.OPTIMUM
    if mode == KeywordStrategyMode.MAX_CONVERSION:
        return AggressionTargetMode.MAX_CONVERSION
    return None
