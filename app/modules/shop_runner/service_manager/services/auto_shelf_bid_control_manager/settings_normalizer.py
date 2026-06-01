"""Нормализация legacy-настроек auto_shelf (рубли ошибочно записаны как bid_minor).

До унификации UI max/шаг иногда сохранялись как «500» (= 5 ₽), а не 50000 коп.
При min WB 120 ₽ (12000 коп) это давало ``invalid_bid_range`` и test=310 коп.
"""

from __future__ import annotations

from dataclasses import dataclass

from app.modules.common_slaves.wildberries.models.auto_shelf_bid_control import (
    AutoShelfBidControlSettings,
    AutoShelfBidControlState,
)

from .bid_units import DEFAULT_MAX_BID_MINOR, rubles_to_bid_minor


@dataclass(frozen=True, slots=True)
class SettingsRepairResult:
    """Результат нормализации settings."""

    max_bid_minor: int
    min_bid_distance_minor: int
    changed: bool


def repair_max_bid_minor(
    max_bid_minor: int,
    *,
    min_bid_minor: int,
    actual_bid_minor: int | None,
    default_max_bid_minor: int = DEFAULT_MAX_BID_MINOR,
) -> int:
    """Привести max к копейкам и сделать ``max >= min``."""
    fixed = int(max_bid_minor)
    if fixed < min_bid_minor:
        as_kopecks = rubles_to_bid_minor(fixed)
        if as_kopecks >= min_bid_minor:
            fixed = as_kopecks
        else:
            candidates = [min_bid_minor, default_max_bid_minor]
            if actual_bid_minor is not None:
                candidates.append(int(actual_bid_minor))
            fixed = max(candidates)
    return fixed


def repair_min_bid_distance_minor(
    min_bid_distance_minor: int,
    *,
    min_bid_minor: int,
) -> int:
    """Шаг: legacy ``1`` трактуем как 1 ₽ → 100 коп; иначе не ниже 1 ₽."""
    fixed = int(min_bid_distance_minor)
    if fixed < min_bid_minor and fixed < rubles_to_bid_minor(1):
        fixed = rubles_to_bid_minor(fixed)
    if fixed < rubles_to_bid_minor(1):
        fixed = rubles_to_bid_minor(1)
    return fixed


def compute_settings_repair(
    settings: AutoShelfBidControlSettings,
    *,
    min_bid_minor: int,
    actual_bid_minor: int | None,
) -> SettingsRepairResult:
    """Вычислить нормализованные max и min_distance без записи в БД."""
    new_max = repair_max_bid_minor(
        int(settings.max_bid_minor),
        min_bid_minor=min_bid_minor,
        actual_bid_minor=actual_bid_minor,
    )
    new_dist = repair_min_bid_distance_minor(
        int(settings.min_bid_distance_minor),
        min_bid_minor=min_bid_minor,
    )
    changed = new_max != int(settings.max_bid_minor) or new_dist != int(
        settings.min_bid_distance_minor
    )
    return SettingsRepairResult(
        max_bid_minor=new_max,
        min_bid_distance_minor=new_dist,
        changed=changed,
    )


def repair_state_test_bid_minor(
    state: AutoShelfBidControlState,
    *,
    min_bid_minor: int,
    max_bid_minor: int,
    actual_bid_minor: int | None,
) -> bool:
    """Выровнять test-ставку в допустимом диапазоне; True если меняли state."""
    test = state.current_test_bid_minor
    if test is None:
        return False
    if min_bid_minor <= int(test) <= max_bid_minor:
        return False
    if (
        actual_bid_minor is not None
        and min_bid_minor <= int(actual_bid_minor) <= max_bid_minor
    ):
        state.current_test_bid_minor = int(actual_bid_minor)
    else:
        state.current_test_bid_minor = int(round((min_bid_minor + max_bid_minor) / 2))
    state.last_reason = "settings_units_repaired"
    return True
