"""DTO строки дневной истории по одному ключевому запросу."""

from __future__ import annotations

from datetime import date as Date

from pydantic import BaseModel, Field


class KeywordDailyStat(BaseModel):
    """Дневная агрегированная статистика по одному norm_query.

    Модель хранит сырой набор метрик из ClickHouse, а производные коэффициенты
    вычисляет лениво через свойства, чтобы экран мог гибко решать, что именно
    показывать пользователю.
    """

    date: Date = Field(alias="date")
    views: int = Field(alias="views")
    clicks: int = Field(alias="clicks")
    add_to_cart: int = Field(alias="add_to_cart")
    orders: int = Field(alias="orders")
    spend: float = Field(alias="spend")
    cpm: float = Field(alias="cpm")
    avg_pos: float = Field(alias="avg_pos")

    model_config = {
        "populate_by_name": True,
        "extra": "ignore",
    }

    @property
    def ctr(self) -> float:
        """Возвращает CTR в долях единицы."""
        if self.views <= 0:
            return 0.0
        return self.clicks / self.views

    @property
    def conv_views_to_cart(self) -> float:
        """Возвращает конверсию показов в корзину."""
        if self.views <= 0:
            return 0.0
        return self.add_to_cart / self.views

    @property
    def conv_cart_to_order(self) -> float:
        """Возвращает конверсию корзины в заказ."""
        if self.add_to_cart <= 0:
            return 0.0
        return self.orders / self.add_to_cart

    @property
    def conv_views_to_order(self) -> float:
        """Возвращает конверсию показов в заказ."""
        if self.views <= 0:
            return 0.0
        return self.orders / self.views

    @property
    def pay_for_order(self) -> float:
        """Возвращает себестоимость заказа за день."""
        if self.orders <= 0:
            return 0.0
        return self.spend / self.orders
