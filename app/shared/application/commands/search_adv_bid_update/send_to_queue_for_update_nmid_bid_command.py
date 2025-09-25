from asyncio import Future
from dataclasses import dataclass

from app.modules.common_slaves.wildberries.data_classes.keywordstat_from_db import CalculatedKeyword


@dataclass
class SendToQueueForUpdateNmidBidCommand:
    shop_id: str
    adv_id: int
    nmid: int
    max_cpm_bid: int
    target_position: int
    bidder_step: int
    best_keyword_future: Future[list[CalculatedKeyword]]
    min_bids_future: Future[dict[int, int]]
    current_positions_future: Future[dict[int, int]]
    current_bids_future: Future[dict[int, int]]
