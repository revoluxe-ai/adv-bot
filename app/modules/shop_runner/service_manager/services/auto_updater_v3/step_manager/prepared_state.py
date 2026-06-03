"""Обновление ``KeywordDTO.current_mode`` in-place (step_manager / rollout)."""

from __future__ import annotations

from app.modules.common_slaves.wildberries.models.enums import KeywordStrategyMode
from app.modules.shop_runner.service_manager.services.auto_updater_v3.keywords_prepared import (
    KeywordsPreparedList,
    UpdateContext,
)
from app.modules.shop_runner.service_manager.services.auto_updater_v3.keywords_prepared.dto import (
    NextState,
)


def bump_prepared_mode(
    ctx: UpdateContext,
    keyword_setting_id: int,
    new_mode: KeywordStrategyMode,
    *,
    executor_name: str = "StepManager",
) -> UpdateContext:
    """In-place: append ``NextState`` для одного ключа."""
    for dto in ctx.keywords:
        if dto.keyword_setting_id == keyword_setting_id:
            dto.current_mode = NextState(new_mode=new_mode, executor_name=executor_name)
            break
    return ctx


def bump_prepared_list_only(
    prepared: KeywordsPreparedList,
    keyword_setting_id: int,
    new_mode: KeywordStrategyMode,
    *,
    executor_name: str = "rollout_planner",
) -> KeywordsPreparedList:
    """In-place: append ``NextState`` без ``UpdateContext``."""
    for dto in prepared.keywords:
        if dto.keyword_setting_id == keyword_setting_id:
            dto.current_mode = NextState(new_mode=new_mode, executor_name=executor_name)
            break
    return prepared
