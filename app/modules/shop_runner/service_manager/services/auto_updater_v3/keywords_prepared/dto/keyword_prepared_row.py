"""Строка ``KeywordsPreparedList``: ключ, stored/active mode, ladder states."""

from __future__ import annotations

from dataclasses import dataclass, replace

from typing import TYPE_CHECKING

from app.modules.common_slaves.wildberries.models.enums import KeywordStrategyMode
from app.modules.shop_runner.service_manager.services.auto_updater_v3.keywords_prepared.dto.keyword_v3_ladder_state import (
    KeywordV3LadderState,
)
from app.modules.wb_adv_updater.calculated_keywords_manager.dto.calculated_keyword import (
    CalculatedKeyword,
)
from app.modules.wb_adv_updater.calculated_keywords_manager.dto.position_profile_point import (
    PositionProfilePoint,
)

if TYPE_CHECKING:
    from app.modules.shop_runner.service_manager.services.auto_updater_v3.selector import (
        KeywordV3Context,
    )


@dataclass(frozen=True, slots=True)
class KeywordPreparedRow:
    """Один ключ на тик: baseline ``stored_mode``, рабочий ``active_mode``, все ladder states."""

    keyword: CalculatedKeyword
    position_profile: list[PositionProfilePoint] | None
    stored_mode: KeywordStrategyMode
    active_mode: KeywordStrategyMode
    states: tuple[KeywordV3LadderState, ...]

    @property
    def keyword_setting_id(self) -> int:
        """``keyword_setting_original_id`` (0 если нет id)."""
        return int(self.keyword.keyword_setting_original_id or 0)

    @property
    def context(self) -> KeywordV3Context:
        """Legacy ``KeywordV3Context`` для planner/collector."""
        from app.modules.shop_runner.service_manager.services.auto_updater_v3.selector import (
            KeywordV3Context,
        )

        return KeywordV3Context(
            keyword=self.keyword,
            position_profile=self.position_profile,
        )

    def with_active_mode(self, mode: KeywordStrategyMode) -> KeywordPreparedRow:
        """Копия строки с новым ``active_mode`` (stored не меняется)."""
        return replace(self, active_mode=mode)

    def states_for_keyword(self) -> tuple[KeywordV3LadderState, ...]:
        """Ladder states этого ключа (alias ``states``)."""
        return self.states

    def __getitem__(self, index: int) -> KeywordV3Context | KeywordStrategyMode:
        """Legacy index: ``0`` → context, ``1`` → ``active_mode`` (для ``row[0]``, ``row[1]``)."""
        if index == 0:
            return self.context
        if index == 1:
            return self.active_mode
        raise IndexError(index)
