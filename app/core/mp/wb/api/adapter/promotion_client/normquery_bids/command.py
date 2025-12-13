from __future__ import annotations

from pydantic import BaseModel, ConfigDict


class SetNormqueryBidsCommandItem(BaseModel):
    """Элемент запроса установки ставки по поисковому кластеру."""

    advert_id: int
    nm_id: int
    norm_query: str
    bid: int

    model_config = ConfigDict(arbitrary_types_allowed=True)


class SetNormqueryBidsCommand(BaseModel):
    """Команда на установку ставок по нормирующим запросам."""

    bids: list[SetNormqueryBidsCommandItem]

    model_config = ConfigDict(arbitrary_types_allowed=True)
