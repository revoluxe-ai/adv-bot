"""Инкрементальная статистика полок (рекомендаций) Auto-РК по ставке и цене."""

from .auto_shelf_bid_increment_manager import AutoShelfBidIncrementManager
from .redis_auto_recommendations_bid_value_manager import (
    RedisAutoRecommendationsBidValueManager,
)

__all__ = ["AutoShelfBidIncrementManager", "RedisAutoRecommendationsBidValueManager"]
