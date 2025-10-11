from abc import ABC

from ..mixins_protocol import RedisCacheMixinsProtocol


class WBShopRedisCache(ABC, RedisCacheMixinsProtocol):
    def __init__(self, shop_id: str) -> None:
        self.__unique_id: str = shop_id

    @property
    def _unique_id(self) -> str:
        unique_id = self.__unique_id
        return unique_id
