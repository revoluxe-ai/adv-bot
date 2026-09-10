"""Пропорциональный promo-множитель и runtime effective Plan/budget values.

Owner labels хранятся буквально. Базовый Plan из БД не мутируется: здесь
только runtime overlay ``base × M``, где ``M = 1 / (1 - f)``.
"""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal, ROUND_HALF_UP
from typing import Final

from app.modules.shop_runner.service_manager.old_modules.setting_auto_updater.data_classes import (
    PlanData,
)

PROMO_MAX_CPO_LABEL: Final[str] = "PromoMaxCPO"
PROMO_TARGET_CPO_LABEL: Final[str] = "PromoTargetCPO"
PROMO_AUTO_BUDGET_LABEL: Final[str] = "PromoAutoBudget"
PROPO_SEARCH_BUDGET_LABEL: Final[str] = "PropoSearchBudget"
PROMO_TARGET_BUDGET_LABEL: Final[str] = "PromoTarget Budget"

_ZERO = Decimal("0")
_ONE = Decimal("1")


def promo_fraction_from_amounts(*, promo_amount: int, total_amount: int) -> Decimal:
    """Фактическая доля promo в сумме. ``200/1000 → 0.2``."""
    if total_amount <= 0 or promo_amount <= 0:
        return _ZERO
    fraction = Decimal(promo_amount) / Decimal(total_amount)
    if fraction < _ZERO:
        return _ZERO
    if fraction >= _ONE:
        return Decimal("0.999999")
    return fraction


def promo_multiplier(fraction: Decimal) -> Decimal:
    """``M = 1 / (1 - f)``. ``0.5 → 2``, ``0.2 → 1.25``."""
    if fraction <= _ZERO:
        return _ONE
    if fraction >= _ONE:
        return _ONE
    return (_ONE / (_ONE - fraction)).quantize(Decimal("0.000001"))


def scale_int(value: int | None, multiplier: Decimal) -> int | None:
    """Округлить int-лимит/CPO half-up после умножения."""
    if value is None:
        return None
    scaled = (Decimal(value) * multiplier).quantize(Decimal("1"), rounding=ROUND_HALF_UP)
    return int(scaled)


def scale_number(value: int | float | None, multiplier: Decimal) -> float | None:
    """Округлить float CPO до 2 знаков, int — как ``scale_int``."""
    if value is None:
        return None
    if isinstance(value, bool):
        return None
    if isinstance(value, int) and not isinstance(value, bool):
        scaled_int = scale_int(value, multiplier)
        return None if scaled_int is None else float(scaled_int)
    scaled = (Decimal(str(value)) * multiplier).quantize(
        Decimal("0.01"), rounding=ROUND_HALF_UP
    )
    return float(scaled)


@dataclass(frozen=True, slots=True)
class EffectivePromoPlan:
    """Runtime overlay пяти Owner-сущностей плюс scaled PlanData.

    Attributes:
        active: True, если флаг включён и есть usable promo.
        fraction: фактическая доля f.
        multiplier: M.
        plan: scaled PlanData или None, если базового плана нет.
        PromoMaxCPO: scaled max CPO.
        PromoTargetCPO: scaled target CPO.
        PromoAutoBudget: scaled auto daily limit.
        PropoSearchBudget: scaled search daily limit (Owner spelling).
        promo_target_budget: scaled common/target budget (``PromoTarget Budget``).
    """

    active: bool
    fraction: Decimal
    multiplier: Decimal
    plan: PlanData | None
    PromoMaxCPO: int | None
    PromoTargetCPO: int | None
    PromoAutoBudget: int
    PropoSearchBudget: int
    promo_target_budget: int | None

    @property
    def PromoTarget_Budget(self) -> int | None:
        """Alias с пробелом в Owner-имени ``PromoTarget Budget``."""
        return self.promo_target_budget


def build_effective_promo_plan(
    *,
    flag_enabled: bool,
    fraction: Decimal,
    base_plan: PlanData | None,
    auto_budget_daily_limit: int,
    search_auto_budget_daily_limit: int,
    common_budget_daily_limit: int | None,
) -> EffectivePromoPlan:
    """Построить overlay. Без флага или при f=0 возвращает base × 1."""
    active = bool(flag_enabled) and fraction > _ZERO
    multiplier = promo_multiplier(fraction) if active else _ONE
    if not active:
        multiplier = _ONE
    scaled_plan: PlanData | None = None
    promo_max: int | None = None
    promo_target: int | None = None
    if base_plan is not None:
        try:
            promo_max = scale_int(int(base_plan.max_pay_for_order), multiplier)
            promo_target = scale_int(int(base_plan.target_pay_for_order), multiplier)
            scaled_plan = PlanData(
                orders=int(base_plan.orders),
                target_pay_for_order=int(promo_target or base_plan.target_pay_for_order),
                max_pay_for_order=int(promo_max or base_plan.max_pay_for_order),
            )
        except (TypeError, ValueError):
            scaled_plan = None
            promo_max = None
            promo_target = None
    return EffectivePromoPlan(
        active=active,
        fraction=fraction if active else _ZERO,
        multiplier=multiplier,
        plan=scaled_plan,
        PromoMaxCPO=promo_max if active else promo_max,
        PromoTargetCPO=promo_target if active else promo_target,
        PromoAutoBudget=int(
            scale_int(int(auto_budget_daily_limit or 0), multiplier) or 0
        ),
        PropoSearchBudget=int(
            scale_int(int(search_auto_budget_daily_limit or 0), multiplier) or 0
        ),
        promo_target_budget=(
            None
            if common_budget_daily_limit is None
            else scale_int(int(common_budget_daily_limit), multiplier)
        ),
    )
