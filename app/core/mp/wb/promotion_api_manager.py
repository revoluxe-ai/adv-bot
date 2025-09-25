from dependency_injector.wiring import inject, Provide

from app.core.mp.wb.adapters.promotion_v1_adapter import PromotionV1Adapter
from app.core.mp.wb.universal_client_factory import UniversalClientFactory


class PromotionApiManager:
    """
    Менеджер для работы с разделом promotion WB API.
    Инкапсулирует фабрику клиентов и адаптер.
    """

    def __init__(self, promotion_adapter: PromotionV1Adapter):
        self._promotion_adapter = promotion_adapter

    @property
    def promotion_adapter(self) -> PromotionV1Adapter:
        return self._promotion_adapter

    @inject
    async def get_client(
            self,
            shop_id: str,
            client_factory: UniversalClientFactory = Provide["promotion_client_factory"],
    ):
        """
        Получить клиента для магазина через UniversalClientFactory (через DI).
        """
        return await client_factory.get_client(shop_id)
