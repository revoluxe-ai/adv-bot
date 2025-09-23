class StartAdvError(Exception):
    pass


class CardNotFoundInWB(Exception):
    pass


class InvalidAdvId(Exception):
    pass


class UnknownApiRequestError(Exception):
    pass


class NotCanDeleteAllProductsError(Exception):
    pass


class ItemCategoryNotInStockError(Exception):
    pass


class NotChangeError(Exception):
    pass


class AdvNotFoundInWBError(Exception):

    def __init__(
        self, adv_id: int | None = None, search_adv_id: int | None = None
    ) -> None:
        m = "Рекламная кампания не найдена в Wildberries"
        super().__init__(f"{m} adv_id: {adv_id}, search_adv_id: {search_adv_id}")
        self.message = m
        self.auto_adv_id = adv_id
        self.search_adv_id = search_adv_id


class NotFoundSearchAdvError(Exception):
    pass


class CpmNotFoundError(Exception):
    pass
