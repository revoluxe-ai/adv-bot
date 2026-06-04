"""Tick report: проекции ``NextState`` → ``V3Action``."""

from __future__ import annotations

from app.modules.common_slaves.wildberries.models.enums import KeywordStrategyMode
from app.modules.shop_runner.service_manager.services.auto_updater_v3.dto import (
    V3Action,
    V3ActionType,
)
from app.modules.shop_runner.service_manager.services.auto_updater_v3.effective_ladder_steps import (
    LadderStepKind,
    classify_ladder_step,
    ladder_step_snapshot_for_mode,
)
from app.modules.shop_runner.service_manager.services.auto_updater_v3.keyword_dto.dto import (
    KeywordDTO,
    NextState,
)


def next_state_steps_for_executor(
    dto: KeywordDTO,
    *,
    executor_name: str,
    steps_before: int,
) -> list[NextState]:
    """Новые ``NextState`` записи одного ключа, добавленные указанным executor."""
    return [
        step
        for step in dto.next_state[steps_before:]
        if step.executor_name == executor_name
    ]


def steps_to_v3_actions(
    dto: KeywordDTO,
    steps: list[NextState],
) -> list[V3Action]:
    """Сконвертировать шаги одного ключа в ``V3Action`` для tick report."""
    if not steps:
        return []
    ks_id = dto.keyword_setting_id
    actions: list[V3Action] = []
    prior = dto.stored_mode
    idx_before = len(dto.next_state) - len(steps)
    if idx_before > 0:
        prior = dto.next_state[idx_before - 1].new_mode.to_strategy_mode()
    for step in steps:
        action = _step_to_action(
            ks_id,
            dto=dto,
            prior_mode=prior,
            step=step,
        )
        if action is not None:
            actions.append(action)
        prior = step.new_mode.to_strategy_mode()
    return actions


def _step_to_action(
    keyword_setting_id: int,
    *,
    dto: KeywordDTO,
    prior_mode: KeywordStrategyMode,
    step: NextState,
) -> V3Action | None:
    new_mode = step.new_mode.to_strategy_mode()
    before = ladder_step_snapshot_for_mode(dto, prior_mode)
    after = ladder_step_snapshot_for_mode(dto, new_mode)
    kind = classify_ladder_step(before, after)
    if kind is None:
        return None
    reason = step.executor_name
    if kind == LadderStepKind.OFF:
        return V3Action(
            action=V3ActionType.FORCE_OFF,
            keyword_setting_id=keyword_setting_id,
            reason=reason,
        )
    if kind == LadderStepKind.DOWN:
        return V3Action(
            action=V3ActionType.DOWN,
            keyword_setting_id=keyword_setting_id,
            target_strategy_mode=new_mode,
            reason=reason,
        )
    return V3Action(
        action=V3ActionType.UP,
        keyword_setting_id=keyword_setting_id,
        target_strategy_mode=new_mode,
        reason=reason,
    )
