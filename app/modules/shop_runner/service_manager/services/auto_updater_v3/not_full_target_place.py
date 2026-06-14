"""Plan-fact управление ``target_place`` для NOT FULL ключей V3 (нет CH-профиля).

Миграция с ``target_place=0`` на ``round(position) - 1`` (реальная позиция − 1) и сдвиг ±1 по соотношению
``fact_pay_for_order`` / ``resolve`` (порог ``MAX_PAY_STABILIZATION_RATIO``).
При OVERSPEND кампании — сброс tp в 0 только для ключей с ``PFO > raise_cpo_ceiling``.
Используется executors preamble NF_migrate / NF_overspend_tp / NF_plan_fact_tp.
"""

from __future__ import annotations

import math
from typing import TYPE_CHECKING

from app.modules.common_slaves.wildberries.models.enums import KeywordStrategyMode
from app.modules.shop_runner.service_manager.old_modules.setting_auto_updater_v2.adv_control_system.sales_state.sales_states import (
    MAX_PAY_STABILIZATION_RATIO,
)
from app.modules.shop_runner.service_manager.services.auto_updater_v3.cpo_max_boundary import (
    campaign_cpo_over_max,
    keyword_pfo_over_max,
)
from app.modules.shop_runner.service_manager.services.auto_updater_v3.keyword_dto.dto.adv_state import (
    AdvState,
)

if TYPE_CHECKING:
    from app.modules.shop_runner.service_manager.services.auto_updater_v3.keyword_dto.dto import (
        KeywordDTO,
    )

NOT_FULL_TARGET_PLACE_MIN = 1
NOT_FULL_TARGET_PLACE_MAX = 300
NOT_FULL_TARGET_PLACE_OVERSPEND = 0


def campaign_cpo_exceeds_max(state: AdvState) -> bool:
    """``fact_pay_for_order > plan.max_pay_for_order`` (OVERSPEND кампании)."""
    if state.fact_pay_for_order is None:
        return False
    return campaign_cpo_over_max(
        state.fact_pay_for_order,
        float(state.max_pay_for_order),
    )


def campaign_overspend_from_plan_fact(
    fact_pay_for_order: float | None,
    max_pay_for_order: float,
) -> bool:
    """OVERSPEND по plan/fact без ``AdvState`` (sync fallback при load)."""
    return campaign_cpo_over_max(fact_pay_for_order, max_pay_for_order)


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


def reset_not_full_target_place_on_overspend(
    keyword: "KeywordDTO",
    *,
    max_pay: float,
) -> bool:
    """OVERSPEND: NOT FULL MIN с ``PFO > max_pay`` → ``target_place=0``."""
    if not keyword_pfo_over_max(keyword.calculated_keyword.pay_for_order, max_pay):
        return False
    if not keyword.is_not_full():
        return False
    if keyword.current_mode != KeywordStrategyMode.MIN_CPA:
        return False
    if keyword.current_target_place == NOT_FULL_TARGET_PLACE_OVERSPEND:
        return False
    return True


def adjust_not_full_target_place_for_plan_fact(
    keyword: "KeywordDTO",
    *,
    fact_pay_for_order: float,
    resolve: float,
    max_pay_for_order: float,
) -> int | None:
    """Применить ±1 к ``current_target_place`` для NOT FULL MIN; ``None`` если no-op.

    Для ключей без CH-профиля факт на границе ``max_pay_for_order`` считается
    safety-stop: здесь мы сразу уводим ``target_place`` в ``0``, чтобы не продолжать
    бустить ключ, который уже упёрся в плановый потолок без профиля для тонкой
    bid-регуляции.
    """
    if not keyword.is_not_full():
        return None
    if keyword.current_mode != KeywordStrategyMode.MIN_CPA:
        return None
    if fact_pay_for_order >= max_pay_for_order:
        return 0
    delta = compute_not_full_target_place_delta(fact_pay_for_order, resolve)
    new_place = clamp_not_full_target_place(keyword.current_target_place + delta)
    if new_place == keyword.current_target_place:
        return None
    return new_place
