"""NF: миграция и plan-fact регулировка ``target_place`` для ключей без CH-профиля."""

from __future__ import annotations

from app.modules.common_slaves.wildberries.models.enums import KeywordStrategyMode
from app.modules.shop_runner.service_manager.services.auto_updater_v3.keyword_dto import NextTargetPlace
from app.modules.shop_runner.service_manager.services.auto_updater_v3.keyword_dto.dto import (
    UpdateContext,
)
from app.modules.shop_runner.service_manager.services.auto_updater_v3.not_full_target_place import (
    current_position_as_target_place,
    plan_fact_target_place_skip_reason,
)
from app.modules.shop_runner.service_manager.services.auto_updater_v3.keyword_v3_tier import (
    KeywordV3DataTier,
)
from app.modules.shop_runner.service_manager.services.auto_updater_v3.update_pipeline.next_state.manager import (
    NextStateManager,
)


class NotFullTargetPlaceMigrateExecutor:
    """NOT FULL MIN: первая инициализация ``target_place`` текущей позицией WB."""

    phase_name = "not_full_target_place_migrate"
    _skip_reason: str | None = None

    def execute(self, context: UpdateContext) -> None:
        """Заполнить пустой ``target_place`` для NOT FULL ключей без CH-профиля.

        Значение ``0`` означает отсутствие целевой позиции для NF-регулятора.
        На первом тике берём текущую позицию WB и не делаем plan-fact шаг в этой
        фазе; следующий executor увидит уже инициализированный target_place.
        """
        self._skip_reason = None
        for dto in context.keywords:
            if dto.data_tier == KeywordV3DataTier.FULL:
                continue
            if dto.current_mode != KeywordStrategyMode.MIN_CPA:
                continue
            if dto.current_target_place != 0:
                continue
            new_place = current_position_as_target_place(dto)
            if new_place is None:
                continue
            dto.current_target_place = NextTargetPlace(
                new_target_place=new_place,
                executor_name=self.__class__.__name__,
            )

    @property
    def skip_reason(self) -> str | None:
        return self._skip_reason


class NotFullTargetPlacePlanFactExecutor:
    """NOT FULL MIN: ±1 ``target_place`` по fact/resolve при изменении plan/fact и views."""

    phase_name = "not_full_target_place_plan_fact"
    _skip_reason: str | None = None

    def __init__(self) -> None:
        self._next_state_manager = NextStateManager(NotFullTargetPlacePlanFactExecutor)

    def execute(self, context: UpdateContext) -> None:
        """Применить NF plan-fact логику к ключам без CH-профиля.

        После общего gate на актуальность plan/fact/views двигаем
        ``target_place`` на ±1 по соотношению fact/resolve. Сброс в ``0`` для
        NOT FULL здесь не выполняется.
        """
        self._skip_reason = plan_fact_target_place_skip_reason(context.adv_state)
        if self._skip_reason is not None:
            return
        state = context.adv_state
        fact = float(state.fact_pay_for_order)  # type: ignore[arg-type]
        resolve = float(state.resolve)
        for dto in context.keywords:
            if dto.data_tier == KeywordV3DataTier.FULL:
                continue
            if (
                dto.history_target_place
                and dto.history_target_place[-1].executor_name
                == NotFullTargetPlaceMigrateExecutor.__name__
            ):
                continue
            self._next_state_manager.adjust_not_full_target_place_plan_fact(
                dto,
                fact_pay_for_order=fact,
                resolve=resolve,
            )

    @property
    def skip_reason(self) -> str | None:
        return self._skip_reason
