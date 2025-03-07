import datetime


class CommonCardStat:
    def __init__(self, nmid, open_card, add_to_cart, orders, orders_sum, buy_outs):
        self.nmid = nmid
        self.open_card = open_card
        self.add_to_cart = add_to_cart
        self.orders = orders
        self.orders_sum = orders_sum
        self.buy_outs = buy_outs
