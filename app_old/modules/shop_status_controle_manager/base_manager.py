from abc import ABC

from .redis_manager import SuccessHandler, ErrorHandler


class BaseManager(ABC):
    def __init__(self, shop_id: str):
        self.__unique_id = shop_id
        self.__shop_id = shop_id
        self.success_handler = SuccessHandler(shop_id)
        self.error_handler = ErrorHandler(shop_id)

    @property
    def shop_id(self) -> str:
        return self.__shop_id
