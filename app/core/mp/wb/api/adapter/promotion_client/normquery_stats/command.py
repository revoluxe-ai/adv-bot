import datetime
from typing import Sequence
from pydantic import BaseModel, field_validator, ConfigDict

from app.modules.shop_runner.service_manager.wb_shop_data_manager.dto.complex_adv import ComplexAdv


class GetNormqueryStatsCommandBatchForAdv(BaseModel):
    adv_id: int
    nmid: int

    model_config = ConfigDict(arbitrary_types_allowed=True)

class GetNormqueryStatsCommand(BaseModel):
    date_from: datetime.date
    date_to: datetime.date
    batchs: list[GetNormqueryStatsCommandBatchForAdv]

    @field_validator("batchs")
    def validate_complex_advs_len(cls, v: Sequence["ComplexAdv"]):
        if len(v) > 100:
            raise ValueError("batchs cannot contain more than 100 elements")
        return v