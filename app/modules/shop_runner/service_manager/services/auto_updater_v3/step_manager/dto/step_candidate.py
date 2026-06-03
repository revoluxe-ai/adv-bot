"""DTO кандидата одного шага DOWN/UP на ключ."""

from __future__ import annotations

from dataclasses import dataclass

from app.modules.common_slaves.wildberries.models.enums import KeywordStrategyMode


@dataclass(frozen=True, slots=True)
class StepCandidate:
    """Выбранный переход ``from_mode`` → ``to_mode`` для одного ``keyword_setting_id``."""

    keyword_setting_id: int
    from_mode: KeywordStrategyMode
    to_mode: KeywordStrategyMode
    state_cost: float = 0.0
    pay_for_order: float = 0.0
