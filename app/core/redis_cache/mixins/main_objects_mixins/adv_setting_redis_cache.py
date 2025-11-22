from abc import ABC

from app.modules.common_slaves.wildberries.models import AdvSetting

from ..mixins_protocol import RedisCacheMixinsProtocol


class AdvSettingRedisCache(ABC, RedisCacheMixinsProtocol):
    def __init__(self, adv: AdvSetting) -> None:
        self.__unique_id: str = str(adv.adv_id)

    @property
    def _unique_id(self) -> str:
        return self.__unique_id
