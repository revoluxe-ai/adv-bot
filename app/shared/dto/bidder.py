from dataclasses import dataclass
from typing import List, Optional, Any


@dataclass
class ProcessingStats:
    total_processed: int = 0
    successful_updates: int = 0
    skipped_updates: int = 0
    api_errors: int = 0
    calculation_errors: int = 0
    batches_sent: int = 0


@dataclass
class BidUpdateResult:
    adv_id: int
    nmid: int
    new_bid: Optional[int] = None
    error: Optional[str] = None


@dataclass
class UpdateBidForNmidTask:
    adv_id: int
    nmid: int
    new_bid_coro: Any  # coroutine returning int


@dataclass
class UpdateBidsSearchAdvInShopBatch:
    tasks: List[UpdateBidForNmidTask]
