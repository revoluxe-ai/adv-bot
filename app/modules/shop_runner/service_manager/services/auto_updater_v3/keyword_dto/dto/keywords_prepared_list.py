"""Список ключей кампании на тик V3: канонически ``list[KeywordDTO]``."""

from __future__ import annotations

from collections.abc import Iterator
from typing import TYPE_CHECKING

from app.modules.common_slaves.wildberries.models.enums import KeywordStrategyMode
from app.modules.shop_runner.service_manager.services.auto_updater_v3.keyword_dto.dto.keyword_dto import (
    KeywordDTO,
)
from app.modules.shop_runner.service_manager.services.auto_updater_v3.keyword_dto.dto.keyword_prepared_row import (
    KeywordPreparedRow,
)
from app.modules.shop_runner.service_manager.services.auto_updater_v3.keyword_dto.dto.keyword_v3_ladder_state import (
    KeywordV3LadderState,
)
from app.modules.shop_runner.service_manager.services.auto_updater_v3.keyword_dto.keyword_batch import (
    KeywordBatch,
)

if TYPE_CHECKING:
    from app.modules.shop_runner.service_manager.services.auto_updater_v3.selector import (
        KeywordV3Context,
    )


class KeywordsPreparedList:
    """Ключи кампании: ``KeywordDTO`` + legacy ``KeywordPreparedRow`` / ``PreparedList``."""

    __slots__ = ("_keywords",)

    def __init__(
        self,
        rows: list[KeywordPreparedRow] | None = None,
        *,
        keywords: list[KeywordDTO] | None = None,
    ) -> None:
        if keywords is not None:
            self._keywords = list(keywords)
        elif rows is not None:
            self._keywords = [KeywordDTO.from_prepared_row(row) for row in rows]
        else:
            self._keywords = []

    @property
    def keywords(self) -> list[KeywordDTO]:
        """Канонический список DTO для Context и executors."""
        return self._keywords

    @property
    def batch(self) -> KeywordBatch:
        return KeywordBatch(self._keywords)

    @property
    def rows(self) -> list[KeywordPreparedRow]:
        """Legacy строки для постепенной миграции planner API."""
        return [dto.to_prepared_row() for dto in self._keywords]

    def __len__(self) -> int:
        return len(self._keywords)

    def __getitem__(self, index: int) -> KeywordPreparedRow:
        return self._keywords[index].to_prepared_row()

    def __iter__(self) -> Iterator[tuple[KeywordV3Context, KeywordStrategyMode]]:
        """Legacy: ``(KeywordV3Context, active_mode)``."""
        return iter(self.batch)

    def iter_rows(self) -> Iterator[KeywordPreparedRow]:
        return iter(self.rows)

    def iter_dtos(self) -> Iterator[KeywordDTO]:
        return iter(self._keywords)

    def iter_all_ladder_states(self) -> Iterator[KeywordV3LadderState]:
        for dto in self._keywords:
            yield from dto.ladder_states

    def copy(self) -> KeywordsPreparedList:
        return KeywordsPreparedList(keywords=list(self._keywords))

    def with_keywords(self, keywords: list[KeywordDTO]) -> KeywordsPreparedList:
        return KeywordsPreparedList(keywords=keywords)

    def to_legacy_list(self) -> list[tuple[KeywordV3Context, KeywordStrategyMode]]:
        return list(self.batch)
