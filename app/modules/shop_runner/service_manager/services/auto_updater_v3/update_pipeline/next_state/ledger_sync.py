"""Синхронизация netto ``KeywordDTO.current_mode`` → ``V3TickKeywordLedger`` перед flush."""

from __future__ import annotations

from app.modules.common_slaves.wildberries.models.enums import KeywordStrategyMode
from app.modules.shop_runner.service_manager.services.auto_updater_v3.dto import (
    V3Action,
    V3ActionType,
)
from app.modules.shop_runner.service_manager.services.auto_updater_v3.keywords_prepared.dto import (
    UpdateContext,
)
from app.modules.shop_runner.service_manager.services.auto_updater_v3.ladder import (
    mode_level,
)
from app.modules.shop_runner.service_manager.services.auto_updater_v3.tick_ledger import (
    V3TickKeywordLedger,
)


def sync_update_context_to_ledger(
    update_context: UpdateContext | None,
    ledger: V3TickKeywordLedger,
) -> list[V3Action]:
    """Применить netto-режимы из ``UpdateContext`` к ledger in-memory."""
    if update_context is None:
        return []
    actions: list[V3Action] = []
    for dto in update_context.keywords:
        ks_id = dto.keyword_setting_id
        if ks_id <= 0:
            continue
        baseline = ledger.baseline_mode_for(ks_id)
        if baseline is None:
            baseline = dto.stored_mode
        desired = dto.current_mode
        action = _netto_action(ks_id, baseline=baseline, desired=desired)
        if action is not None:
            actions.append(action)
    if actions:
        ledger.apply_in_memory(actions)
    return actions


def _netto_action(
    keyword_setting_id: int,
    *,
    baseline: KeywordStrategyMode,
    desired: KeywordStrategyMode,
) -> V3Action | None:
    if baseline == desired:
        return None
    if desired == KeywordStrategyMode.OFF:
        return V3Action(
            action=V3ActionType.FORCE_OFF,
            keyword_setting_id=keyword_setting_id,
            reason="next_state_netto",
        )
    if mode_level(desired) < mode_level(baseline):
        return V3Action(
            action=V3ActionType.DOWN,
            keyword_setting_id=keyword_setting_id,
            target_strategy_mode=desired,
            reason="next_state_netto",
        )
    return V3Action(
        action=V3ActionType.UP,
        keyword_setting_id=keyword_setting_id,
        target_strategy_mode=desired,
        reason="next_state_netto",
    )
