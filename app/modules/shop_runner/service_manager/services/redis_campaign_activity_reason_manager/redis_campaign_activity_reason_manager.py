"""Redis manager that stores last campaign activity command and reason per campaign (auto/search)."""

from __future__ import annotations

from datetime import timedelta
from typing import Literal

from app.core.redis_manager_v2.redis_client import RedisClient

from .dto.campaign_activity_reason import CampaignActivityReason

CampaignType = Literal["auto", "search"]


class RedisCampaignActivityReasonManager:
    """Stores and retrieves last activity reason for each campaign (by adv_id and type)."""

    _PREFIX = "campaign-activity-reason"
    _TTL = int(timedelta(hours=48).total_seconds())

    def __init__(self, redis_client: RedisClient) -> None:
        self._redis_client = redis_client

    @staticmethod
    def _key(adv_id: int, campaign_type: CampaignType) -> str:
        return f"{RedisCampaignActivityReasonManager._PREFIX}:{adv_id}:{campaign_type}"

    async def set(
        self,
        adv_id: int,
        campaign_type: CampaignType,
        reason: CampaignActivityReason,
    ) -> None:
        """Store the last command and reason for the given campaign."""
        key = self._key(adv_id, campaign_type)
        await self._redis_client.set(key, reason.to_redis(), ex=self._TTL)

    async def get(
        self,
        adv_id: int,
        campaign_type: CampaignType,
    ) -> CampaignActivityReason | None:
        """Load the last stored reason for the given campaign. Returns None if missing or invalid."""
        key = self._key(adv_id, campaign_type)
        raw = await self._redis_client.get(key)
        if not raw:
            return None
        return CampaignActivityReason.from_redis(raw)
