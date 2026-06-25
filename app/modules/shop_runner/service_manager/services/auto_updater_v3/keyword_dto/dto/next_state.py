"""Один шаг смены ``current_mode`` ключа на тике V3 (цепочка ``KeywordDTO._next_state``)."""

from __future__ import annotations

from dataclasses import dataclass

from app.modules.shop_runner.service_manager.services.auto_updater_v3.keyword_dto.dto.keyword_mode import (
    KeywordMode,
)


@dataclass(frozen=True, slots=True)
class NextState:
    """Запись перехода режима с атрибуцией executor и phase_id.

    ``executor_name`` остаётся техническим именем класса для reason/debug, а
    ``phase_id`` используется для отчёта и post-hoc audit. Если ``phase_id`` не
    задан, downstream-код может восстановить его из ``executor_name``.
    """

    new_mode: KeywordMode
    executor_name: str
    phase_id: str | None = None
