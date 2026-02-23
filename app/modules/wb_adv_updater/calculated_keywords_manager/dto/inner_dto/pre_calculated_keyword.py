from __future__ import annotations

from pydantic import BaseModel

from app.modules.wb_adv_updater.calculated_keywords_manager.keyword_setting_dto import KeywordSettingDTO
from app.modules.wb_adv_updater.calculated_keywords_manager.keyword_stat import KeywordStat
from app.shared.domains.wb.dto.redis_keyword_bidder_status_manager.bidder_keyword_status import BidderKeywordStatus

from .keyword_cpm_sources import KeywordCpmSources


class PreCalculatedKeyword(BaseModel):
    adv_id: int
    keyword_setting: KeywordSettingDTO
    cluster_stat: KeywordStat
    bidder_status: "BidderKeywordStatus"
    cpm_sources: KeywordCpmSources | None = None

    @property
    def ctr(self) -> float:
        return self.cluster_stat.ctr

    @property
    def rating_by_orders(self) -> float:
        return self.cluster_stat.final_rating

    @property
    def hard_status(self) -> int:
        return self.keyword_setting.hard_status


    @property
    def relevant(self) -> bool:
        return self.keyword_setting.relevant
