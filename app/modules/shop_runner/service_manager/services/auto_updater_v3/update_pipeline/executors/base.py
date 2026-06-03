"""Базовый протокол executor для ``UpdatePipeline`` (in-place ``NextState``)."""

from __future__ import annotations

from abc import ABC

from app.modules.shop_runner.service_manager.services.auto_updater_v3.dto import (
    V3Action,
)
from app.modules.shop_runner.service_manager.services.auto_updater_v3.keywords_prepared.dto import (
    UpdateContext,
)
from app.modules.shop_runner.service_manager.services.auto_updater_v3.update_pipeline.next_state.manager import (
    NextStateManager,
)


class UpdateExecutor(ABC):
    """Одна preamble-фаза V3: in-place мутация ``KeywordDTO._next_state``."""

    phase_name: str
    _skip_reason: str | None = None

    def check_skip(self, context: UpdateContext) -> str | None:
        """``None`` — выполнять; иначе причина пропуска (``skip_reason`` для tick report)."""
        return None

    def plan_actions(self, context: UpdateContext) -> list[V3Action]:
        """Planned actions для фаз с rollout planner (применяются через ``NextState``)."""
        return []

    def execute(self, context: UpdateContext) -> None:
        """Выполнить фазу in-place или установить ``skip_reason``."""
        self._skip_reason = self.check_skip(context)
        if self._skip_reason is not None:
            return
        actions = self.plan_actions(context)
        NextStateManager(type(self)).apply_v3_actions(context, actions)

    @property
    def skip_reason(self) -> str | None:
        """Причина пропуска последнего ``execute``."""
        return self._skip_reason
