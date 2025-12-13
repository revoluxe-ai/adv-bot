from dataclasses import dataclass

from app.shared.domains.wb.dto.redis_keyword_bidder_status_manager.bidder_keyword_status import BidderKeywordStatus


@dataclass
class RedisCommand:
    adv_id: int
    nmid: int
    text: str
    bidder_keyword_status: BidderKeywordStatus | None
