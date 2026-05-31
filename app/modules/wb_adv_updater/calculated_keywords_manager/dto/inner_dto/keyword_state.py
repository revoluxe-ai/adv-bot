from pydantic import BaseModel

from app.modules.wb_adv_updater.calculated_keywords_manager.dto.above_target_min_bid_diagnostic import (
    AboveTargetMinBidDiagnostic,
)
from app.modules.wb_adv_updater.calculated_keywords_manager.dto.states import KeywordStatus, KeywordStatusReason


class KeywordState(BaseModel):
    status: KeywordStatus
    reason: KeywordStatusReason
    best_keyword_status: bool
    # Окно перетеста 24–25 ч: метка «Т», основная причина — от обычной логики
    cooldown_display_tag: str | None = None
    # Диагностика правила МС (mirror factual outcome apply, без смены решения)
    above_target_min_bid: AboveTargetMinBidDiagnostic | None = None
