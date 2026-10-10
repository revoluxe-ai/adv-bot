"""Короткие callback-data экрана рекламного контроля (лимит 64 байта)."""

from aiogram.filters.callback_data import CallbackData


class AdcShop(CallbackData, prefix="adc_sh"):
    """Открыть обзор магазина."""

    cab: int


class AdcCampPage(CallbackData, prefix="adc_cp"):
    """Страница списка кампаний (1-based offset)."""

    cab: int
    pg: int


class AdcCamp(CallbackData, prefix="adc_c"):
    """Карточка кампании. ``aid`` — advert_id. ``pg`` — страница списка."""

    cab: int
    aid: int
    pg: int


class AdcFeat(CallbackData, prefix="adc_f"):
    """Одна feature кампании. ``f`` — короткий код registry."""

    cab: int
    aid: int
    f: str
    pg: int


class AdcPrev(CallbackData, prefix="adc_p"):
    """Старт dry-run. ``op``: dis | clr | ovr."""

    cab: int
    aid: int
    f: str
    op: str
    pg: int
