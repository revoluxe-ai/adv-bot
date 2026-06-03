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
from app.modules.shop_runner.service_manager.services.auto_updater_v3.v3_operable_keywords import (
    HARD_STATUS_AUTO_MODE,
)


class NextStateManager:
    """Операции in-place над ``KeywordDTO``; ``executor_name`` пишется в каждый ``NextState``."""

    def __init__(self, executor_class: type) -> None:
        self._executor_name = executor_class.__name__


    def validate_state_by_hard_status(self, keyword: KeywordDTO) -> None:
        """``hard_status=1`` → ``OFF``; всегда append для трассировки."""
        if keyword.hard_status != HARD_STATUS_AUTO_MODE:
            return
        keyword.current_mode = NextState(
            new_mode=KeywordStrategyMode.OFF,
            executor_name=self._executor_name,
        )
