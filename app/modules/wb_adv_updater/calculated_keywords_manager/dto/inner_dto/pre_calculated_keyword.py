from pydantic import BaseModel

from app.modules.wb_adv_updater.calculated_keywords_manager.keyword_setting_dto import KeywordSettingDTO
from app.modules.wb_adv_updater.calculated_keywords_manager.keyword_stat import KeywordStat



class PreCalculatedKeyword(BaseModel):
    adv_id: int
    keyword_setting: KeywordSettingDTO
    cluster_stat: KeywordStat

    @property
    def ctr(self) -> float:
        return self.cluster_stat.ctr

    @property
    def rating_by_orders(self) -> float:
        return self.cluster_stat.final_rating

    @property
    def hard_status(self) -> int:
        return self.keyword_setting.hard_status