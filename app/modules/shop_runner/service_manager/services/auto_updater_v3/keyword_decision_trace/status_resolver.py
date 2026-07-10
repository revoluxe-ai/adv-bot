"""Метки state/status_hint для KeywordDecisionTrace (read-only, без business logic)."""

from __future__ import annotations

from app.modules.common_slaves.wildberries.models.enums import KeywordStrategyMode
from app.modules.shop_runner.service_manager.services.auto_updater_v3.keyword_dto.dto import (
    KeywordDTO,
)
from app.modules.shop_runner.service_manager.services.auto_updater_v3.keyword_v3_tier import (
    KeywordV3DataTier,
)
from app.modules.wb_adv_updater.calculated_keywords_manager.dto.states import (
    KeywordStatus,
)

_STATE_UNKNOWN = "unknown"
_STATUS_HINT_UNKNOWN = "unknown"
_STATUS_HINT_OFF_LIKE = "off-like"


def resolve_state_label(dto: KeywordDTO) -> str:
    """Буква режима / GAP / OFF для UI trace.

    Args:
        dto: Состояние ключа после фазы (read-only).

    Returns:
        ``OFF`` | ``GAP`` | ``M`` | ``O`` | ``C`` | ``unknown``.
    """
    mode = dto.current_mode
    tier = dto.data_tier
    if mode == KeywordStrategyMode.OFF and tier == KeywordV3DataTier.GAP:
        return "GAP"
    if mode == KeywordStrategyMode.OFF:
        return "OFF"
    if mode == KeywordStrategyMode.MIN_CPA:
        return "M"
    if mode == KeywordStrategyMode.OPTIMUM:
        return "O"
    if mode == KeywordStrategyMode.MAX_CONVERSION:
        return "C"
    return _STATE_UNKNOWN


def resolve_status_hint(dto: KeywordDTO) -> str:
    """Hint статуса ключа во время preamble (не финальный DB/UI status).

    Зеркалит карточку Telegram: hard_status 0/3/4 → фиксированные метки;
    operable 1|2 → ``calculated_keyword.status``. При ``OFF`` режиме — ``off-like``.

    Args:
        dto: Состояние ключа после фазы (read-only).

    Returns:
        ``good`` | ``bad`` | ``pause`` | ``off-like`` | ``unknown``.
    """
    hard = int(dto.hard_status)
    if hard == 4:
        return "good"
    if hard in (0, 3):
        return "bad"
    if dto.current_mode == KeywordStrategyMode.OFF:
        return _STATUS_HINT_OFF_LIKE

    status = dto.calculated_keyword.status
    if status == KeywordStatus.GOOD:
        return "good"
    if status == KeywordStatus.BAD:
        return "bad"
    if status == KeywordStatus.VIEWS_IS_NOT_ENOUGH:
        return "pause"
    return _STATUS_HINT_UNKNOWN
