"""Выбор ladder-state для preamble executors (без логики в KeywordDTO)."""

from __future__ import annotations

from app.modules.common_slaves.wildberries.models.enums import KeywordStrategyMode
from app.modules.shop_runner.service_manager.services.auto_updater_v3.keyword_dto.dto import (
    KeywordDTO,
)
from app.modules.shop_runner.service_manager.services.auto_updater_v3.keyword_dto.dto.keyword_v3_ladder_state import (
    KeywordV3LadderState,
)
from app.modules.shop_runner.service_manager.services.auto_updater_v3.keyword_dto.dto.ladder_state_kind import (
    V3LadderStageKind,
)
from app.modules.shop_runner.service_manager.services.auto_updater_v3.ladder import (
    mode_level,
)

_OPERABLE_LADDER_STAGES = (
    V3LadderStageKind.MIN_CPA,
    V3LadderStageKind.OPTIMUM,
    V3LadderStageKind.MAX_CONVERSION,
)


def is_gap_ladder(dto: KeywordDTO) -> bool:
    """``True``, если в матрице есть ступень GAP (NO DATA без CH)."""
    return any(state.stage == V3LadderStageKind.GAP for state in dto.ladder_states)


def has_operable_cpo(dto: KeywordDTO) -> bool:
    """Есть ли MIN/OPT/MAX с известным CPO."""
    return any(
        state.cpo is not None and state.stage in _OPERABLE_LADDER_STAGES
        for state in dto.ladder_states
    )


def ladder_state_for_mode(
    dto: KeywordDTO,
    mode: KeywordStrategyMode,
) -> KeywordV3LadderState | None:
    """Ladder-state по ``strategy_mode`` (первая подходящая запись)."""
    for state in dto.ladder_states:
        if state.strategy_mode == mode:
            return state
    return None


def pick_off_ladder_state(dto: KeywordDTO) -> KeywordV3LadderState | None:
    """OFF-ступень (stage OFF), не GAP."""
    for state in dto.ladder_states:
        if state.stage == V3LadderStageKind.OFF:
            return state
    for state in dto.ladder_states:
        if state.strategy_mode == KeywordStrategyMode.OFF:
            return state
    return None


def is_gap_without_operable_cpo(dto: KeywordDTO) -> bool:
    """GAP ladder и нет CPO у текущей ступени / operable-ступеней."""
    if not is_gap_ladder(dto):
        return False
    if not has_operable_cpo(dto):
        return True
    current = ladder_state_for_mode(dto, dto.current_mode)
    return current is None or current.cpo is None


def pick_max_ladder_state_at_or_below_cpo(
    dto: KeywordDTO,
    ceiling: float,
) -> KeywordV3LadderState | None:
    """Максимальная по агрессии ступень MIN/OPT/MAX с ``cpo <= ceiling``."""
    threshold = float(ceiling)
    candidates = [
        state
        for state in dto.ladder_states
        if state.cpo is not None
        and state.stage in _OPERABLE_LADDER_STAGES
        and float(state.cpo) <= threshold
    ]
    if not candidates:
        return None
    return max(candidates, key=lambda state: mode_level(state.strategy_mode))
