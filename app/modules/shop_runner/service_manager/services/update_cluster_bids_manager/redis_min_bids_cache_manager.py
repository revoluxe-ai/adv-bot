import json
from typing import TYPE_CHECKING

from app.core.mp.wb.dto.adv_placement_type import AdvPlacementType
from app.core.redis_manager_v2.base_protocol import BaseRedisManagerProtocol
from app.core.redis_manager_v2.base_redis_manager import BaseRedisManager

if TYPE_CHECKING:
    pass

MIN_BIDS_V2_DEFAULT_TTL_SEC = 12 * 60 * 60


class MinBidsAdvPlacementCacheMixin:
    """Кеш минимальной ставки по тройке (adv_id WB, тип размещения, nmid). TTL по умолчанию 12 ч."""

    @staticmethod
    def min_bids_v2_key(adv_id: int, placement: AdvPlacementType, nmid: int) -> str:
        return (
            f"min_bids:v2:adv:{adv_id}:pt:{placement.value}:nmid:{nmid}"
        )

    async def get_min_bid_for_adv_placement_nmid(
        self: "BaseRedisManagerProtocol",
        adv_id: int,
        placement: AdvPlacementType,
        nmid: int,
    ) -> int | None:
        key = MinBidsAdvPlacementCacheMixin.min_bids_v2_key(adv_id, placement, nmid)
        result = await self._client.get(key)  # pyright: ignore
        if not result:
            return None
        data = json.loads(result)
        return int(data["cpm"])

    async def set_min_bid_for_adv_placement_nmid(
        self: "BaseRedisManagerProtocol",
        adv_id: int,
        placement: AdvPlacementType,
        nmid: int,
        cpm: int,
        ttl: int | None = None,
    ) -> None:
        key = MinBidsAdvPlacementCacheMixin.min_bids_v2_key(adv_id, placement, nmid)
        effective = (
            ttl
            if ttl is not None
            else MIN_BIDS_V2_DEFAULT_TTL_SEC
        )
        await self._client.set(  # pyright: ignore
            key,
            json.dumps({"cpm": cpm}),
            ex=effective,
        )


class MinBidsCacheMixin:
    """Mixin для кэширования минимальных ставок по nmid."""

    prefix = "min_bids:nmid"
    default_ttl = 60 * 60  # 1 час

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


class MinBidsCacheManager(
    MinBidsAdvPlacementCacheMixin,
    MinBidsCacheMixin,
    BaseRedisManager,
    BaseRedisManagerProtocol,
):
    """Менеджер для кэширования ставок по nmid (legacy) и по adv+placement+nmid (v2)."""

    pass











