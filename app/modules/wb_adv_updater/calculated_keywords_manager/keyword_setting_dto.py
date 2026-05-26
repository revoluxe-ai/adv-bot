from pydantic import BaseModel

from app.modules.common_slaves.wildberries.models.enums import KeywordStrategyMode


class KeywordSettingDTO(BaseModel):
    text: str
    relevant: bool
    hard_status: int
    id: int
    target_place: int | None = None
    predict_ctr: float | None = None
    added_clicks: int | None = 0
    strategy_mode: KeywordStrategyMode = KeywordStrategyMode.MIN_CPA
