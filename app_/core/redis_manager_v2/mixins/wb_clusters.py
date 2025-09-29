import logging
import typing
from urllib.parse import quote

from ..base_redis_manager_protocol import BaseRedisManagerProtocol

logger = logging.getLogger(__name__)


class WBClustersMixin:
    _prefix = "cluster_and_preset:"

    def get_key(self: BaseRedisManagerProtocol, text: str) -> str:
        return self._prefix + quote(text)

    async def set_cluster_and_preset(
        self: BaseRedisManagerProtocol, text, cluster: str, preset: typing.Optional[int]
    ):
        key = self._get_key(text)
        if cluster is None or preset is None:
            await self._client.delete(key)
        else:
            value = cluster + ":" + str(preset)
            await self._client.set(key, value)
            text = cluster
            key = self._get_key(text)
            await self._client.set(key, value)
        return None

    async def get_cluster_and_preset(
        self: BaseRedisManagerProtocol, text: str
    ) -> tuple[str | None, str | None]:
        key = self._get_key(text)
        result: bytes | None = await self._client.get(key)
        if result is None:
            return None, None
        value = result.decode("utf-8")
        data = value.split(":")
        try:
            cluster, preset = data
        except ValueError:
            logger.error("Ошибка распаковки данных о кластере и пресете")
            return None, None
        return cluster, preset
