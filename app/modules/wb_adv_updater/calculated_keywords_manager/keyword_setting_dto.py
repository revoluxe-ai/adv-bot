from pydantic import BaseModel


class KeywordSettingDTO(BaseModel):
    text: str
    relevant: bool
    hard_status: int
    id: int
    target_place: int | None = None
    predict_ctr: float | None = None
    added_clicks: int | None = 0
