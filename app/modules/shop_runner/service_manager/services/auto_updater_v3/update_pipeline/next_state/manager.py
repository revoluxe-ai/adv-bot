"""In-place переходы ``KeywordDTO.current_mode`` для preamble executors."""

from __future__ import annotations

from app.modules.common_slaves.wildberries.models.enums import KeywordStrategyMode
from app.modules.shop_runner.service_manager.services.auto_updater_v3.applier import (
    V3_ACTION_APPLY_ORDER,
    resolve_v3_action_target_mode,
)
from app.modules.shop_runner.service_manager.services.auto_updater_v3.dto import (
    V3Action,
    V3ActionType,
)
from app.modules.shop_runner.service_manager.services.auto_updater_v3.keywords_prepared.dto import (
    KeywordDTO,
    NextState,
    UpdateContext,
)
from app.modules.shop_runner.service_manager.services.auto_updater_v3.keywords_prepared.dto.keyword_mode import (
    KeywordMode,
)
from app.modules.shop_runner.service_manager.services.auto_updater_v3.keywords_prepared.dto.keyword_v3_ladder_state import (
    KeywordV3LadderState,
)
from app.modules.shop_runner.service_manager.services.auto_updater_v3.v3_operable_keywords import (
    HARD_STATUS_AUTO_MODE,
)


class NextStateManager:
    """Операции in-place над ``KeywordDTO``; ``executor_name`` пишется в каждый ``NextState``."""

    def __init__(self, executor_class: type) -> None:
        self._executor_name = executor_class.__name__

    @property
    def executor_name(self) -> str:
        return self._executor_name

    def validate_state_by_hard_status(self, keyword: KeywordDTO) -> None:
        """``hard_status=1`` → ``OFF``."""
        if keyword.hard_status != HARD_STATUS_AUTO_MODE:
            return
        keyword.current_mode = NextState(
            new_mode=KeywordMode.OFF,
            executor_name=self._executor_name,
        )

    def validate_not_full_state(self, keyword: KeywordDTO) -> None:
        """Validate NOT FULL active keys → ``NOT_FULL_ACTIVATE`` (DTO → MIN + tp=0)."""
        keyword.current_mode = NextState(
            new_mode=KeywordMode.NOT_FULL_ACTIVATE,
            executor_name=self._executor_name,
        )

    def raise_state_to_target_cpo(
        self,
        keyword: KeywordDTO,
        state: KeywordV3LadderState | None,
    ) -> None:
        """Применить ladder-state; ``None`` — no-op."""
        if state is None:
            return
        keyword.apply_ladder_state(state, executor_name=self._executor_name)

    def apply_v3_actions(self, context: UpdateContext, actions: list[V3Action]) -> None:
        """Применить planned ``V3Action`` к ключам контекста через ``NextState``."""
        if not actions:
            return
        ordered = sorted(
            actions,
            key=lambda action: V3_ACTION_APPLY_ORDER.get(action.action, 99),
        )
        for action in ordered:
            self._apply_one(context, action)

    def _apply_one(self, context: UpdateContext, action: V3Action) -> None:
        if action.action == V3ActionType.DO_NOTHING:
            return
        if action.action == V3ActionType.REBALANCE_TRANSFER:
            if action.from_keyword_setting_id is not None:
                self._set_mode(
                    context,
                    int(action.from_keyword_setting_id),
                    KeywordStrategyMode.OFF,
                )
            if (
                action.to_keyword_setting_id is not None
                and action.target_strategy_mode is not None
            ):
                self._set_mode(
                    context,
                    int(action.to_keyword_setting_id),
                    action.target_strategy_mode,
                )
            return
        if action.keyword_setting_id is None:
            return
        ks_id = int(action.keyword_setting_id)
        dto = _find_dto(context, ks_id)
        if dto is None:
            return
        if action.action == V3ActionType.FORCE_OFF:
            if dto.current_mode != KeywordStrategyMode.OFF:
                self._set_mode(context, ks_id, KeywordStrategyMode.OFF)
            return
        current = dto.current_mode
        nxt = resolve_v3_action_target_mode(action, current)
        if nxt is not None:
            self._set_mode(context, ks_id, nxt)

    def _set_mode(
        self,
        context: UpdateContext,
        keyword_setting_id: int,
        mode: KeywordStrategyMode,
    ) -> None:
        dto = _find_dto(context, keyword_setting_id)
        if dto is None:
            return
        dto.current_mode = NextState(
            new_mode=KeywordMode.from_strategy_mode(mode),
            executor_name=self._executor_name,
        )


def _find_dto(context: UpdateContext, keyword_setting_id: int) -> KeywordDTO | None:
    for dto in context.keywords:
        if dto.keyword_setting_id == keyword_setting_id:
            return dto
    return None
