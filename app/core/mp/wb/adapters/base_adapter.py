from app.core.mp.wb.adapters.promotion_v1_adapter import PromotionV1Adapter


class WBBaseAdapters:
    """
    Базовый класс для доступа к адаптерам WB API.
    Все адаптеры подключаются как свойства.
    """

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._promotion_adapter = None

    @property
    def promotion_adapter(self) -> PromotionV1Adapter:
        if self._promotion_adapter is None:
            self._promotion_adapter = PromotionV1Adapter()
        return self._promotion_adapter
