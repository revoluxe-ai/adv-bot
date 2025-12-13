from app.shared.domains.wb.dto.redis_keyword_bidder_status_manager.bidder_keyword_status import BidderKeywordStatus
from .calculation_input import CalculationInput
from .update_bids_command import NewBid
import logging

logger = logging.getLogger(__name__)

def new_bid_calculate(calculation_input: CalculationInput) -> NewBid | None:
    current_bid = calculation_input.current_bid
    current_position = calculation_input.current_position
    target_position = calculation_input.target_position
    step: int = calculation_input.step
    max_bid = calculation_input.max_bid
    min_bid: int | None = calculation_input.min_bid
    auto_max_bid = calculation_input.auto_max_bid
    if auto_max_bid and auto_max_bid < max_bid:
        max_bid = int(auto_max_bid + 0.5)
    new_bid: int
    if current_position > target_position:
        new_bid = current_bid + step
    else:
        new_bid = current_bid - step

    if new_bid >= max_bid:
        new_bid = max_bid
        bidder_keyword_status = BidderKeywordStatus.GOOD
    elif min_bid is not None and min_bid <= new_bid < max_bid:
        bidder_keyword_status = BidderKeywordStatus.GOOD
    elif min_bid is None:
        logger.error("Нет минимальной ставки: не могу снизить ставку!!!")
        return None
    else:
        new_bid = min_bid
        bidder_keyword_status = BidderKeywordStatus.BAD
    if new_bid == current_bid:
        return None
    return  NewBid(
        adv_id=calculation_input.adv_id,
        nmid=calculation_input.nmid,
        new_bid=new_bid,
        bidder_keyword_status=bidder_keyword_status,
        cluster=calculation_input.cluster,
    )





