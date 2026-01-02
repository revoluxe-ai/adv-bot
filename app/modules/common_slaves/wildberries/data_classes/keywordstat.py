from __future__ import annotations

import datetime

from pydantic import AliasChoices, BaseModel, ConfigDict, Field


class KeywordStat(BaseModel):
    model_config = ConfigDict(
        extra="ignore",  # новые поля от API не валят парсинг
        populate_by_name=True,  # принимать и по alias, и по имени поля
    )

    # Базовые поля, которые реально используются дальше по коду
    text: str = Field(validation_alias=AliasChoices("text", "keyword"))
    views: int
    clicks: int
    spend: float = Field(validation_alias=AliasChoices("spend", "sum"))
    adv_id: int
    update_timestamp: datetime.datetime
    date: datetime.date

    # Текущие поля, которые уже могут прилетать от WB (и раньше ломали модель)
    ctr: float | None = None
    cpc: float | None = None

    # Часто встречающиеся поля в статистике WB (пусть будут, но не обязательны)
    cpm: float | None = None
    atbs: int | None = None
    orders: int | None = None
    cr: float | None = None
    shks: int | None = None
    sum_price: float | None = None
