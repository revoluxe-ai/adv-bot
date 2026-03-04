from app.shared.domains.wb.dto.redis_keyword_bidder_status_manager.bidder_keyword_status import BidderKeywordStatus
from .calculation_input import CalculationInput
from .update_bids_command import DirectEnum, NewBid
import logging

logger = logging.getLogger(__name__)


def _resolve_direct(current_position: float, target_position: int) -> DirectEnum:
    if current_position > target_position:
        return DirectEnum.UP
    return DirectEnum.DOWN


def _resolve_effective_step(calculation_input: CalculationInput, direct: DirectEnum) -> int:
    base_step = max(1, calculation_input.step)
    prev_step = calculation_input.prev_step
    prev_direct = calculation_input.prev_direct
    if prev_step is None or prev_step <= 0 or prev_direct is None:
        return base_step
    if prev_direct == direct:
        return min(prev_step * 2, base_step)
    return max(prev_step // 2, 1)


def _resolve_predict_bid(calculation_input: CalculationInput) -> int | None:
    predict_map = calculation_input.predict_target_bids
    if not predict_map:
        return None
    cluster_map = predict_map.get(calculation_input.cluster)
    if not cluster_map:
        return None
    predict_bid = cluster_map.get(calculation_input.target_position)
    if predict_bid is None:
        return None
    return int(round(predict_bid))


def new_bid_calculate(calculation_input: CalculationInput) -> NewBid | None:
    current_bid = calculation_input.current_bid
    current_position = calculation_input.current_position
    if current_position < 1: # фоллбек на всякий случай
        current_position  = 1
    direct = _resolve_direct(current_position, calculation_input.target_position)
    effective_step = _resolve_effective_step(calculation_input, direct)
    predict_bid_for_target_position = _resolve_predict_bid(calculation_input)
    max_bid = calculation_input.max_bid
    min_bid: int | None = calculation_input.min_bid
    new_bid: int

    if (
        direct == DirectEnum.UP
        and predict_bid_for_target_position is not None
        and predict_bid_for_target_position > current_bid
    ):
        new_bid = predict_bid_for_target_position
    elif (
        direct == DirectEnum.DOWN
        and predict_bid_for_target_position is not None
        and predict_bid_for_target_position < current_bid
    ):
        new_bid = predict_bid_for_target_position
    elif direct == DirectEnum.UP:
        new_bid = current_bid + effective_step
    else:
        new_bid = current_bid - effective_step

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
        step=effective_step,
        direct=direct,
    )





