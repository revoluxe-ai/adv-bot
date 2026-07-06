"""SSOT tier ключа V3.

Модуль вводит единую операционную классификацию ключа, чтобы разные части
updater-а не принимали собственные решения на основе косвенных признаков вроде
``position_profile is None`` или ``target_place == 0``. Это особенно важно для
NF-контуров: после рефакторинга они больше не должны интерпретировать
отсутствие CH-профиля как «можно сбросить всё в 0», а должны различать bootstrap
активного no-CH ключа и полностью пустой GAP-зоны.

Семантика tier-ов:

- ``GAP`` — на ключе нет operational ``pay_for_order``. Даже если CH-профиль уже
  есть, такой ключ не готов к ladder/NF-контрам и должен идти через отдельный
  GAP enable/reset.
- ``FULL`` — у ключа есть CH-профиль и operational ``pay_for_order``. Такой ключ
  живёт в ladder-контуре: здесь работают raise, skip_up, rebalancing,
  calibration и все операции, которые опираются на CPO ступеней из профиля.
- ``PFO`` — CH-профиля нет, но есть operational ``pay_for_order``. Это активный
  no-CH ключ: он должен пройти NF validate, затем получить bootstrap
  ``target_place`` от текущей WB-позиции, а после этого регулироваться только
  plan-fact шагом ``±1``.

Эта классификация нужна как SSOT для:

- NF validate / migrate / plan-fact;
- ladder-веток, которые должны работать только по ``FULL``;
- sync-слоя, где no-CH ключи нельзя заново инициализировать через fallback;
- отчётности и документации, чтобы различать bootstrap PFO/GAP и ladder FULL.
"""

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

    Атрибут ``data_tier`` у ``KeywordDTO`` и этот enum — это один и тот же
    продуктовый контракт: FULL / PFO / GAP описывают не режим ключа, а его
    операционную готовность к разным веткам updater-а.

    ``FULL``:
        Есть CH-профиль и operational ``pay_for_order``. Такие ключи должны
        продолжать путь по ladder-профилю, а NF-фазы для них не выполняют
        bootstrap или plan-fact коррекцию.

    ``PFO``:
        CH-профиля нет, но есть operational ``pay_for_order``. Это активный
        no-CH ключ, для которого допустим NF-контур: validate переводит ключ в
        ``MIN_CPA``, migrate инициализирует стартовый ``target_place``, а
        plan-fact поддерживает его далее.

    ``GAP``:
        Нет operational ``pay_for_order``. CH-профиль сам по себе не делает ключ
        FULL, потому что без PFO он остаётся в GAP enable/reset зоне.
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

    Возвращаемое значение используется как SSOT для всего NF/ladder контуров:

    - если operational ``pay_for_order`` отсутствует или неположительный, ключ
      считается ``GAP`` независимо от CH-профиля;
    - если есть непустой CH-профиль и PFO, ключ считается ``FULL`` и дальше
      должен жить в ladder-ветке;
    - если профиля нет, но operational ``pay_for_order`` положительный, ключ
      относится к ``PFO`` и может проходить NF validate → migrate → plan-fact;

    Здесь намеренно не пытаемся интерпретировать ``OFF``/``MIN_CPA``/прочие
    режимы: функция классифицирует только наличие данных, а не текущий режим.
    """
    if keyword_pfo_value(keyword) is not None:
        if bool(position_profile):
            return KeywordV3DataTier.FULL
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
