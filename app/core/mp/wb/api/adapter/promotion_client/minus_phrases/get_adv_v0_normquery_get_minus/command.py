from pydantic import BaseModel


class GetMinusPhrasesCommand(BaseModel):
    advert_id: int
    nm_id: int
