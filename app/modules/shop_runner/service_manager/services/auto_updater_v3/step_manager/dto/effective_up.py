"""DTO результата одного effective UP."""

from __future__ import annotations

from dataclasses import dataclass

from app.modules.common_slaves.wildberries.models.enums import KeywordStrategyMode


@dataclass(frozen=True, slots=True)
class EffectiveUp:
    """Результат одного effective UP (схлопнутые alias)."""

    from_mode: KeywordStrategyMode
    to_mode: KeywordStrategyMode | None
    skipped_aliases: tuple[str, ...]
