"""NF: миграция и plan-fact регулировка ``target_place`` для ключей без CH-профиля."""

from __future__ import annotations

from app.modules.shop_runner.service_manager.services.auto_updater_v3.keyword_dto import NextTargetPlace
from app.modules.shop_runner.service_manager.services.auto_updater_v3.keyword_dto.dto import (
    UpdateContext,
)
from app.modules.shop_runner.service_manager.services.auto_updater_v3.not_full_target_place import (
    plan_fact_target_place_skip_reason,
)
from app.modules.shop_runner.service_manager.services.auto_updater_v3.update_pipeline.next_state.manager import (
    NextStateManager,
)


class NotFullTargetPlacePlanFactExecutor:
    """NOT FULL MIN: ±1 ``target_place`` по fact/resolve при изменении plan/fact и views."""

    phase_name = "not_full_target_place_plan_fact"
    _skip_reason: str | None = None

    def __init__(self) -> None:
        self._next_state_manager = NextStateManager(NotFullTargetPlacePlanFactExecutor)

    def execute(self, context: UpdateContext) -> None:
        self._skip_reason = plan_fact_target_place_skip_reason(context.adv_state)
        if self._skip_reason is not None:
            return
        state = context.adv_state
        fact = float(state.fact_pay_for_order)  # type: ignore[arg-type]
        resolve = float(state.resolve)
        for dto in context.keywords:
            if not dto.is_not_full():
                continue
            if not dto.calculated_keyword.pay_for_order:
                dto.current_target_place = NextTargetPlace(
                    new_target_place=0,
                    executor_name=self.__name__
                )
                continue
            self._next_state_manager.adjust_not_full_target_place_plan_fact(
                dto,
                fact_pay_for_order=fact,
                resolve=resolve,
                max_pay_for_order=float(context.adv_state.max_pay_for_order),
            )

    @property
    def skip_reason(self) -> str | None:
        return self._skip_reason
