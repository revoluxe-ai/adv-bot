from pydantic import BaseModel

from app.modules.wb_adv_updater.calculated_keywords_manager.dto.states import KeywordStatus, KeywordStatusReason


class KeywordState(BaseModel):
    status: KeywordStatus
    reason: KeywordStatusReason
    best_keyword_status: bool
