"""SSOT tier ключа V3: FULL / PFO / NO DATA по ``CalculatedKeyword.pay_for_order`` и CH+conv."""

from __future__ import annotations

from enum import Enum

from app.modules.common_slaves.wildberries.models.enums import KeywordStrategyMode
from app.modules.wb_adv_updater.calculated_keywords_manager.dto.calculated_keyword import (
    CalculatedKeyword,
)
from app.modules.wb_adv_updater.calculated_keywords_manager.dto.position_profile_point import (
    PositionProfilePoint,
)


class KeywordV3DataTier(str, Enum):
    """Операционный tier ключа V3.

    FULL означает, что у ключа уже есть CH-профиль и дальнейшие ladder-решения
    должны опираться на него. PFO означает отсутствие профиля при наличии
    operational ``pay_for_order``: такие ключи живут в NF-потоке, но могут
    участвовать в plan-fact регулировке. GAP означает отсутствие и профиля, и
    operational ``pay_for_order``: это отдельная зона bootstrap/enable без
    NF-миграции.
    """

    FULL = "full"
    PFO = "pfo"
    GAP = "gap"


def resolve_keyword_v3_data_tier(
    *,
    position_profile: list[PositionProfilePoint] | None,
    keyword: CalculatedKeyword,
) -> KeywordV3DataTier:
    """Определить операционный tier ключа.

    Классификация нужна как SSOT для NF-веток и bootstrap-веток:
    - ``FULL``: есть непустой CH-профиль, значит ключ должен жить по ladder;
    - ``PFO``: профиля нет, но есть положительный operational ``pay_for_order``;
      это активный NO-CH/NF-кейс, где допустимы migrate и plan-fact шаги;
    - ``GAP``: профиля нет и ``pay_for_order`` не задан или невалиден, значит
      ключ попадает в enable/bootstrap-контур, а не в NF-регулятор.
    """
    if bool(position_profile):
        return KeywordV3DataTier.FULL
    if keyword_pfo_value(keyword) is not None:
        return KeywordV3DataTier.PFO
    return KeywordV3DataTier.GAP


def is_keyword_no_data(keyword: CalculatedKeyword) -> bool:
    """``True``, если на ключе нет операционного ``pay_for_order`` (NO DATA tier)."""
    pfo = keyword.pay_for_order
    return pfo is None or float(pfo) <= 0


def keyword_pfo_value(keyword: CalculatedKeyword) -> float | None:
    """Положительный ``keyword.pay_for_order`` или ``None``."""
    pfo = keyword.pay_for_order
    if pfo is None:
        return None
    value = float(pfo)
    if value <= 0:
        return None
    return value


def is_pay_for_order_gap(
    keyword: CalculatedKeyword,
    *,
    strategy_mode: KeywordStrategyMode | None = None,
) -> bool:
    """NO DATA + OFF: кандидат на enable (фаза ``plan_pay_for_order_gap_enable``)."""
    mode = strategy_mode if strategy_mode is not None else keyword.strategy_mode
    return mode == KeywordStrategyMode.OFF and is_keyword_no_data(keyword)
