from __future__ import annotations

"""Миксин для работы с рекламными кампаниями (Promotion API)."""

import logging
from typing import TYPE_CHECKING, Any

from app.shared.application.dto.campaigns import CampaignDTO, CampaignsListDTO

if TYPE_CHECKING:
    from ..base_wb_api import BaseWBApi

logger = logging.getLogger(__name__)


class CampaignsMixin:
    """Миксин для получения списка рекламных кампаний через адаптер нового WB API."""

    async def get_campaigns(
        self: BaseWBApi,
        adv_ids: list[int] | None = None,
    ) -> CampaignsListDTO:
        """Получить список рекламных кампаний магазина.

        Args:
            adv_ids: Необязательный список ID кампаний. Если не указан, будут загружены все.

        Returns:
            CampaignsListDTO: Список кампаний в формате DTO.

        """
        try:
            from dependency_injector.wiring import Provide
            from app.core.di.wb_api.wb_api_container import WBApiDIContainer

            adapter = WBApiDIContainer.current_adapter()

            # Если ID не переданы — получаем все ID кампаний
            if adv_ids is None:
                adv_ids = await adapter.get_campaign_ids()

            if not adv_ids:
                return CampaignsListDTO(shop_id=self.shop_id, campaigns=[])

            campaigns: list[CampaignDTO] = []
            batch_size = 50
            for i in range(0, len(adv_ids), batch_size):
                batch_ids = adv_ids[i : i + batch_size]
                raw_campaigns = await adapter.get_campaigns_by_ids(batch_ids)

                for c in raw_campaigns:
                    dto = self._to_campaign_dto(c)
                    if dto is not None:
                        campaigns.append(dto)

            return CampaignsListDTO(shop_id=self.shop_id, campaigns=campaigns)

        except Exception as e:
            logger.error(f"[{self.shop_id}] Ошибка получения кампаний: {e}", exc_info=True)
            raise

    async def get_bids(
        self: BaseWBApi,
        adv_id: int,
    ) -> dict[int, int]:
        """Получить текущие CPM-ставки кампании (dict[nmid, cpm])."""
        campaigns = await self.get_campaigns([adv_id])
        if not campaigns.campaigns:
            return {}
        campaign = campaigns.campaigns[0]
        return campaign.bids or {}

    def _to_campaign_dto(self, data: dict[str, Any]) -> CampaignDTO | None:
        """Преобразовать словарь кампании в CampaignDTO."""
        try:
            return CampaignDTO(
                advert_id=int(data.get("advert_id", 0)),
                name=str(data.get("name", "")),
                status=int(data.get("status", 0)),
                type=int(data.get("type", 0)),
                create_time=str(data.get("create_time", "")),
                change_time=str(data.get("change_time", "")),
                start_time=data.get("start_time"),
                end_time=data.get("end_time"),
                daily_budget=data.get("daily_budget"),
                nmids=data.get("nmids"),
                payment_type=data.get("payment_type"),
                auto_active=data.get("auto_active"),
                auto_subject_id=data.get("auto_subject_id"),
                auto_subject_name=data.get("auto_subject_name"),
                auto_sets=data.get("auto_sets"),
                bids=data.get("bids"),
            )
        except Exception:
            logger.exception("Не удалось конвертировать данные кампании в DTO")
            return None
