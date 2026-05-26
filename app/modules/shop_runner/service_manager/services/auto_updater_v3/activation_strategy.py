"""Стратегии активации ключей V3: поштучная и послойная.

Поштучная («по одному ключу»): за цикл одно UP/DOWN на одном выбранном ключе.
Послойная («по уровню для всех»): за цикл одно UP, но приоритет слоя OFF→MIN → MIN→OPT → OPT→MAX.

Не путать с ``AdvSetting.strategy`` (MIN_CPO/MAX_CONV в ``change_adv_strategy``).
"""

from __future__ import annotations

from enum import Enum

from app.modules.shop_runner.service_manager.wb_shop_data_manager.dto.complex_adv import (
    ComplexAdv,
    TrafficClicksDTO,
)


class ActivationStrategy(str, Enum):
    """Как выбирается ключ(и) для UP/DOWN в V3."""

    PIECEWISE = "PIECEWISE"  # поштучная — по одному ключу
    LAYERED = "LAYERED"  # послойная — по уровню для всех


class ShelfClickMode(str, Enum):
    """Сравнение organic/shelf кликов за сегодня (полочная фаза)."""

    ORGANIC_DOMINANT = "ORGANIC_DOMINANT"  # organic > shelf
    SHELF_DOMINANT_OR_EQUAL = "SHELF_DOMINANT_OR_EQUAL"  # shelf >= organic
    UNKNOWN = "UNKNOWN"  # DTO нет — трактуем как shelf >= organic


def resolve_shelf_click_mode(
    traffic_clicks_dto: TrafficClicksDTO | None,
) -> ShelfClickMode:
    """Режим кликов для полочной фазы V3."""
    if traffic_clicks_dto is None:
        return ShelfClickMode.UNKNOWN
    if traffic_clicks_dto.organic_clicks > traffic_clicks_dto.shelf_clicks:
        return ShelfClickMode.ORGANIC_DOMINANT
    return ShelfClickMode.SHELF_DOMINANT_OR_EQUAL


def resolve_shelf_click_mode_from_adv(complex_adv: ComplexAdv) -> ShelfClickMode:
    return resolve_shelf_click_mode(complex_adv.traffic_clicks_dto)


def activation_strategy_for_shelf_underperform(
    click_mode: ShelfClickMode,
) -> ActivationStrategy:
    """Маппинг click-mode → стратегия активации при UNDERPERFORM в полочной фазе."""
    if click_mode == ShelfClickMode.ORGANIC_DOMINANT:
        return ActivationStrategy.LAYERED
    return ActivationStrategy.PIECEWISE
