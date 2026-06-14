"""Фаза NF: PFO-ключи без CH-профиля → active → MIN_CPA.

``target_place`` — после NF: ``NotFullTargetPlaceMigrateExecutor`` / plan-fact.
GAP-контур в эту фазу не входит: для него есть отдельный enable/reset путь.
Заменяет legacy ``cap_down`` для PFO-ключей без ``position_profile``.
"""

from __future__ import annotations

from app.modules.shop_runner.service_manager.services.auto_updater_v3.keyword_dto.dto import (
    UpdateContext,
)
from app.modules.shop_runner.service_manager.services.auto_updater_v3.update_pipeline.next_state.manager import (
    NextStateManager,
)


class NotFullValidateExecutor:
    """Validate PFO keys: команда ``NOT_FULL_ACTIVATE`` через ``NextStateManager``.

    GAP-key не переводится здесь в ``MIN_CPA`` для NF bootstrap: он живёт в
    отдельном enable/reset контуре и станет NF-кандидатом только после появления
    operational PFO.
    """

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
