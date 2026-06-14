"""NF bootstrap и plan-fact регулировка ``target_place`` для no-CH PFO ключей.

Модуль содержит две соседние фазы NF-контуры:
- ``NotFullTargetPlaceMigrateExecutor``: первый bootstrap ``target_place`` из
  текущей WB-позиции только для активных PFO ключей;
- ``NotFullTargetPlacePlanFactExecutor``: последующая коррекция на ``±1`` по
  fact/resolve после bootstrap.

Обе фазы работают только для PFO no-CH контура. FULL ladder-ключи проходят мимо,
GAP остаётся в отдельном enable/reset контуре, а ``OFF`` не инициализируется
NF-логикой.
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
    """Инициализировать ``target_place`` для активных PFO ключей.

    Это первая NF bootstrap-фаза. Её смысл не в оптимизации ставки и не в
    ladder-выборе, а в том, чтобы перевести no-CH ключ из состояния
    ``target_place=0`` в состояние «есть стартовая точка регулировки».

    Почему это нужно:
    - до migrate у активного PFO ключа ``target_place=0`` означает не
      целевую позицию, а отсутствие инициализации;
    - после migrate ключ получает округлённую текущую WB-позицию и дальше уже
      может участвовать в NF plan-fact как полноценный регулируемый элемент;
    - FULL, GAP, OFF и ключи с уже заполненным target_place остаются без изменений.

    Таким образом, migrate отделяет bootstrap от дальнейшей коррекции и не
    смешивает no-CH контур с ladder-контуром.
    """

    phase_name = "not_full_target_place_migrate"
    _skip_reason: str | None = None

    def execute(self, context: UpdateContext) -> None:
        """Заполнить пустой ``target_place`` для активных PFO ключей.

        Шаг выполняется только если одновременно соблюдены все условия:

        - ключ относится к PFO tier, а не к FULL или GAP;
        - текущий режим уже ``MIN_CPA``;
        - ``target_place`` ещё не инициализирован (равен ``0``).

        Если любое из условий не выполнено, migrate не делает ничего. Это
        гарантирует, что OFF не будет случайно «оживлён», FULL и GAP не попадут
        в NF bootstrap, а повторные тики не будут перетирать уже выбранный
        стартовый target_place.
        """
        self._skip_reason = None
        for dto in context.keywords:
            if dto.data_tier != KeywordV3DataTier.PFO:
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
    """Корректировать ``target_place`` для активных PFO ключей по plan-fact.

    Это вторая NF фаза после bootstrap. Она не должна решать задачи инициализации,
    не должна сбрасывать target_place в 0 и не должна подменять ladder-логики
    FULL-ветки. Её единственная ответственность — после NF validate/migrate
    двигать уже стартовавший PFO ключ на ``±1`` относительно
    ``fact_pay_for_order`` и ``resolve``.

    Важно: если ключ только что прошёл migrate, plan-fact в этом же тике его не
    двигает. Так первый тик остаётся чистым bootstrap, а не bootstrap + correction
    одновременно.
    """

    phase_name = "not_full_target_place_plan_fact"
    _skip_reason: str | None = None

    def __init__(self) -> None:
        self._next_state_manager = NextStateManager(NotFullTargetPlacePlanFactExecutor)

    def execute(self, context: UpdateContext) -> None:
        """Применить NF plan-fact логику к активным PFO ключам.

        Алгоритм:

        1. Проверить общий gate план/факт/views.
        2. Пропустить FULL-ключи, потому что они живут в ladder-контуре.
        3. Пропустить ключи, которые только что были инициализированы migrate
           в этом же тике: их стартовая позиция должна сохраниться без
           немедленной коррекции.
        4. Для остальных PFO ключей применить plan-fact шаг ``±1``.

        Тем самым эта фаза поддерживает NF-контур, но не выполняет bootstrap и
        не вмешивается в OFF / FULL.
        """
        self._skip_reason = plan_fact_target_place_skip_reason(context.adv_state)
        if self._skip_reason is not None:
            return
        state = context.adv_state
        fact = float(state.fact_pay_for_order)  # type: ignore[arg-type]
        resolve = float(state.resolve)
        for dto in context.keywords:
            if dto.data_tier != KeywordV3DataTier.PFO:
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
