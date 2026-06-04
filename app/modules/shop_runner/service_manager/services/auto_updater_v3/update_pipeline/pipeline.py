"""Цепочка executors V3: in-place мутация ``UpdateContext``."""

from __future__ import annotations

from collections.abc import Sequence

from app.modules.shop_runner.service_manager.services.auto_updater_v3.keyword_dto.dto import (
    UpdateContext,
)
from app.modules.shop_runner.service_manager.services.auto_updater_v3.update_pipeline.executors.base import (
    UpdateExecutor,
)


class UpdatePipeline:
    """Последовательный прогон executors (mutate ``UpdateContext`` in-place)."""

    def __init__(self, executors: Sequence[UpdateExecutor]) -> None:
        self._executors = tuple(executors)

    @property
    def executors(self) -> tuple[UpdateExecutor, ...]:
        """Зарегистрированные executors в порядке выполнения."""
        return self._executors

    def update(self, context: UpdateContext) -> UpdateContext:
        """Прогнать executors in-place; вернуть тот же ``UpdateContext``."""
        for executor in self._executors:
            executor.execute(context)
        return context
