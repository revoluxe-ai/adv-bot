"""Фасад ``list[KeywordDTO]`` для legacy planner projections."""

from __future__ import annotations

from collections.abc import Iterator
from typing import TYPE_CHECKING

from app.modules.common_slaves.wildberries.models.enums import KeywordStrategyMode
from app.modules.shop_runner.service_manager.services.auto_updater_v3.keyword_dto.dto import (
    KeywordDTO,
    KeywordV3LadderState,
)

if TYPE_CHECKING:
    from app.modules.shop_runner.service_manager.services.auto_updater_v3.selector import (
        KeywordV3Context,
    )
    from app.modules.shop_runner.service_manager.services.auto_updater_v3.transition_ranking import (
        PreparedList,
    )


class KeywordBatch:
    """Рабочий набор ключей тика: planners читают ``current_mode``."""

    __slots__ = ("_items",)

    def __init__(self, items: list[KeywordDTO] | None = None) -> None:
        self._items: list[KeywordDTO] = list(items or [])

    @property
    def items(self) -> list[KeywordDTO]:
        return self._items

    def __len__(self) -> int:
        return len(self._items)

    def __iter__(self) -> Iterator[tuple[KeywordV3Context, KeywordStrategyMode]]:
        """Legacy ``PreparedList``: ``(ctx, current_mode)``."""
        for dto in self._items:
            yield dto.context, dto.current_mode

    def find(self, keyword_setting_id: int) -> KeywordDTO | None:
        for dto in self._items:
            if dto.keyword_setting_id == keyword_setting_id:
                return dto
        return None

    def iter_ladder_states(self) -> Iterator[KeywordV3LadderState]:
        for dto in self._items:
            yield from dto.ladder_states

    def to_legacy_prepared(self) -> PreparedList:
        """Явная legacy-проекция для rollout planner."""
        return list(self.__iter__())

    def copy(self) -> KeywordBatch:
        return KeywordBatch(list(self._items))

    def replace_items(self, items: list[KeywordDTO]) -> KeywordBatch:
        return KeywordBatch(items)

    @classmethod
    def from_dtos(cls, dtos: list[KeywordDTO]) -> KeywordBatch:
        return cls(dtos)
