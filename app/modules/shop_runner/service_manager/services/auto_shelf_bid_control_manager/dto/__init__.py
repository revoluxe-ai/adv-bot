"""DTO слоя управления ставкой полок Auto-РК."""

from .bid_stats_dto import BidStatsDTO
from .control_view_dto import (
    AutoShelfBidControlViewDTO,
    BidPointStatsDTO,
    CoverageLayerBidDTO,
)
from .next_test_bid import NextTestBid
from .optimization_metric import OptimizationMetric, resolve_optimization_metric
from .selected_cpo_contract import (
    AutoShelfBidSelectedCpoContract,
    resolve_selected_cpo_contract_from_view,
)

__all__ = [
    "AutoShelfBidControlViewDTO",
    "BidPointStatsDTO",
    "CoverageLayerBidDTO",
    "BidStatsDTO",
    "NextTestBid",
    "OptimizationMetric",
    "AutoShelfBidSelectedCpoContract",
    "resolve_selected_cpo_contract_from_view",
    "resolve_optimization_metric",
]
