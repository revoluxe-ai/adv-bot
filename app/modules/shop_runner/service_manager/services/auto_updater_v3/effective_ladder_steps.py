"""Effective STEP_UP / STEP_DOWN: пропуск логических режимов с тем же target_place.

Логические режимы MIN_CPA / OPTIMUM / MAX_CONVERSION сохраняются в модели;
переход создаётся только если ``target_place`` (позиция CH-кандидата) реально меняется.

OFF не сравнивается по target_place — это выключение ключа.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass

from app.modules.common_slaves.wildberries.models.enums import KeywordStrategyMode
from app.modules.shop_runner.service_manager.services.auto_updater_v3.dto import (
    AggressionTargetMode,
    ModeCandidate,
    aggression_target_for_stored_mode,
)
from app.modules.shop_runner.service_manager.services.auto_updater_v3.ladder import (
    step_down,
    step_up,
)

logger = logging.getLogger(__name__)


def candidate_for_strategy_mode(
    mode: KeywordStrategyMode,
    catalog: dict[AggressionTargetMode, ModeCandidate],
) -> ModeCandidate | None:
    """``ModeCandidate`` для stored ``KeywordStrategyMode`` (OFF → ``None``)."""
    agg = aggression_target_for_stored_mode(mode)
    if agg is None:
        return None
    return catalog.get(agg)


def target_place_from_mode_candidate(mc: ModeCandidate | None) -> int | None:
    """``target_place`` режима из ``ModeCandidate.position`` (как в ``target_place_sync``)."""
    if mc is None or not mc.is_valid or mc.position is None:
        return None
    return max(1, int(mc.position))


def mode_candidates_same_effective_target(
    left: ModeCandidate | None,
    right: ModeCandidate | None,
) -> bool:
    """Два режима ведут в один ``target_place`` (bid/CPO/conv не сравниваем)."""
    left_place = target_place_from_mode_candidate(left)
    right_place = target_place_from_mode_candidate(right)
    if left_place is None or right_place is None:
        return False
    return left_place == right_place


def skipped_mode_alias_reason(
    skipped: KeywordStrategyMode,
    anchor: KeywordStrategyMode,
    *,
    target_place: int | None = None,
) -> str:
    """Текст для логов/debug при пропуске alias-режима."""
    base = (
        f"skipped_mode_alias: {skipped.name} effective target_place "
        f"equals {anchor.name}"
    )
    if target_place is not None:
        return f"{base} (place={target_place})"
    return base


@dataclass(frozen=True, slots=True)
class EffectiveStepResult:
    """Следующий логический режим с отличием target_place или ``None``."""

    next_mode: KeywordStrategyMode | None
    skipped_aliases: tuple[str, ...]


def resolve_next_effective_step_up(
    current: KeywordStrategyMode,
    catalog: dict[AggressionTargetMode, ModeCandidate],
) -> EffectiveStepResult:
    """Первый режим выше ``current`` с другим ``target_place``."""
    if current == KeywordStrategyMode.OFF:
        nxt = step_up(KeywordStrategyMode.OFF)
        return EffectiveStepResult(nxt, ())
    skipped: list[str] = []
    cursor = current
    while True:
        nxt = step_up(cursor)
        if nxt is None:
            return EffectiveStepResult(None, tuple(skipped))
        nxt_c = candidate_for_strategy_mode(nxt, catalog)
        if nxt_c is None or not nxt_c.is_valid:
            return EffectiveStepResult(None, tuple(skipped))
        cursor_c = candidate_for_strategy_mode(cursor, catalog)
        if mode_candidates_same_effective_target(cursor_c, nxt_c):
            skipped.append(
                skipped_mode_alias_reason(
                    nxt,
                    cursor,
                    target_place=target_place_from_mode_candidate(cursor_c),
                )
            )
            cursor = nxt
            continue
        return EffectiveStepResult(nxt, tuple(skipped))


def resolve_next_effective_step_down(
    current: KeywordStrategyMode,
    catalog: dict[AggressionTargetMode, ModeCandidate],
) -> EffectiveStepResult:
    """Первый режим ниже ``current`` с другим ``target_place``."""
    if current == KeywordStrategyMode.OFF:
        return EffectiveStepResult(None, ())
    skipped: list[str] = []
    cursor = current
    while True:
        nxt = step_down(cursor)
        if nxt is None:
            return EffectiveStepResult(None, tuple(skipped))
        if nxt == KeywordStrategyMode.OFF:
            return EffectiveStepResult(nxt, tuple(skipped))
        nxt_c = candidate_for_strategy_mode(nxt, catalog)
        if nxt_c is None or not nxt_c.is_valid:
            return EffectiveStepResult(nxt, tuple(skipped))
        cursor_c = candidate_for_strategy_mode(cursor, catalog)
        if mode_candidates_same_effective_target(cursor_c, nxt_c):
            skipped.append(
                skipped_mode_alias_reason(
                    nxt,
                    cursor,
                    target_place=target_place_from_mode_candidate(cursor_c),
                )
            )
            cursor = nxt
            continue
        return EffectiveStepResult(nxt, tuple(skipped))


def iter_effective_upper_modes(
    current: KeywordStrategyMode,
    catalog: dict[AggressionTargetMode, ModeCandidate],
) -> list[KeywordStrategyMode]:
    """Все режимы выше ``current`` с попарно различным ``target_place``."""
    out: list[KeywordStrategyMode] = []
    cursor = current
    while True:
        res = resolve_next_effective_step_up(cursor, catalog)
        for msg in res.skipped_aliases:
            logger.debug("%s", msg)
        if res.next_mode is None:
            return out
        out.append(res.next_mode)
        cursor = res.next_mode
    return out


def count_effective_released_aggression_steps(
    from_mode: KeywordStrategyMode,
    to_mode: KeywordStrategyMode | None,
    catalog: dict[AggressionTargetMode, ModeCandidate],
) -> int:
    """Сколько «снято агрессии» одним DOWN: 1 только если place изменился или OFF.

    Логический MAX→OPT при том же ``target_place`` = 0 (alias, не шаг ребаланса).
    """
    if to_mode is None or to_mode == from_mode:
        return 0
    if to_mode == KeywordStrategyMode.OFF:
        return 1
    from_c = candidate_for_strategy_mode(from_mode, catalog)
    to_c = candidate_for_strategy_mode(to_mode, catalog)
    if mode_candidates_same_effective_target(from_c, to_c):
        return 0
    return 1


def log_skipped_aliases(keyword: str, skipped: tuple[str, ...]) -> None:
    """Debug-лог пропущенных alias-режимов для ключа."""
    for msg in skipped:
        logger.debug("v3 kw=%s %s", keyword, msg)
