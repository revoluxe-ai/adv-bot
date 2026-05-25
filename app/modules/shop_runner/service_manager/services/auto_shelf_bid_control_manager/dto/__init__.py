"""DTO слоя управления ставкой полок Auto-РК."""

from .bid_stats_dto import BidStatsDTO
from .control_view_dto import AutoShelfBidControlViewDTO, BidPointStatsDTO
from .next_test_bid import NextTestBid

__all__ = [
    "AutoShelfBidControlViewDTO",
    "BidPointStatsDTO",
    "BidStatsDTO",
    "NextTestBid",
]

