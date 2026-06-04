"""Один шаг смены ``current_target_place`` ключа на тике V3."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class NextTargetPlace:
    """Запись перехода target_place и имя executor."""

    new_target_place: int
    executor_name: str
