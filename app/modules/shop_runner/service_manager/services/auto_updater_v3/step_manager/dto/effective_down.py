"""DTO результата одного effective DOWN."""

from __future__ import annotations

from dataclasses import dataclass

from app.modules.common_slaves.wildberries.models.enums import KeywordStrategyMode


@dataclass(frozen=True, slots=True)
class EffectiveDown:
    """Результат одного effective DOWN (схлопнутые alias + released aggression)."""

    from_mode: KeywordStrategyMode
    to_mode: KeywordStrategyMode | None
    skipped_aliases: tuple[str, ...]
    released_aggression_steps: int
