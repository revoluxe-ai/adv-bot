import json
from typing import TYPE_CHECKING

from app.core.redis_manager_v2.base_protocol import BaseRedisManagerProtocol
from app.core.redis_manager_v2.base_redis_manager import BaseRedisManager

if TYPE_CHECKING:
    pass


class MinBidsCacheMixin:
    """Mixin для кэширования минимальных ставок по nmid."""

    prefix = "min_bids:nmid"
    default_ttl = 300  # 5 минут

    def _get_key(self: "BaseRedisManagerProtocol", nmid: int) -> str:
        """Генерирует ключ для nmid."""
        return f"{self.prefix}:{nmid}"

    async def set_min_bid_for_nmid(
        self: "BaseRedisManagerProtocol",
        nmid: int,
        auto_cpm: int,
        search_cpm: int,
        ttl: int | None = None,
    ) -> None:
        """Сохраняет минимальные ставки для nmid."""
        key = self._get_key(nmid)  # pyright: ignore
        effective_ttl = self._resolve_ttl(ttl) # pyright: ignore
        data = {"auto": auto_cpm, "search": search_cpm}
        await self._client.set(key, json.dumps(data), ex=effective_ttl)  # pyright: ignore

    async def get_min_bid_for_nmid(
        self: "BaseRedisManagerProtocol",
        nmid: int,
    ) -> tuple[int, int] | None:
        """Получает минимальные ставки для nmid."""
        key = self._get_key(nmid)  # pyright: ignore
        result = await self._client.get(key) # pyright: ignore
        if not result:
            return None
        data = json.loads(result)
        return data["auto"], data["search"]

    async def get_min_bids_for_nmids(
        self: "BaseRedisManagerProtocol",
        nmids: list[int],
    ) -> dict[int, tuple[int, int]]:
        """Возвращает cached ставки для переданных nmids."""
        result: dict[int, tuple[int, int]] = {}
        for nmid in nmids:
            # TODO: Исправить косяк с архитектурой, сделал ИИ через одно место
            cached = await self.get_min_bid_for_nmid(nmid)  # type: ignore [attr-defined]
            if cached:
                result[nmid] = cached
        return result


class MinBidsCacheManager(MinBidsCacheMixin, BaseRedisManager, BaseRedisManagerProtocol):
    """Менеджер для кэширования ставок по nmid."""

    pass











