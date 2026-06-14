"""Plan-fact управление ``target_place`` для NOT FULL ключей V3 (нет CH-профиля).

Миграция с ``target_place=0`` на текущую позицию WB и сдвиг ±1 по соотношению
``fact_pay_for_order`` / ``resolve`` (порог ``MAX_PAY_STABILIZATION_RATIO``).
Сброс ``target_place`` в 0 для NOT FULL не выполняется.
"""

from __future__ import annotations

import math
from typing import TYPE_CHECKING

from app.modules.common_slaves.wildberries.models.enums import KeywordStrategyMode
from app.modules.shop_runner.service_manager.old_modules.setting_auto_updater_v2.adv_control_system.sales_state.sales_states import (
    MAX_PAY_STABILIZATION_RATIO,
)
from app.modules.shop_runner.service_manager.services.auto_updater_v3.keyword_v3_tier import (
    KeywordV3DataTier,
)

if TYPE_CHECKING:
    from app.modules.shop_runner.service_manager.services.auto_updater_v3.keyword_dto.dto import (
        AdvState,
        KeywordDTO,
    )

NOT_FULL_TARGET_PLACE_MIN = 1
NOT_FULL_TARGET_PLACE_MAX = 300


def clamp_not_full_target_place(place: int) -> int:
    """Ограничить целевую позицию диапазоном legacy TargetPlaceUp/Down."""
    return max(NOT_FULL_TARGET_PLACE_MIN, min(NOT_FULL_TARGET_PLACE_MAX, int(place)))


def current_position_as_target_place(keyword: "KeywordDTO") -> int | None:
    """Стартовая tp после миграции: округлённая реальная позиция WB."""
    pos = keyword.calculated_keyword.position
    if pos <= 0:
        return None
    real_place = int(math.floor(pos + 0.5))
    return clamp_not_full_target_place(real_place)


def compute_not_full_target_place_delta(
    fact_pay_for_order: float,
    resolve: float,
) -> int:
    """Сдвиг tp: fact < 0.9×resolve → −1 (выше), иначе +1 (ниже)."""
    threshold = MAX_PAY_STABILIZATION_RATIO * float(resolve)
    if float(fact_pay_for_order) < threshold:
        return -1
    return 1


def plan_fact_target_place_skip_reason(state: AdvState) -> str | None:
    """Gate NF_plan_fact_tp: те же проверки plan/fact/views, что у calibration."""
    if state.plan_fact_equal and state.views_equal:
        return "plan_fact_unchanged_and_views_unchanged"
    if state.plan_fact_equal:
        return "plan_fact_unchanged"
    if state.views_equal:
        return "views_unchanged"
    if float(state.resolve) <= 0:
        return "resolve_invalid"
    if state.fact_pay_for_order is None:
        return "no_fact_pay_for_order"
    return None


def adjust_not_full_target_place_for_plan_fact(
    keyword: "KeywordDTO",
    *,
    fact_pay_for_order: float,
    resolve: float,
) -> int | None:
    """Применить ±1 к ``current_target_place`` для NOT FULL MIN; ``None`` если no-op.

    Сброс ``target_place`` в ``0`` не выполняется: NOT FULL управляется только
    миграцией с нуля и plan-fact шагом в пределах legacy диапазона.
    """
    if keyword.data_tier == KeywordV3DataTier.FULL:
        return None
    if keyword.current_mode != KeywordStrategyMode.MIN_CPA:
        return None
    delta = compute_not_full_target_place_delta(fact_pay_for_order, resolve)
    new_place = clamp_not_full_target_place(keyword.current_target_place + delta)
    if new_place == keyword.current_target_place:
        return None
    return new_place
