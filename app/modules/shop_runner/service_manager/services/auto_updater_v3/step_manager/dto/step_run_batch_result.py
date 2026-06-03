"""DTO результата серии итераций шага UP/DOWN."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Generic, TypeVar

from app.modules.shop_runner.service_manager.services.auto_updater_v3.keywords_prepared import (
    KeywordsPreparedList,
    UpdateContext,
)

PoolT = TypeVar("PoolT")


@dataclass(slots=True)
class StepRunBatchResult(Generic[PoolT]):
    """Финальный ``UpdateContext`` и все успешные picks за бюджет итераций."""

    context: UpdateContext
    picks: list[PoolT] = field(default_factory=list)

    @property
    def prepared(self) -> KeywordsPreparedList:
        """Legacy: только ``KeywordsPreparedList`` без history."""
        return self.context.prepared
