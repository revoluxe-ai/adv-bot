"""NF: миграция и plan-fact регулировка ``target_place`` для ключей без CH-профиля."""

from __future__ import annotations

from app.modules.shop_runner.service_manager.services.auto_updater_v3.keyword_dto.dto import (
    UpdateContext,
)

from app.modules.shop_runner.service_manager.services.auto_updater_v3.update_pipeline.next_state.manager import (
    NextStateManager,
)
#
#
# class NotFullTargetPlaceMigrateExecutor:
#     """Миграция NOT FULL: ``target_place=0`` → ``round(position) `` (реальная позиция)."""
#
#     phase_name = "not_full_target_place_migrate"
#     _skip_reason: str | None = None
#
#     def __init__(self) -> None:
#         self._next_state_manager = NextStateManager(NotFullTargetPlaceMigrateExecutor)
#
#     def execute(self, context: UpdateContext) -> None:
#         overspend = campaign_cpo_exceeds_max(context.adv_state)
#         if overspend:
#             self._skip_reason = "campaign_cpo_gt_max"
#             return
#         self._skip_reason = None
#         for dto in context.keywords:
#             self._next_state_manager.migrate_not_full_target_place(dto)
#
#     @property
#     def skip_reason(self) -> str | None:
#         return self._skip_reason

#
# class NotFullTargetPlaceOverspendResetExecutor:
#     """OVERSPEND: NOT FULL MIN с ``PFO > raise_cpo_ceiling`` → ``target_place=0``."""
#
#     phase_name = "not_full_target_place_overspend_reset"
#     _skip_reason: str | None = None
#
#     def __init__(self) -> None:
#         self._next_state_manager = NextStateManager(
#             NotFullTargetPlaceOverspendResetExecutor
#         )
#
#     def execute(self, context: UpdateContext) -> None:
#         if not campaign_cpo_exceeds_max(context.adv_state):
#             self._skip_reason = "fact_within_max"
#             return
#         self._skip_reason = None
#         for dto in context.keywords:
#             self._next_state_manager.reset_not_full_target_place_overspend(dto)
#
#     @property
#     def skip_reason(self) -> str | None:
#         return self._skip_reason


class NotFullTargetPlacePlanFactExecutor:
    """NOT FULL MIN: ±1 ``target_place`` по fact/resolve при изменении plan/fact и views."""

    phase_name = "not_full_target_place_plan_fact"
    _skip_reason: str | None = None

    def __init__(self) -> None:
        self._next_state_manager = NextStateManager(NotFullTargetPlacePlanFactExecutor)

    def execute(self, context: UpdateContext) -> None:
        state = context.adv_state
        fact = float(state.fact_pay_for_order)  # type: ignore[arg-type]
        resolve = float(state.resolve)
        for dto in context.keywords:
            if dto.is_not_full():
                if dto.calculated_keyword.pay_for_order:
                    self._next_state_manager.adjust_not_full_target_place_plan_fact(
                        dto,
                        fact_pay_for_order=fact,
                        resolve=resolve,
                        max_pay_for_order=context.adv_state.max_pay_for_order
                    )

    @property
    def skip_reason(self) -> str | None:
        return self._skip_reason
