"""Установка целевой ставки полок Auto-кампании (с dry-run защитой)."""

from __future__ import annotations

import logging
from typing import Protocol

from app.core.mp.wb.api.managers.wb_promotion_manager.wb_promotion_manager import WBModifier
from app.modules.shop_runner.service_manager.services.auto_shelf_bid_increment_manager.redis_auto_recommendations_bid_value_manager import (
    RedisAutoRecommendationsBidValueManager,
)
from app.modules.shop_runner.service_manager.wb_shop_data_manager.dto.complex_adv import (
    ComplexAdv,
)
from app.settings import settings

logger = logging.getLogger(__name__)


class AutoShelfBidControlWriteBlockedError(PermissionError):
    """Raised when shelf bid write is attempted for read-only campaigns."""


class _AutoShelfBidPatchPort(Protocol):
    """Порт PATCH ставки полок (копейки)."""

    async def patch_auto_adv_bids_kopecks(
        self, adv_id: int, nm_bid_kopecks: dict[int, int]
    ) -> None: ...


class _BidCachePort(Protocol):
    """Порт записи фактической ставки в Redis после PATCH."""

    async def set_bids(
        self,
        auto_adv_id: int,
        bids: dict[int, int],
    ) -> None: ...


class AutoShelfBidSetter:
    """Сервис установки ставки полок для одного nmid через PATCH /api/advert/v1/bids.

    ``bid_minor`` (копейки) передаётся в WB как ``bid_kopecks`` без умножения на 100.
    Legacy ``adv/v0/bids`` (WBApi.update_cpm) снят с WB — 404 path not found.
    """

    def __init__(
        self,
        wb_modifier: WBModifier | _AutoShelfBidPatchPort,
        bid_cache_manager: RedisAutoRecommendationsBidValueManager | _BidCachePort | None = None,
    ) -> None:
        self._wb_modifier = wb_modifier
        self._bid_cache_manager = bid_cache_manager

    @staticmethod
    def to_api_bid(bid_minor: int) -> int:
        """Внутренний ``bid_minor`` = ``bid_kopecks`` для v1 API."""
        return int(bid_minor)

    async def set_bid(
        self,
        complex_adv: ComplexAdv,
        bid_minor: int,
        currency: str,
    ) -> None:
        """Установить ставку полок для Auto-РК.

        В dry-run режиме реальные PATCH-запросы не выполняются.
        Источник dry-run — только глобальная настройка приложения.
        После успешного PATCH при переданном ``bid_cache_manager`` обновляет
        Redis (источник actual bid для control/UI).
        """
        nmids = complex_adv.nmids
        if len(nmids) != 1:
            raise ValueError("AutoShelfBidSetter supports only single-nmid campaigns")
        if not complex_adv.bot_active:
            raise AutoShelfBidControlWriteBlockedError(
                "Auto shelf bid write requires bot_active=True"
            )
        if not bool(getattr(complex_adv, "auto_shelf_bid_control_enabled", True)):
            logger.info(
                "auto_shelf_bid_control_set_bid_skipped_disabled auto_adv_id=%s nmid=%s bid_minor=%s",
                getattr(complex_adv, "auto_adv_id", None),
                nmids[0],
                bid_minor,
            )
            return None
        auto_adv_id = complex_adv.auto_adv_id
        nmid = nmids[0]
        api_bid = self.to_api_bid(bid_minor)
        if settings.AUTO_SHELF_BID_CONTROL_DRY_RUN:
            logger.info(
                "auto_shelf_bid_control_set_bid_dry_run auto_adv_id=%s nmid=%s bid_minor=%s api_bid=%s currency=%s",
                auto_adv_id,
                nmid,
                bid_minor,
                api_bid,
                currency,
            )
            return None

        await self._wb_modifier.patch_auto_adv_bids_kopecks(
            int(auto_adv_id),
            {int(nmid): int(api_bid)},
        )
        if self._bid_cache_manager is not None:
            await self._bid_cache_manager.set_bids(
                int(auto_adv_id),
                {int(nmid): int(bid_minor)},
            )
        logger.info(
            "auto_shelf_bid_control_set_bid_ok auto_adv_id=%s nmid=%s bid_minor=%s api_bid=%s currency=%s",
            auto_adv_id,
            nmid,
            bid_minor,
            api_bid,
            currency,
        )
        return None
