"""Выбор ladder-state для preamble executors (без логики в KeywordDTO)."""

from __future__ import annotations

from app.modules.common_slaves.wildberries.models.enums import KeywordStrategyMode
from app.modules.shop_runner.service_manager.services.auto_updater_v3.dto import (
    AggressionTargetMode,
    ModeCandidate,
    aggression_target_for_stored_mode,
)
from app.modules.shop_runner.service_manager.services.auto_updater_v3.effective_ladder_steps import (
    candidate_for_strategy_mode,
    resolve_next_effective_step_down,
    target_place_from_mode_candidate,
)
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

OPERABLE_LADDER_STAGES = (
    V3LadderStageKind.MIN_CPA,
    V3LadderStageKind.OPTIMUM,
    V3LadderStageKind.MAX_CONVERSION,
)
_OPERABLE_LADDER_STAGES = OPERABLE_LADDER_STAGES


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


def ladder_aggression_rank(state: KeywordV3LadderState) -> tuple[int, int]:
    """Ранг ступени: ``(mode_level, -target_position)``; OFF → ``(-1, -1)``."""
    if state.strategy_mode == KeywordStrategyMode.OFF:
        return (-1, -1)
    return (mode_level(state.strategy_mode), -int(state.target_position))


def current_aggression_rank(dto: KeywordDTO) -> tuple[int, int]:
    """Ранг текущего effective-состояния ключа (через ``resolve_current_ladder_state``)."""
    if dto.current_mode == KeywordStrategyMode.OFF:
        return (-1, -1)
    state = resolve_current_ladder_state(dto)
    if state is not None:
        return ladder_aggression_rank(state)
    return (mode_level(dto.current_mode), 0)


def resolve_current_ladder_state(dto: KeywordDTO) -> KeywordV3LadderState | None:
    """Ladder-state, соответствующий ``current_mode`` + ``current_target_place``."""
    if dto.current_mode == KeywordStrategyMode.OFF:
        return pick_off_ladder_state(dto)
    place = int(dto.current_target_place)
    for state in dto.ladder_states:
        if (
            state.strategy_mode == dto.current_mode
            and int(state.target_position) == place
        ):
            return state
    return ladder_state_for_mode(dto, dto.current_mode)


def mode_catalog_from_dto(
    dto: KeywordDTO,
) -> dict[AggressionTargetMode, ModeCandidate]:
    """Lightweight M/O/C catalog из ``dto.ladder_states`` для effective UP/DOWN.

    При нескольких ступенях одного режима берётся минимальный ``target_position``
    (корректный effective DOWN через alias на одном place).
    """
    picks: dict[AggressionTargetMode, KeywordV3LadderState] = {}
    for state in dto.ladder_states:
        agg = aggression_target_for_stored_mode(state.strategy_mode)
        if agg is None:
            continue
        existing = picks.get(agg)
        if existing is None or int(state.target_position) < int(existing.target_position):
            picks[agg] = state
    catalog: dict[AggressionTargetMode, ModeCandidate] = {}
    for agg, state in picks.items():
        catalog[agg] = ModeCandidate(
            mode=agg,
            position=state.target_position,
            predicted_cpa=state.cpo,
            is_valid=state.is_valid,
        )
    return catalog


def ladder_state_for_mode_and_place(
    dto: KeywordDTO,
    mode: KeywordStrategyMode,
    target_place: int | None,
) -> KeywordV3LadderState | None:
    """Стейт по режиму и ``target_place``; ``None`` place — OFF."""
    if mode == KeywordStrategyMode.OFF:
        return pick_off_ladder_state(dto)
    if target_place is None:
        return ladder_state_for_mode(dto, mode)
    for state in dto.ladder_states:
        if (
            state.strategy_mode == mode
            and int(state.target_position) == int(target_place)
        ):
            return state
    return ladder_state_for_mode(dto, mode)


def pick_effective_down_ladder_state(dto: KeywordDTO) -> KeywordV3LadderState | None:
    """Один effective DOWN: следующий ladder-state с другим ``target_place`` или OFF."""
    if dto.current_mode == KeywordStrategyMode.OFF:
        return None
    catalog = mode_catalog_from_dto(dto)
    step = resolve_next_effective_step_down(dto.current_mode, catalog)
    next_mode = step.next_mode
    if next_mode is None:
        return None
    if next_mode == KeywordStrategyMode.OFF:
        return pick_off_ladder_state(dto)
    next_candidate = candidate_for_strategy_mode(next_mode, catalog)
    place = target_place_from_mode_candidate(next_candidate)
    return ladder_state_for_mode_and_place(dto, next_mode, place)
