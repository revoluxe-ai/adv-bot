class CardsNotFoundForShopError(Exception):
    pass


class ComplexAdvsExistsError(Exception):
    def __init__(self, message, auto_adv_id, search_adv_id):
        self.auto_adv_id = auto_adv_id
        self.search_adv_id = search_adv_id
        super().__init__(message)


class NotEnoughBalanceOnShopError(Exception):
    adv_id: int | None = None


class StartComplexAdvError(Exception):
    auto_adv_id: int
    search_adv_id: int


class AdvExistsForNmidError(Exception):
    def __init__(self, exist_adv_ids_rows: list[tuple[int, int | None]]):
        message = "Существующие рекламные кампании найдены для данного артикула."
        super().__init__(message)
        self.exist_adv_ids_rows = exist_adv_ids_rows  # Список кортежей (auto_id, search_id | None)