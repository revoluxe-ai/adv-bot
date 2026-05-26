"""Почему стратегии автоапдейтера различаются при organic и при полках (V2, V3).

Единственный источник смысла — ниже. Не дополнять операционными правилами
(что отключать, какие поля, очереди UP) в этом модуле.

Цель
----
Повысить общую конверсию карточки.

Почему сравниваем organic и shelf
---------------------------------
Это не «у кого больше кликов». По соотношению organic/shelf за день понимаем,
**что сильнее влияет на конверсию карточки** — и от этого **разная логика** отбора
и усиления ключей.

Когда влияние полок сильнее (shelf >= organic)
----------------------------------------------
Основное влияние на конверсию карточки дают **полки**.

Чтобы поднять общую конверсию карточки, имеет смысл включать только те ключи,
у которых конверсия **выше, чем у полок**. Иначе мы ослабляем тот канал,
который сейчас тянет карточку.

Когда влияние органики сильнее (organic > shelf)
------------------------------------------------
Сильнее влияет **органика**.

Здесь исходим из того, что **любой ключ с рекламой** по конверсии **лучше**,
чем ключ **без рекламы** (органический показ без ставки). Сравнение с полками
как обязательный порог для «можно ли усиливать ключ» **не отражает** эту
ситуацию — поэтому логика **другая**, не как при доминировании полок.

Итог: почему стратегии должны отличаться
---------------------------------------
Один и тот же критерий «ключ должен быть лучше полок» применим только когда
полки — главный драйвер конверсии карточки. Когда доминирует органика, барьер
«лучше полок» для решения «усиливать ключ или нет» **не тот**; нужна отдельная
стратегия, исходя из преимущества рекламного ключа над нерекламным органическим.
"""

from __future__ import annotations

from enum import Enum

from app.modules.shop_runner.service_manager.wb_shop_data_manager.dto.complex_adv import (
    TrafficClicksDTO,
)


class ShelfTrafficInfluenceMode(str, Enum):
    """Что сильнее влияет на конверсию карточки (суррогат по кликам за сутки)."""

    SHELF_DOMINANT = "SHELF_DOMINANT"
    ORGANIC_DOMINANT = "ORGANIC_DOMINANT"
    UNKNOWN = "UNKNOWN"


def resolve_shelf_traffic_influence_mode(
    traffic_clicks_dto: TrafficClicksDTO | None,
) -> ShelfTrafficInfluenceMode:
    if traffic_clicks_dto is None:
        return ShelfTrafficInfluenceMode.UNKNOWN
    if traffic_clicks_dto.organic_clicks > traffic_clicks_dto.shelf_clicks:
        return ShelfTrafficInfluenceMode.ORGANIC_DOMINANT
    return ShelfTrafficInfluenceMode.SHELF_DOMINANT


def shelf_conversion_filter_applies(mode: ShelfTrafficInfluenceMode) -> bool:
    """См. module docstring: барьер «лучше полок» только при SHELF_DOMINANT."""
    return mode == ShelfTrafficInfluenceMode.SHELF_DOMINANT


def keyword_passes_shelf_conversion_gate(
    above_rec_conversion: bool | None,
    *,
    mode: ShelfTrafficInfluenceMode,
) -> bool:
    """См. module docstring."""
    if not shelf_conversion_filter_applies(mode):
        return True
    return above_rec_conversion is True
