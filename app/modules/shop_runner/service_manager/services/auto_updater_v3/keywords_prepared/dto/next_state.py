"""Один шаг смены ``current_mode`` ключа на тике V3 (цепочка ``KeywordDTO._next_state``)."""

from __future__ import annotations

from dataclasses import dataclass

from app.modules.common_slaves.wildberries.models.enums import KeywordStrategyMode


@dataclass(frozen=True, slots=True)
class NextState:
    """Запись перехода режима: новый mode и имя executor, выполнившего шаг."""

    new_mode: KeywordStrategyMode
    executor_name: str
