"""DTO результата одной итерации шага UP/DOWN."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Generic, TypeVar

from app.modules.shop_runner.service_manager.services.auto_updater_v3.keywords_prepared import (
    KeywordsPreparedList,
    UpdateContext,
)

PoolT = TypeVar("PoolT")


@dataclass(slots=True)
class StepRunResult(Generic[PoolT]):
    """Обновлённый ``UpdateContext`` и выбранный pick."""

    context: UpdateContext
    pick: PoolT | None
    pool_size: int = 0

    @property
    def prepared(self) -> KeywordsPreparedList:
        """Legacy: только ``KeywordsPreparedList`` без history."""
        return self.context.prepared
