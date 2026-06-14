"""NF bootstrap и plan-fact регулировка ``target_place`` для no-CH ключей.

Модуль содержит две соседние фазы NF-контуры:
- ``NotFullTargetPlaceMigrateExecutor``: первый bootstrap ``target_place`` из
  текущей WB-позиции для активных PFO/GAP ключей;
- ``NotFullTargetPlacePlanFactExecutor``: последующая коррекция на ``±1`` по
  fact/resolve после bootstrap.

Обе фазы работают только для no-CH контуров. FULL ladder-ключи проходят мимо,
а ``OFF`` не инициализируется NF-логикой.
"""

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
    """Инициализировать ``target_place`` для активных PFO/GAP ключей.

    Фаза нужна только на первом заходе NF-ключа, когда target_place ещё нулевой.
    Она берёт округлённую текущую позицию WB и не трогает FULL, а также не
    оживляет ``OFF``. В результате plan-fact видит уже стартовую позицию и дальше
    может делать только ±1, не подменяя bootstrap.
    """

    phase_name = "not_full_target_place_migrate"
    _skip_reason: str | None = None

    def execute(self, context: UpdateContext) -> None:
        """Заполнить пустой ``target_place`` для активных PFO/GAP ключей.

        Если у ключа уже есть target_place или он не находится в ``MIN_CPA``, фаза
        ничего не меняет. Это защищает OFF/ladder-ключи от случайной инициализации
        и сохраняет первый шаг как чистый bootstrap.
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
    """Корректировать ``target_place`` для активных PFO/GAP ключей по plan-fact.

    Фаза вызывается только после NF validate и NF migrate. Она не инициализирует
    ключ и не сбрасывает его в ``0``: её роль — подстроить уже стартовавший NF
    ключ на ±1 относительно факта и ``resolve``.
    """

    phase_name = "not_full_target_place_plan_fact"
    _skip_reason: str | None = None

    def __init__(self) -> None:
        self._next_state_manager = NextStateManager(NotFullTargetPlacePlanFactExecutor)

    def execute(self, context: UpdateContext) -> None:
        """Применить NF plan-fact логику к активным PFO/GAP ключам.

        Сначала проверяем общий gate plan/fact/views. Затем обновляем только
        ключи, которые уже были инициализированы migrate-фазой или имеют
        существующий NF target_place. ``FULL`` и ``OFF`` ключи не затрагиваются.
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
