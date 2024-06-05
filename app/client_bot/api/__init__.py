from new.wildberries.api import WBApi
from new.wildberries.data_classes.wb_shop import WbShop
from session_maker import get_async_session_maker

sm = get_async_session_maker


class AdvManager:

    def __init__(self, shop: WbShop):
        self.__wb_api = WBApi()
