from pydantic import BaseModel


class KeywordSettingDTO(BaseModel):
    text: str
    relevant: bool
    hard_status: int
    id: int
    predict_ctr: float | None = None
    added_clicks: int | None = 0