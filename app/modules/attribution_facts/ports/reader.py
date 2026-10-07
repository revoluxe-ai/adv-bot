"""Порт чтения attribution facts (transport-independent)."""

from __future__ import annotations

from typing import Protocol

from app.modules.attribution_facts.domain.models import (
    AttributionQueryResult,
    AttributionScope,
    DateWindow,
)


class AttributionFactsReader(Protocol):
    """
    Read-side контракт для AI Package, analysis и будущего MCP.

    Реализации Slice C читают CH; Slice A предоставляет in-memory fake в тестах.
    """

    async def query(
        self,
        scope: AttributionScope,
        window: DateWindow,
    ) -> AttributionQueryResult:
        """
        Вернуть facts, coverage и reconciliation summary для scope/window.

        Args:
            scope: shop и physical adv ids (без synthetic pair merge по умолчанию).
            window: Включительные календарные границы.

        Returns:
            AttributionQueryResult без exposure физического storage.
        """
        ...
