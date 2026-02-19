from dataclasses import dataclass
from datetime import datetime


@dataclass
class BidPosition:
    keyword: str
    position: int
    bid: int  # стоимость 1000 показов
    timestamp: datetime
    _conv_carts_to_views: float | None = None

    @property
    def conv_carts_to_views(self) -> float | None:
        return self._conv_carts_to_views

    @conv_carts_to_views.setter
    def conv_carts_to_views(self, value):
        self._conv_carts_to_views = value  # сколько получаем корзин из 1 показа

    @property
    def pay_for_cart(self) -> float:
        conv = self.conv_carts_to_views
        if conv is None or conv <= 0:
            return float("inf")
        views_for_cart = 1 / conv
        pay_for_cart = views_for_cart * self.bid / 1000
        return pay_for_cart
