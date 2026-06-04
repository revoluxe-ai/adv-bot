"""Базовый протокол preamble executor (in-place ``NextState``)."""

from __future__ import annotations

from typing import Protocol

from app.modules.shop_runner.service_manager.services.auto_updater_v3.keyword_dto.dto.update_context import (
    UpdateContext,
)


class PreambleExecutor(Protocol):
    """Одна preamble-фаза V3: in-place мутация ``KeywordDTO._next_state``."""

    phase_name: str

    def execute(self, context: UpdateContext) -> None:
        """Выполнить фазу in-place или установить ``skip_reason``."""
        ...

    @property
    def skip_reason(self) -> str | None:
        """Причина пропуска последнего ``execute``."""
        ...


# Backward-compatible alias (tests / imports).
UpdateExecutor = PreambleExecutor
