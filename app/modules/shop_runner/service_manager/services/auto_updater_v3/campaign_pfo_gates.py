"""SSOT гейты кампании по fact/max pay_for_order и keyword.pay_for_order.

Пороги «1 от MAX плана» — доля ``plan.max_pay_for_order`` из ``settings_master`` (``.env``):

- ``V3_PAY_FOR_ORDER_GAP_ENABLE_PLAN_HEADROOM_RATIO`` (default ``0.9``) — skip enable;
- ``V3_PAY_FOR_ORDER_OFF_PLAN_HEADROOM_RATIO`` (default ``0.9``) — фаза pfo_off.

- ``pay_for_order_gap_enable`` — skip enable, если fact уже в этой зоне;
- ``pay_for_order_over_max_off_on_deep_overspend`` — OFF ключей с ``PFO > max`` в этой зоне.
"""

from __future__ import annotations

from app.modules.shop_runner.service_manager.services.auto_updater_v3.keyword_dto.dto import (
    AdvState,
    KeywordDTO,
)
from app.settings import settings


def gap_enable_plan_headroom_ratio() -> float:
    """Доля plan.max для skip ``PayForOrderGapEnableExecutor`` (env, default 0.9)."""
    return float(settings.V3_PAY_FOR_ORDER_GAP_ENABLE_PLAN_HEADROOM_RATIO)


def pfo_off_plan_headroom_ratio() -> float:
    """Доля plan.max для gate ``PayForOrderOverMaxOffOnDeepOverspend`` (env, default 0.9)."""
    return float(settings.V3_PAY_FOR_ORDER_OFF_PLAN_HEADROOM_RATIO)


def gap_enable_plan_headroom_floor(max_pay: float) -> float:
    """Нижняя граница зоны skip enable: ``ratio × plan.max_pay_for_order``."""
    return gap_enable_plan_headroom_ratio() * float(max_pay)


def pfo_off_plan_headroom_floor(max_pay: float) -> float:
    """Нижняя граница зоны pfo_off: ``ratio × plan.max_pay_for_order``."""
    return pfo_off_plan_headroom_ratio() * float(max_pay)


def plan_max_stabilization_floor(max_pay: float) -> float:
    """Алиас ``pfo_off_plan_headroom_floor`` (tick-report, тесты)."""
    return pfo_off_plan_headroom_floor(max_pay)


def is_campaign_at_plan_headroom_plus_one(adv_state: AdvState) -> bool:
    """``True``, если fact в зоне pfo_off (``>= ratio × plan.max``)."""
    if adv_state.fact_pay_for_order is None:
        return False
    max_pay = float(adv_state.max_pay_for_order)
    if max_pay <= 0:
        return False
    return float(adv_state.fact_pay_for_order) >= pfo_off_plan_headroom_floor(max_pay)


def is_deep_overspend(adv_state: AdvState) -> bool:
    """Алиас ``is_campaign_at_plan_headroom_plus_one`` (имя фазы legacy)."""
    return is_campaign_at_plan_headroom_plus_one(adv_state)


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
