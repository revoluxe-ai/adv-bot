from app.core.mp.wb.base_adapters.base_adapter import WBBaseAdapters


class BaseWBApiManager(WBBaseAdapters):
    """
    Базовый менеджер для работы с WB API.
    Содержит логику получения клиентов и адаптеров для различных разделов через фабрики.
    """

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Здесь можно добавить инициализацию других клиентов/адаптеров при необходимости

    async def get_promotion_client(self, shop_id: str):
        """
        Получить клиента для раздела promotion через UniversalClientFactory.
        """
        return await self.promotion_adapter.client_factory.get_client(shop_id)

    # Аналогично можно добавить методы для других разделов (bidder, reports и т.д.)
