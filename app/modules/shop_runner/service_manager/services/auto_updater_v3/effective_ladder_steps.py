"""Effective STEP_UP / STEP_DOWN: SSOT схлопывания alias по ``target_place``.

Контракт исполнения **любого** шага V3 (pooled UP, passing, calibration, realloc,
trim, shelf cleanup):
- одно действие = один вызов ``resolve_next_effective_step_up`` / ``resolve_next_effective_step_down``;
- режимы M/O/C с тем же ``target_place``, что у якоря шага, схлопываются (UP → max
  ``mode_level`` в группе, DOWN → пройти alias-цепочку до следующего place или OFF);
- это **не** увеличивает бюджет шагов (×2 calibration, released_steps realloc и т.д.).

``iter_effective_upper_modes`` / ``iter_effective_lower_modes`` / ``iter_effective_upper_mode_groups``
— перечисление смен ``target_place`` для анализа и «до упора» в **одном** UP
(``_highest_passing_mode_in_upper_groups``), не для N отдельных действий по alias.

OFF не сравнивается по ``target_place`` — отдельный уровень лестницы.

OFF → первый effective UP (важно для eligibility)
-------------------------------------------------
При ``current == OFF`` первый шаг не фиксирован как ``MIN_CPA``: после ``step_up(OFF)``
берётся ``target_place`` первой ступени и **схлопываются** все M/O/C на этом place
в max ``mode_level`` (например OFF→``MAX_CONVERSION``, если M=O=C на pos40).

Collectors с ослабленным gate (calibration UP ``off_no_data_bootstrap``) проверяют
``to_mode == MIN_CPA`` буквально. Если collapsed target — ``OPTIMUM``/``MAX_CONVERSION``,
а ``can_target_mode`` запрещает (MIN-only tier, пустой ``allowed_modes`` у NO DATA
без bootstrap-ветки), ключ **выпадает из пула без fallback** на ``MIN_CPA``.
Enable (``plan_pay_for_order_gap_enable``) всегда целится в ``MIN_CPA`` и не затронут.
См. ``collect_calibration_up_next_step_candidates`` и ``V3_UPDATER_VALIDATION.md``.
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
    mode_level,
    step_down,
    step_up,
)

_LADDER_MODES: tuple[KeywordStrategyMode, ...] = (
    KeywordStrategyMode.MIN_CPA,
    KeywordStrategyMode.OPTIMUM,
    KeywordStrategyMode.MAX_CONVERSION,
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


def logical_modes_at_target_place_above(
    above: KeywordStrategyMode,
    target_place: int,
    catalog: dict[AggressionTargetMode, ModeCandidate],
) -> tuple[KeywordStrategyMode, ...]:
    """Все валидные режимы выше ``above`` с заданным ``target_place`` (alias-группа)."""
    out: list[KeywordStrategyMode] = []
    for mode in _LADDER_MODES:
        if mode_level(mode) <= mode_level(above):
            continue
        mc = candidate_for_strategy_mode(mode, catalog)
        if mc is None or not mc.is_valid:
            continue
        place = target_place_from_mode_candidate(mc)
        if place == target_place:
            out.append(mode)
    return tuple(out)


def resolve_alias_collapse_up_at_same_target_place(
    current: KeywordStrategyMode,
    catalog: dict[AggressionTargetMode, ModeCandidate],
) -> KeywordStrategyMode | None:
    """Схлопнуть alias UP на текущем ``target_place`` до max ``mode_level`` в группе.

    Срабатывает только если ``step_up(current)`` ведёт на тот же ``target_place``,
    что и текущий режим. Не поднимает ключ на новый place (в отличие от
    ``resolve_next_effective_step_up``).
    """
    if current in (
        KeywordStrategyMode.OFF,
        KeywordStrategyMode.MAX_CONVERSION,
    ):
        return None
    cur_c = candidate_for_strategy_mode(current, catalog)
    if cur_c is None or not cur_c.is_valid:
        return None
    place = target_place_from_mode_candidate(cur_c)
    if place is None:
        return None
    nxt = step_up(current)
    if nxt is None:
        return None
    nxt_c = candidate_for_strategy_mode(nxt, catalog)
    if nxt_c is None or not nxt_c.is_valid:
        return None
    if not mode_candidates_same_effective_target(cur_c, nxt_c):
        return None
    group = logical_modes_at_target_place_above(current, place, catalog)
    if not group:
        return None
    target = max(group, key=mode_level)
    if mode_level(target) <= mode_level(current):
        return None
    return target


def resolve_next_effective_step_up(
    current: KeywordStrategyMode,
    catalog: dict[AggressionTargetMode, ModeCandidate],
) -> EffectiveStepResult:
    """Следующий effective UP: новый ``target_place`` и max ``mode_level`` в alias-группе.

    DOWN по-прежнему пропускает alias; UP внутри группы с одним place выбирает
    самый высокий логический режим (например MIN→MAX при O=C на pos1).

    Ветка ``current == OFF``: см. module docstring — collapse на первом place может
    вернуть режим выше ``MIN_CPA``; callers с MIN-only bootstrap должны учитывать
    рассинхрон с ``can_target_mode`` / ``off_no_data_bootstrap``.
    """
    if current == KeywordStrategyMode.OFF:
        nxt = step_up(KeywordStrategyMode.OFF)
        if nxt is None:
            return EffectiveStepResult(None, ())
        nxt_c = candidate_for_strategy_mode(nxt, catalog)
        if nxt_c is None or not nxt_c.is_valid:
            return EffectiveStepResult(nxt, ())
        place = target_place_from_mode_candidate(nxt_c)
        if place is None:
            return EffectiveStepResult(nxt, ())
        group = logical_modes_at_target_place_above(
            KeywordStrategyMode.OFF, place, catalog
        )
        if not group:
            return EffectiveStepResult(nxt, ())
        highest = max(group, key=mode_level)
        skipped_off: list[str] = []
        for mode in group:
            if mode != highest:
                skipped_off.append(
                    skipped_mode_alias_reason(
                        mode,
                        highest,
                        target_place=place,
                    )
                )
        return EffectiveStepResult(highest, tuple(skipped_off))
    skipped: list[str] = []
    cursor = current
    while True:
        nxt = step_up(cursor)
        if nxt is None:
            if mode_level(cursor) > mode_level(current):
                return EffectiveStepResult(cursor, tuple(skipped))
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
        target_place = target_place_from_mode_candidate(nxt_c)
        if target_place is None:
            return EffectiveStepResult(None, tuple(skipped))
        group = logical_modes_at_target_place_above(cursor, target_place, catalog)
        if not group:
            return EffectiveStepResult(None, tuple(skipped))
        highest = max(group, key=mode_level)
        for mode in group:
            if mode != highest:
                skipped.append(
                    skipped_mode_alias_reason(
                        mode,
                        highest,
                        target_place=target_place,
                    )
                )
        return EffectiveStepResult(highest, tuple(skipped))


def resolve_next_effective_step_down(
    current: KeywordStrategyMode,
    catalog: dict[AggressionTargetMode, ModeCandidate],
) -> EffectiveStepResult:
    """Один effective DOWN: alias ниже ``current`` с тем же place пропускаются (до OFF)."""
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


def iter_effective_upper_mode_groups(
    current: KeywordStrategyMode,
    catalog: dict[AggressionTargetMode, ModeCandidate],
) -> tuple[tuple[KeywordStrategyMode, ...], ...]:
    """Группы режимов по новому ``target_place`` (alias внутри группы) для UP-планировщиков."""
    groups: list[tuple[KeywordStrategyMode, ...]] = []
    cursor = current
    while True:
        res = resolve_next_effective_step_up(cursor, catalog)
        for msg in res.skipped_aliases:
            logger.debug("%s", msg)
        if res.next_mode is None:
            return tuple(groups)
        nxt_c = candidate_for_strategy_mode(res.next_mode, catalog)
        place = target_place_from_mode_candidate(nxt_c)
        if place is None:
            if cursor == KeywordStrategyMode.OFF and res.next_mode is not None:
                groups.append((res.next_mode,))
                cursor = res.next_mode
                continue
            return tuple(groups)
        group = logical_modes_at_target_place_above(cursor, place, catalog)
        if group:
            groups.append(group)
        elif cursor == KeywordStrategyMode.OFF and res.next_mode is not None:
            groups.append((res.next_mode,))
        cursor = res.next_mode


def iter_effective_upper_modes(
    current: KeywordStrategyMode,
    catalog: dict[AggressionTargetMode, ModeCandidate],
) -> list[KeywordStrategyMode]:
    """Цепочка collapsed UP-целей (по place); не для N действий за тик — см. module docstring."""
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


def iter_effective_lower_modes(
    current: KeywordStrategyMode,
    catalog: dict[AggressionTargetMode, ModeCandidate],
) -> list[KeywordStrategyMode]:
    """Цепочка collapsed DOWN-целей; не для N действий за тик — см. module docstring."""
    out: list[KeywordStrategyMode] = []
    if current == KeywordStrategyMode.OFF:
        return out
    cursor = current
    while True:
        res = resolve_next_effective_step_down(cursor, catalog)
        for msg in res.skipped_aliases:
            logger.debug("%s", msg)
        if res.next_mode is None:
            return out
        out.append(res.next_mode)
        if res.next_mode == KeywordStrategyMode.OFF:
            return out
        cursor = res.next_mode
    return out


def count_effective_released_aggression_steps(
    from_mode: KeywordStrategyMode,
    to_mode: KeywordStrategyMode | None,
    catalog: dict[AggressionTargetMode, ModeCandidate],
) -> int:
    """Сколько «снято агрессии» одним DOWN: 1 только если place изменился или OFF."""
    return count_effective_aggression_steps_between(from_mode, to_mode, catalog)


def count_effective_aggression_steps_between(
    from_mode: KeywordStrategyMode,
    to_mode: KeywordStrategyMode | None,
    catalog: dict[AggressionTargetMode, ModeCandidate],
) -> int:
    """1 если ``target_place`` изменился между режимами (или OFF); 0 для alias-only."""
    if to_mode is None or to_mode == from_mode:
        return 0
    if to_mode == KeywordStrategyMode.OFF or from_mode == KeywordStrategyMode.OFF:
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
