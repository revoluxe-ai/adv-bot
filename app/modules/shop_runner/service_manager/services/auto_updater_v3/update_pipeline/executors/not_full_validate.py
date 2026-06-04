"""Фаза NF: нет CH-профиля (PFO / GAP) → active → MIN_CPA + target_place=0.

Заменяет legacy ``cap_down`` для ключей без ``position_profile``. При наличии профиля
лестница строится из CH (FULL); отдельный cap по eligibility не применяется.
"""

from __future__ import annotations

from app.modules.shop_runner.service_manager.services.auto_updater_v3.keyword_dto.dto import (
    UpdateContext,
)
from app.modules.shop_runner.service_manager.services.auto_updater_v3.update_pipeline.next_state.manager import (
    NextStateManager,
)


class NotFullValidateExecutor:
    """Validate NOT FULL keys: команда ``NOT_FULL_ACTIVATE`` через ``NextStateManager``."""

    phase_name = "validate_not_full_state"
    _skip_reason: str | None = None

    def __init__(self) -> None:
        self._next_state_manager = NextStateManager(NotFullValidateExecutor)

    def execute(self, context: UpdateContext) -> None:
        self._skip_reason = None
        for dto in context.keywords:
            self._next_state_manager.validate_not_full_state(dto)

    @property
    def skip_reason(self) -> str | None:
        return self._skip_reason
