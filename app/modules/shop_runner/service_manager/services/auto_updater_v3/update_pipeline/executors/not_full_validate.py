"""Фаза NF: PFO-ключи без CH-профиля → active → MIN_CPA.

Здесь происходит только «активация режима», а не bootstrap позиции:
``target_place`` будет инициализирован уже в migrate-фазе, если ключ оказался
в PFO-контуре.

Почему GAP исключён:

- у GAP ещё нет operational ``pay_for_order``;
- GAP живёт в отдельном enable/reset контуре;
- NF validate не должен превращать GAP в как будто уже активный NF-ключ.

Именно поэтому этот executor — не общий no-CH валидатор, а gate только для PFO.
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

    Класс существует только для одного шага: подготовить активный PFO ключ к
    последующему NF bootstrap. Здесь не должно быть ни bootstrap позиции, ни
    overspend-reset, ни логики GAP enable. Если ключ не PFO, он просто проходит
    мимо.
    """

    phase_name = "validate_not_full_state"
    _skip_reason: str | None = None

    def __init__(self) -> None:
        self._next_state_manager = NextStateManager(NotFullValidateExecutor)

    def execute(self, context: UpdateContext) -> None:
        """Пройти по ключам и активировать только PFO tier.

        Validate не создает target_place и не занимается GAP. Он лишь
        нормализует режим до ``MIN_CPA`` для тех ключей, которые уже доказали,
        что они operational no-CH PFO.
        """
        self._skip_reason = None
        for dto in context.keywords:
            self._next_state_manager.validate_not_full_state(dto)

    @property
    def skip_reason(self) -> str | None:
        return self._skip_reason
