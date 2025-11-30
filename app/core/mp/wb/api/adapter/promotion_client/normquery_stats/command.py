import datetime
from typing import Sequence
from pydantic import BaseModel, field_validator, ConfigDict

from app.modules.shop_runner.service_manager.wb_shop_data_manager.dto.complex_adv import ComplexAdv


class GetNormqueryStatsCommand(BaseModel):

    complex_advs: Sequence[ComplexAdv]
    date_from: datetime.date
    date_to: datetime.date

    @field_validator("complex_advs")
    def validate_complex_advs_len(cls, v: Sequence["ComplexAdv"]):
        if len(v) > 100:
            raise ValueError("complex_advs cannot contain more than 100 elements")
        return v

    model_config = ConfigDict(arbitrary_types_allowed=True)