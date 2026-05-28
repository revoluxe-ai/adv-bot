"""Отображение ``SalesStates`` в UI и логах (буква, название, цель)."""

from __future__ import annotations

from dataclasses import dataclass

from app.modules.shop_runner.service_manager.old_modules.setting_auto_updater_v2.adv_control_system.sales_state.sales_states import (
    SalesStates,
)


@dataclass(frozen=True, slots=True)
class SalesStateMeta:
    """Метаданные состояния кампании для Telegram и документации."""

    letter: str
    title_ru: str
    goal_ru: str


SALES_STATE_META: dict[SalesStates, SalesStateMeta] = {
    SalesStates.OVERSPEND: SalesStateMeta(
        letter="П",
        title_ru="Перерасход",
        goal_ru="снизить расход",
    ),
    SalesStates.UNDERPERFORM: SalesStateMeta(
        letter="Нд",
        title_ru="Недопродажи",
        goal_ru="нарастить продажи",
    ),
    SalesStates.STABLE: SalesStateMeta(
        letter="С",
        title_ru="Стабильно",
        goal_ru="снизить себестоимость",
    ),
    SalesStates.OPTIMAL: SalesStateMeta(
        letter="О",
        title_ru="Оптимально",
        goal_ru="удерживать результат",
    ),
    SalesStates.NO_DATA: SalesStateMeta(
        letter="Н",
        title_ru="Нет данных",
        goal_ru="мин. ставка WB, MIN_CPA по ключам без V2 CPO",
    ),
}


def sales_state_meta(state: SalesStates) -> SalesStateMeta:
    """Метаданные состояния; для неизвестного enum — fallback по имени."""
    return SALES_STATE_META.get(
        state,
        SalesStateMeta(letter="?", title_ru=state.name, goal_ru=""),
    )


def sales_state_short_label(state: SalesStates) -> str:
    """Краткая подпись для меню РК: ``Н (Нет данных)``."""
    meta = sales_state_meta(state)
    return f"{meta.letter} ({meta.title_ru})"


def format_keyword_list_target_place_suffix(target_place: int | None) -> str:
    """Суффикс целевой позиции в списке ключей.

    - ``None`` — нет индивидуальной цели (OFF / не задано): ``->Н>``.
    - ``0`` — мин. ставка WB (V3 NO_DATA): ``->0``.
    - ``>0`` — позиция из CH: ``->N``.
    """
    if target_place is None:
        return "->Н>"
    return f"->{target_place}"
