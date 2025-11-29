from pydantic import BaseModel


class SetMinusPhrasesCommand(BaseModel):
    advert_id: int
    nm_id: int
    norm_queries: list[str]
