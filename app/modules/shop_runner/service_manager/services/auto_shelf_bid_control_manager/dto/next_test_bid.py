"""DTO для результата выбора следующей тестовой ставки."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class NextTestBid:
    """Результат выбора следующей тестовой точки."""

    bid_minor: int | None
    max_distance_minor: int
    covered_count: int

