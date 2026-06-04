"""Фаза V: validate hard_status=1 → OFF через ``NextState``."""

from __future__ import annotations

from app.modules.shop_runner.service_manager.services.auto_updater_v3.keyword_dto.dto import (
    UpdateContext,
)
from app.modules.shop_runner.service_manager.services.auto_updater_v3.update_pipeline.next_state.manager import (
    NextStateManager,
)


class HardStatusValidateExecutor:
    """VALIDATE hard_status: авто-ключи (1) → ``OFF``."""

    phase_name = "validate_state_by_hard_status"
    _skip_reason: str | None = None

    def __init__(self) -> None:
        self._next_state_manager = NextStateManager(HardStatusValidateExecutor)

    def execute(self, context: UpdateContext) -> None:
        self._skip_reason = None
        for dto in context.keywords:
            self._next_state_manager.validate_state_by_hard_status(dto)

    @property
    def skip_reason(self) -> str | None:
        return self._skip_reason
