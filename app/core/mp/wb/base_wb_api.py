from .adapter_factory import AdapterFactory


class BaseWBApi:
    def __init__(self, shop_id: str):
        self.shop_id = shop_id
        self.adapter_factory = AdapterFactory()
