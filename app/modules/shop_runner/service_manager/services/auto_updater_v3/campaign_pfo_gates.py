"""SSOT гейты кампании по fact/max pay_for_order и keyword.pay_for_order.

Используется preamble NORMAL: блок ladder UP и фаза OFF при «глубоком overspend»
(``fact > 1.1 * max``) для ключей с ``keyword.pay_for_order > max``.
"""

from __future__ import annotations

from app.modules.shop_runner.service_manager.services.auto_updater_v3.keyword_dto.dto import (
    AdvState,
    KeywordDTO,
)

FACT_OVER_MAX_DEEP_OVERSPEND_RATIO = 1.1


def is_deep_overspend(adv_state: AdvState) -> bool:
    """``True``, если факт CPA строго выше ``1.1 * plan.max_pay_for_order``."""
    if adv_state.fact_pay_for_order is None:
        return False
    max_pay = float(adv_state.max_pay_for_order)
    if max_pay <= 0:
        return False
    return float(adv_state.fact_pay_for_order) > (
        FACT_OVER_MAX_DEEP_OVERSPEND_RATIO * max_pay
    )


def keyword_pay_for_order_over_plan_max(
    dto: KeywordDTO,
    *,
    max_pay: float,
) -> bool:
    """``keyword.pay_for_order`` строго выше потолка плана (как в NO CH bootstrap)."""
    pfo = dto.calculated_keyword.pay_for_order
    if pfo is None:
        return False
    return float(pfo) > float(max_pay)


def deep_overspend_blocks_ladder_up(dto: KeywordDTO, adv_state: AdvState) -> bool:
    """Запрет ladder UP: deep overspend на РК и PFO ключа выше max."""
    if not is_deep_overspend(adv_state):
        return False
    return keyword_pay_for_order_over_plan_max(
        dto,
        max_pay=float(adv_state.max_pay_for_order),
    )
