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
    auto_adv_id: int | None = None
    search_adv_id: int | None = None
