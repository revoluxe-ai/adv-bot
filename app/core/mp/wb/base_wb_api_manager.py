from .wb_api_adapter_factory import WbApiAdapterFactory


class BaseWBApiManager:
    """
    Базовый менеджер для работы с WB API.
    Содержит логику получения клиентов и адаптеров для различных разделов через фабрики.
    """

    adapter_factory = WbApiAdapterFactory()

    def __init__(self, shop_id) -> None:
        self._shop_id = shop_id
