import datetime
from pydantic import BaseModel, ConfigDict


class GetNormqueryStatsCommandBatchForAdv(BaseModel):
    adv_id: int
    nmid: int

    model_config = ConfigDict(arbitrary_types_allowed=True)

class GetNormqueryStatsCommand(BaseModel):
    date_from: datetime.date
    date_to: datetime.date
    batchs: list[GetNormqueryStatsCommandBatchForAdv]
