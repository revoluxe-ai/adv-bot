from typing import Optional


class CardsNotFoundForShopError(Exception):
    pass


class ComplexAdvsExistsError(Exception):
    def __init__(self, message, auto_adv_id, search_adv_id):
        self.auto_adv_id = auto_adv_id
        self.search_adv_id = search_adv_id
        super().__init__(message)


class NotEnoughBalanceOnShopError(Exception):
    pass


class StartComplexAdvError(Exception):
    auto_adv_id: int
    search_adv_id: int