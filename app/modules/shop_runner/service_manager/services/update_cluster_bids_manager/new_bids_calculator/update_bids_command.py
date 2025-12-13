from dataclasses import dataclass

from app.shared.domains.wb.dto.redis_keyword_bidder_status_manager.bidder_keyword_status import BidderKeywordStatus


@dataclass(frozen=True)
class NewBid:
    new_bid: int
    adv_id: int
    nmid: int
    cluster: str
    bidder_keyword_status: BidderKeywordStatus



@dataclass(frozen=True)
class UpdateBidsCommand:
    new_bids: list[NewBid]
