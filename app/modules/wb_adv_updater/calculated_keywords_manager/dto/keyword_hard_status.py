from dataclasses import dataclass

from app.modules.common_slaves.wildberries.models import KeywordSetting
from app.shared.domains.wb.dto.redis_keyword_bidder_status_manager.bidder_keyword_status import BidderKeywordStatus


@dataclass
class KeywordHardStatus:
    keyword_setting: KeywordSetting
    bidder_keyword_status: BidderKeywordStatus