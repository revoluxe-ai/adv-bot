"""Супер-объект тика V3: ключи и ``AdvState`` кампании."""

from __future__ import annotations

from collections.abc import Iterator
from dataclasses import dataclass
from typing import TYPE_CHECKING

from app.modules.common_slaves.wildberries.models.enums import KeywordStrategyMode
from app.modules.shop_runner.service_manager.services.auto_updater_v3.keyword_dto.dto.adv_state import (
    AdvState,
)
from app.modules.shop_runner.service_manager.services.auto_updater_v3.keyword_dto.dto.update_context_runtime import (
    UpdateContextRuntime,
)
from app.modules.shop_runner.service_manager.services.auto_updater_v3.keyword_dto.dto.keyword_dto import (
    KeywordDTO,
)
from app.modules.shop_runner.service_manager.services.auto_updater_v3.keyword_dto.dto.keywords_prepared_list import (
    KeywordsPreparedList,
)
from app.modules.shop_runner.service_manager.services.auto_updater_v3.keyword_dto.keyword_batch import (
    KeywordBatch,
)

if TYPE_CHECKING:
    from app.modules.shop_runner.service_manager.services.auto_updater_v3.selector import (
        KeywordV3Context,
    )


@dataclass
class UpdateContext:
    """Контекст обновления кампании: ``prepared`` + ``adv_state``; ключи мутируются in-place."""

    prepared: KeywordsPreparedList
    adv_state: AdvState
    runtime: UpdateContextRuntime | None = None

    def __len__(self) -> int:
        return len(self.prepared)

    def __getitem__(self, index: int):
        return self.prepared[index]

    def __iter__(self) -> Iterator[tuple[KeywordV3Context, KeywordStrategyMode]]:
        """Legacy: ``(ctx, current_mode)`` — делегат в ``prepared``."""
        return iter(self.prepared)

    @property
    def keywords(self) -> list[KeywordDTO]:
        """Канонический список ключей тика."""
        return self.prepared.keywords

    @property
    def keyword_batch(self) -> KeywordBatch:
        """Фасад для legacy planner projections."""
        return self.prepared.batch

    @property
    def rows(self) -> list:
        """Строки ``KeywordsPreparedList``."""
        return self.prepared.rows

    def copy(self) -> UpdateContext:
        """Поверхностная копия контейнера (те же ``KeywordDTO`` refs)."""
        return UpdateContext(
            prepared=self.prepared.copy(),
            adv_state=self.adv_state.copy(),
            runtime=self.runtime,
        )
