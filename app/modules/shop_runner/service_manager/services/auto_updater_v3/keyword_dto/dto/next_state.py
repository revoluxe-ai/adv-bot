"""Один шаг смены ``current_mode`` ключа на тике V3 (цепочка ``KeywordDTO._next_state``)."""

from __future__ import annotations

from dataclasses import dataclass

from app.modules.shop_runner.service_manager.services.auto_updater_v3.keyword_dto.dto.keyword_mode import (
    KeywordMode,
)


@dataclass(frozen=True, slots=True)
class NextState:
    """Запись перехода режима: ``KeywordMode`` и имя executor."""

    new_mode: KeywordMode
    executor_name: str
