from dataclasses import dataclass
from enum import StrEnum, auto

from app.shared.domains.wb.dto.redis_keyword_bidder_status_manager.bidder_keyword_status import BidderKeywordStatus


class DirectEnum(StrEnum):
    UP = auto()
    DOWN = auto()


@dataclass(frozen=True)
class NewBid:
    """Одна новая ставка по кластеру; правила min/max — в ``new_bid_calculate``."""

    new_bid: int
    adv_id: int
    nmid: int
    cluster: str
    bidder_keyword_status: BidderKeywordStatus
    step: int
    direct: DirectEnum



@dataclass(frozen=True)
class UpdateBidsCommand:
    new_bids: list[NewBid]
