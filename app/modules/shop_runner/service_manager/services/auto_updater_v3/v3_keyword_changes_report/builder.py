"""Post-hoc сборка audit из ``KeywordDTO.next_state``."""

from __future__ import annotations

from collections import defaultdict
from datetime import datetime, timezone

from app.modules.common_slaves.wildberries.models.enums import KeywordStrategyMode
from app.modules.shop_runner.service_manager.services.auto_updater_v3.dto import (
    V3ActionType,
)
from app.modules.shop_runner.service_manager.services.auto_updater_v3.keyword_dto.dto import (
    KeywordDTO,
)
from app.modules.shop_runner.service_manager.services.auto_updater_v3.ladder import (
    mode_level,
)
from app.modules.shop_runner.service_manager.services.auto_updater_v3.update_pipeline.next_state.phase_report import (
    step_to_action,
)
from app.modules.shop_runner.service_manager.services.auto_updater_v3.v3_keyword_changes_report.executor_phase_map import (
    IGNORED_EXECUTOR_NAMES,
    phase_id_for_executor,
    short_label_for_executor,
    title_ru_for_phase,
)
from app.modules.shop_runner.service_manager.services.auto_updater_v3.v3_keyword_changes_report.models import (
    V3ExecutorPhaseBreakdown,
    V3KeywordChangeEntry,
    V3KeywordChangesSnapshot,
    V3KeywordStepRecord,
)
from app.modules.shop_runner.service_manager.services.auto_updater_v3.v3_tick_report import (
    mode_aggression_points,
)


def _mode_label(mode: KeywordStrategyMode) -> str:
    return mode.name


def _classify_netto(
    baseline: KeywordStrategyMode,
    desired: KeywordStrategyMode,
) -> V3ActionType | None:
    if baseline == desired:
        return None
    if desired == KeywordStrategyMode.OFF:
        return V3ActionType.FORCE_OFF
    if mode_level(desired) < mode_level(baseline):
        return V3ActionType.DOWN
    if mode_level(desired) > mode_level(baseline):
        return V3ActionType.UP
    return None


def _net_breakdown(keywords: list[KeywordDTO]) -> tuple[int, int, int, int]:
    up = down = force_off = net_on = 0
    for dto in keywords:
        action = _classify_netto(dto.stored_mode, dto.current_mode)
        if action == V3ActionType.UP:
            up += 1
        elif action == V3ActionType.DOWN:
            down += 1
        elif action == V3ActionType.FORCE_OFF:
            force_off += 1
        if (
            dto.stored_mode == KeywordStrategyMode.OFF
            and dto.current_mode != KeywordStrategyMode.OFF
        ):
            net_on += 1
    return up, down, force_off, net_on


def _executor_outcome_counts(
    keyword_modes: dict[int, tuple[KeywordStrategyMode, KeywordStrategyMode]],
) -> tuple[int, int]:
    """Исходы по ключам одного executor: off (ended OFF) и on (OFF→active)."""
    ended_off = ended_on = 0
    for start, end in keyword_modes.values():
        if end == KeywordStrategyMode.OFF:
            ended_off += 1
        if start == KeywordStrategyMode.OFF and end != KeywordStrategyMode.OFF:
            ended_on += 1
    return ended_off, ended_on


def _track_executor_keyword_mode(
    keyword_modes: dict[int, tuple[KeywordStrategyMode, KeywordStrategyMode]],
    *,
    ks_id: int,
    mode_before_step: KeywordStrategyMode,
    mode_after_step: KeywordStrategyMode,
) -> None:
    if ks_id not in keyword_modes:
        keyword_modes[ks_id] = (mode_before_step, mode_before_step)
    start, _ = keyword_modes[ks_id]
    keyword_modes[ks_id] = (start, mode_after_step)


def _aggression_score_from_dtos(keywords: list[KeywordDTO]) -> int:
    return sum(mode_aggression_points(dto.current_mode) for dto in keywords)


def _increment_breakdown(
    buckets: dict[str, dict[str, int]],
    *,
    executor_name: str,
    action: V3ActionType,
    keyword_touched: set[int],
    ks_id: int,
) -> None:
    bucket = buckets[executor_name]
    keyword_touched.add(ks_id)
    if action == V3ActionType.UP:
        bucket["up"] += 1
        bucket["planned"] += 1
    elif action == V3ActionType.DOWN:
        bucket["down"] += 1
        bucket["planned"] += 1
    elif action == V3ActionType.FORCE_OFF:
        bucket["force_off"] += 1
        bucket["planned"] += 1
    elif action == V3ActionType.REBALANCE_TRANSFER:
        bucket["rebalance"] += 1
        bucket["planned"] += 1


def _build_keyword_entry(dto: KeywordDTO) -> V3KeywordChangeEntry | None:
    has_mode = bool(dto.next_state)
    has_place = bool(dto.history_target_place)
    if not has_mode and not has_place:
        return None

    ks_id = dto.keyword_setting_id
    if ks_id <= 0:
        return None

    steps: list[V3KeywordStepRecord] = []
    labels: list[str] = []
    prior = dto.stored_mode
    for step in dto.next_state:
        if step.executor_name in IGNORED_EXECUTOR_NAMES:
            prior = step.new_mode.to_strategy_mode()
            continue
        new_mode = step.new_mode.to_strategy_mode()
        action = step_to_action(ks_id, dto=dto, prior_mode=prior, step=step)
        action_label = "NOOP"
        if action is not None:
            action_label = action.action.name
        steps.append(
            V3KeywordStepRecord(
                executor_name=step.executor_name,
                from_mode=_mode_label(prior),
                to_mode=_mode_label(new_mode),
                action=action_label,
            )
        )
        if action is not None:
            labels.append(short_label_for_executor(step.executor_name))
        prior = new_mode

    chain_modes = [_mode_label(dto.stored_mode)]
    for step in dto.next_state:
        if step.executor_name in IGNORED_EXECUTOR_NAMES:
            continue
        chain_modes.append(_mode_label(step.new_mode.to_strategy_mode()))
    # dedupe consecutive identical
    compact_chain: list[str] = []
    for mode in chain_modes:
        if not compact_chain or compact_chain[-1] != mode:
            compact_chain.append(mode)

    place_steps = [
        f"{item.new_target_place} ({short_label_for_executor(item.executor_name)})"
        for item in dto.history_target_place
        if item.executor_name not in IGNORED_EXECUTOR_NAMES
    ]

    return V3KeywordChangeEntry(
        keyword_setting_id=ks_id,
        keyword_text=dto.calculated_keyword.text,
        stored_mode=_mode_label(dto.stored_mode),
        current_mode=_mode_label(dto.current_mode),
        mode_chain="→".join(compact_chain),
        executor_short_labels="·".join(labels),
        steps=steps,
        target_place_steps=place_steps,
    )


def build_keyword_changes_snapshot(
    keywords: list[KeywordDTO],
    *,
    adv_id: int,
    tick_at: datetime | None = None,
) -> V3KeywordChangesSnapshot:
    """Собрать audit из ``KeywordDTO`` после preamble pipeline.

    Args:
        keywords: Канонический список ключей ``UpdateContext.keywords``.
        adv_id: ID рекламной кампании WB.
        tick_at: Время тика (UTC); по умолчанию ``now(UTC)``.

    Returns:
        Snapshot с breakdown по executor и per-keyword entries.
    """
    ts = tick_at or datetime.now(timezone.utc)
    if ts.tzinfo is None:
        ts = ts.replace(tzinfo=timezone.utc)

    buckets: dict[str, dict[str, int]] = defaultdict(
        lambda: {
            "planned": 0,
            "up": 0,
            "down": 0,
            "force_off": 0,
            "rebalance": 0,
        }
    )
    keywords_by_executor: dict[str, set[int]] = defaultdict(set)
    executor_keyword_modes: dict[str, dict[int, tuple[KeywordStrategyMode, KeywordStrategyMode]]] = (
        defaultdict(dict)
    )
    entries: list[V3KeywordChangeEntry] = []

    for dto in keywords:
        entry = _build_keyword_entry(dto)
        if entry is not None:
            entries.append(entry)

        ks_id = dto.keyword_setting_id
        if ks_id <= 0:
            continue
        prior = dto.stored_mode
        for step in dto.next_state:
            if step.executor_name in IGNORED_EXECUTOR_NAMES:
                prior = step.new_mode.to_strategy_mode()
                continue
            mode_before = prior
            new_mode = step.new_mode.to_strategy_mode()
            action = step_to_action(ks_id, dto=dto, prior_mode=prior, step=step)
            if action is not None:
                _increment_breakdown(
                    buckets,
                    executor_name=step.executor_name,
                    action=action.action,
                    keyword_touched=keywords_by_executor[step.executor_name],
                    ks_id=ks_id,
                )
            _track_executor_keyword_mode(
                executor_keyword_modes[step.executor_name],
                ks_id=ks_id,
                mode_before_step=mode_before,
                mode_after_step=new_mode,
            )
            prior = new_mode

    by_phase: list[V3ExecutorPhaseBreakdown] = []
    for executor_name, counts in sorted(buckets.items()):
        phase_id = phase_id_for_executor(executor_name)
        ended_off, ended_on = _executor_outcome_counts(
            executor_keyword_modes[executor_name]
        )
        by_phase.append(
            V3ExecutorPhaseBreakdown(
                phase_id=phase_id,
                executor_name=executor_name,
                title_ru=title_ru_for_phase(phase_id),
                planned=counts["planned"],
                up=counts["up"],
                down=counts["down"],
                force_off=counts["force_off"],
                rebalance=counts["rebalance"],
                keywords_touched=len(keywords_by_executor[executor_name]),
                ended_off=ended_off,
                ended_on=ended_on,
            )
        )

    net_up, net_down, net_force_off, net_on = _net_breakdown(keywords)
    return V3KeywordChangesSnapshot(
        tick_at=ts,
        adv_id=adv_id,
        source="keyword_dto",
        changed_keywords=len(entries),
        net_up=net_up,
        net_down=net_down,
        net_force_off=net_force_off,
        net_on=net_on,
        aggression_score_after=_aggression_score_from_dtos(keywords),
        by_phase=by_phase,
        keyword_entries=sorted(entries, key=lambda e: e.keyword_text.lower()),
    )
