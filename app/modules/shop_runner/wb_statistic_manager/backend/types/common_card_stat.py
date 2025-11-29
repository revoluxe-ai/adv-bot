import datetime

class CommonCardStat:
    def __init__(
        self,
        nmid: int,
        open_card: int,
        add_to_cart: int,
        orders: int,
        orders_sum: int,
        buy_outs: int,
    ) -> None:
        self.nmid = nmid
        self.open_card = open_card
        self.add_to_cart = add_to_cart
        self.orders = orders
        self.orders_sum = orders_sum
        self.buy_outs = buy_outs
        self._date = None

    @property
    def date(self) -> datetime.datetime:
        return self._date

    @date.setter
    def date(self, value: datetime.date) -> None:
        assert isinstance(value, datetime.date)
        self._date = value
